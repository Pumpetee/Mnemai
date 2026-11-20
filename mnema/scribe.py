"""Meeting scribe: record a meeting or take a recording, recognise speech locally, put the result into a chat.

Same engine as the owner's MeetScribe: faster-whisper on the CPU (int8), the microphone and the computer's sound are
recorded as two separate channels, so the transcript shows who speaks without guessing by voice. Silence
hallucinations ("Спасибо за просмотр") and speaker echo picked up by the microphone are cut out.

Audio and transcript are files in the memory folder, «80 Meetings/<дата> <название>/». Where speech is recognised —
here or by a cloud Whisper — is decided by a preset (Private / Quality / Fast, see scribe_cloud.py); the owner is
always told. A recording lasts no more than 5 hours, then it stops by itself.
The summary request goes to the chosen chat model, as with any message.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path

from .vault import Vault

SR = 16000
BLOCK = 4000
MAX_RECORD_S = 5 * 60 * 60  # the owner's limit: a meeting recording lasts no more than 5 hours
AUDIO_EXT = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".oga",
    ".opus",
    ".webm",
    ".flac",
    ".aac",
    ".wma",
    ".amr",
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".3gp",
    ".m4v",  # video: the sound track is transcribed
}
_state: dict[str, dict] = {}
_model = {"name": "", "obj": None, "threads": 0}
_lock = threading.Lock()


def available() -> tuple[bool, str]:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False, "распознавание речи не установлено"
    return True, ""


def human_error(e: BaseException) -> str:
    """What went wrong with a recording or a transcription, in the owner's words."""
    import re as _re

    text = str(e)
    if any(w in text for w in ("snapshot", "HF_HUB", "huggingface", "hf.co")) or isinstance(e, (ConnectionError,)):
        return (
            "Не скачалась модель распознавания речи (около 0,5 ГБ): её нужно скачать один раз, нужен интернет. "
            "Подключись и повтори — или выбери облачную расшифровку: Настройки → Записи встреч."
        )
    if _re.search(r"[А-Яа-яЁё]", text) and not _re.search(r"Errno|WinError", text):
        return text[:300]
    from .errors import human

    return human(e, "распознаванием речи")


MIC_HELP = (
    "Микрофон не найден или Windows не даёт к нему доступ: проверь, что он подключён, и разреши доступ — "
    "Параметры Windows → Конфиденциальность → Микрофон."
)


def can_record() -> tuple[bool, str]:
    try:
        import soundcard as sc

        sc.default_microphone()
        return True, ""
    except Exception:
        return False, MIC_HELP


def st(vault: Vault) -> dict:
    return _state.setdefault(str(vault.root), {"status": "idle"})


def folder(vault: Vault, name: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H-%M")
    slug = re.sub(r'[\\/:*?"<>|]+', " ", name or "Встреча").strip()[:60] or "Встреча"
    from .vault import MEETINGS

    d = vault.root / MEETINGS / f"{stamp} {slug}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def status(vault: Vault) -> dict:
    s = {k: v for k, v in st(vault).items() if not k.startswith("_")}
    ok, why = available()
    s["available"], s["reason"] = ok, why
    if s.get("status") == "recording" and s.get("started"):
        s["elapsed"] = int(time.time() - s["started"])
        s["max_seconds"] = MAX_RECORD_S
    return s


# ---------------------------------------------------------------- recording


def _capture(device, path: Path, stop_evt: threading.Event, errors: list):
    import soundfile as sf

    try:
        with (
            device.recorder(samplerate=SR, channels=1, blocksize=BLOCK) as rec,
            sf.SoundFile(str(path), mode="w", samplerate=SR, channels=1, subtype="PCM_16") as out,
        ):
            while not stop_evt.is_set():
                out.write(rec.record(numframes=BLOCK))
    except Exception as e:
        errors.append(f"{path.stem}: {e}")


def start(vault: Vault, name: str = "") -> dict:
    s = st(vault)
    if s.get("status") in ("recording", "transcribing"):
        raise ValueError("уже идёт запись или расшифровка")
    ok, why = available()
    if not ok:
        raise ValueError(why)
    import soundcard as sc

    name = name or "Встреча " + dt.datetime.now().strftime("%d.%m %H:%M")
    d = folder(vault, name)
    try:
        speaker = sc.default_speaker()
        loop = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        mic = sc.default_microphone()
    except Exception:
        raise ValueError(MIC_HELP) from None
    stop_evt, errors = threading.Event(), []
    threads = [
        threading.Thread(target=_capture, args=(loop, d / "system.wav", stop_evt, errors), daemon=True),
        threading.Thread(target=_capture, args=(mic, d / "mic.wav", stop_evt, errors), daemon=True),
    ]
    for t in threads:
        t.start()
    s.clear()
    s.update(
        status="recording",
        name=name,
        dir=str(d),
        started=time.time(),
        errors=errors,
        mic=mic.name,
        speaker=speaker.name,
        max_seconds=MAX_RECORD_S,
        _stop=stop_evt,
        _threads=threads,
    )
    s["_limit"] = threading.Timer(MAX_RECORD_S, lambda: _limit(vault))
    s["_limit"].daemon = True
    s["_limit"].start()
    return status(vault)


def _limit(vault: Vault) -> None:
    """The owner's limit: a recording stops by itself after 5 hours."""
    s = st(vault)
    if s.get("status") != "recording":
        return
    s["notice"] = f"Запись остановлена: лимит {MAX_RECORD_S // 3600} часов"
    stop(vault)


def stop(vault: Vault, model_ref: str = "") -> dict:
    s = st(vault)
    if s.get("status") != "recording":
        raise ValueError("запись не идёт")
    t = s.get("_limit")
    if t:
        t.cancel()
    s["_stop"].set()
    for t in s["_threads"]:
        t.join(timeout=5)
    d = Path(s["dir"])
    tracks = [(d / "system.wav", "Собеседник"), (d / "mic.wav", "Я")]
    duration = int(time.time() - s["started"])
    from . import achievements

    achievements.event(vault, "meeting", seconds=duration)
    _launch(vault, d, s["name"], tracks, duration, model_ref)
    return status(vault)


def import_file(vault: Vault, filename: str, data_b64: str, name: str = "", model_ref: str = "") -> dict:
    s = st(vault)
    if s.get("status") in ("recording", "transcribing"):
        raise ValueError("уже идёт запись или расшифровка")
    ok, why = available()
    if not ok:
        raise ValueError(why)
    ext = Path(filename or "").suffix.lower()
    if ext not in AUDIO_EXT:
        raise ValueError("это не аудиозапись")
    title = name or Path(filename).stem
    d = folder(vault, title)
    src = d / f"запись{ext}"
    src.write_bytes(base64.b64decode(str(data_b64).split(",")[-1]))
    from . import achievements

    achievements.event(vault, "meeting", seconds=0)
    _launch(vault, d, title, [(src, "Запись")], 0, model_ref)
    return status(vault)


# ---------------------------------------------------------------- recognition


def _whisper(model_name: str, threads: int = 0):
    with _lock:
        if _model["obj"] is None or _model["name"] != model_name or _model["threads"] != threads:
            from . import net

            p = net.proxy(net._setting["value"])  # the model is downloaded once, through the same proxy
            if p:
                os.environ.setdefault("HTTPS_PROXY", p)
            from faster_whisper import WhisperModel

            _model.update(
                name=model_name,
                threads=threads,
                obj=WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads),
            )
        return _model["obj"]


def model_name(vault: Vault) -> str:
    from .agent import profile as P

    m = P.load(vault).get("scribe_model") or "auto"
    if m != "auto":
        return m
    hub = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"
    return "medium" if (hub / "models--Systran--faster-whisper-medium").exists() else "small"


def transcribe(model, path, speaker: str, progress=None) -> tuple[list[dict], float]:
    """path: a file or the decoded audio itself."""
    if isinstance(path, Path):
        if not path.exists() or path.stat().st_size < 8000:
            return [], 0.0
        path = str(path)
    segments, info = model.transcribe(path, vad_filter=True, vad_parameters={"min_silence_duration_ms": 700})
    out = []
    for seg in segments:
        if progress and info.duration:
            progress(min(1.0, seg.end / info.duration))
        txt = seg.text.strip()
        if not txt or len(txt) < 3 or getattr(seg, "no_speech_prob", 0) > 0.6:
            continue  # whisper invents phrases on silence
        out.append({"start": seg.start, "end": seg.end, "speaker": speaker, "text": txt})
    return out, info.duration or 0.0


def keep(seg, speaker: str) -> dict | None:
    """A recognised segment worth keeping (whisper invents phrases on silence)."""
    txt = seg.text.strip()
    if not txt or len(txt) < 3 or getattr(seg, "no_speech_prob", 0) > 0.6:
        return None
    return {"start": seg.start, "end": seg.end, "speaker": speaker, "text": txt}


def _norm(t: str) -> str:
    return "".join(c for c in t.lower() if c.isalnum() or c == " ").strip()


def drop_echo(segs: list[dict], system_label: str = "Собеседник") -> list[dict]:
    """Speakers playing into the microphone duplicate the other side's words — the system channel wins."""
    sys_segs = [s for s in segs if s["speaker"] == system_label]
    out = []
    for s in segs:
        if s["speaker"] != system_label and any(
            s["start"] < t["end"] + 1.5
            and t["start"] < s["end"] + 1.5
            and SequenceMatcher(None, _norm(s["text"]), _norm(t["text"])).ratio() > 0.55
            for t in sys_segs
        ):
            continue
        out.append(s)
    return out


def transcript_md(name: str, segs: list[dict], duration: int, model: str, where: str = "local") -> str:
    when = dt.datetime.now().strftime("%d.%m.%Y %H:%M")
    mm, ss = divmod(int(duration), 60)
    how = f"распознано на этом компьютере (модель {model})" if where == "local" else "распознано облачным Whisper"
    lines = [f"# {name}", "", f"> {when} · {mm} мин {ss} с · {how}", ""]
    prev = None
    for s in segs:
        m, sec = divmod(int(s["start"]), 60)
        if s["speaker"] != prev:
            lines += ["", f"**{s['speaker']}** `{m:02d}:{sec:02d}`"]
            prev = s["speaker"]
        lines.append(s["text"])
    return "\n".join(lines).strip() + "\n"


def _launch(vault: Vault, d: Path, name: str, tracks: list, duration: int, model_ref: str) -> None:
    s = st(vault)
    s.clear()
    s.update(
        status="transcribing",
        name=name,
        dir=str(d),
        progress=0.0,
        started=time.time(),
        notices=[],
    )

    def say(text: str) -> None:
        """What the owner is told about where and how long: the bar above the chat keeps the latest line."""
        s["notice"] = text
        s["notices"].append(text)

    def work():
        from . import scribe_cloud as SC
        from . import tuning

        try:
            mname = model_name(vault)
            s["model"] = mname
            threads = tuning.get(vault)["threads"]
            s["phase"] = "читаю запись"
            audios = [
                (SC.load(Path(p)), label) for p, label in tracks if Path(p).exists() and Path(p).stat().st_size >= 8000
            ]
            if not audios:
                raise RuntimeError("в записи не нашлось звука")
            total = max(len(a) / SC.SR for a, _ in audios)
            work_s = sum(len(a) / SC.SR for a, _ in audios)
            cfg, cloud = SC.settings(vault), SC.creds(vault)
            where, model, measured = "local", None, None
            if cfg["mode"] == "quality" and cloud:
                where = "cloud"
                say("Расшифровываю облачным Whisper: пресет Quality")
            elif cfg["mode"] == "quality":
                say("Ключа для облачного Whisper нет — расшифровываю на компьютере")
            elif cfg["mode"] == "fast" and work_s > 120:
                s["phase"] = "загружаю модель распознавания"
                model = _whisper(mname, threads)
                s["phase"] = "замеряю скорость компьютера"
                longest = max(range(len(audios)), key=lambda i: len(audios[i][0]))
                rtf, sample = SC.measure(model, audios[longest][0])
                measured = (longest, sample)
                if rtf:
                    from .agent import profile as P

                    P.save(vault, {"scribe_rtf": round(rtf, 3)})
                est = rtf * max(0.0, work_s - SC.SAMPLE_S)  # the measured minute is already done
                s["estimate"] = round(est)
                if SC.fits(est, total):
                    say(f"Расшифровываю на компьютере, примерно {SC.minutes(est)}")
                elif cloud:
                    where = "cloud"
                    say(f"На компьютере вышло бы {SC.minutes(est)} — отдаю облачному Whisper, так выбрано в настройках")
                else:
                    say(
                        f"Расшифровка на компьютере займёт примерно {SC.minutes(est)}. Быстрее — с ключом OpenAI: "
                        f"Настройки → Записи встреч"
                    )
            else:
                say("Расшифровываю на компьютере")
            s["where"] = where
            segs = []
            if where == "cloud":
                s["phase"] = "расшифровывает облачный Whisper"
                try:
                    for i, (audio, label) in enumerate(audios):
                        part = lambda f, i=i: s.update(progress=round((i + f) / len(audios), 3))  # noqa: E731
                        segs += SC.cloud_transcribe(vault, audio, label, part)
                except Exception as e:
                    say(f"Облачный Whisper не ответил ({str(e)[:80]}) — расшифровываю на компьютере")
                    where, segs = "local", []
                    s["where"] = where
            if where == "local":
                if model is None:
                    s["phase"] = "загружаю модель распознавания"
                    model = _whisper(mname, threads)
                s["phase"] = "распознаю речь"
                for i, (audio, label) in enumerate(audios):
                    part = lambda f, i=i: s.update(progress=round((i + f) / len(audios), 3))  # noqa: E731
                    if measured is not None and i == measured[0] and len(audio) > SC.SR * SC.SAMPLE_S:
                        segs += [g for g in (keep(x, label) for x in measured[1]) if g]  # the measured minute is done
                        got, _ = transcribe(model, audio[SC.SR * SC.SAMPLE_S :], label, part)
                        segs += [{**g, "start": g["start"] + SC.SAMPLE_S, "end": g["end"] + SC.SAMPLE_S} for g in got]
                    else:
                        got, _ = transcribe(model, audio, label, part)
                        segs += got
            segs.sort(key=lambda x: x["start"])
            if len(tracks) > 1:
                segs = drop_echo(segs)
            if not segs:
                raise RuntimeError("в записи не нашлось речи")
            md = transcript_md(name, segs, duration or int(total), mname, where)
            (d / "Расшифровка.md").write_text(md, encoding="utf-8")
            (d / "transcript.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
            s.update(phase="готовлю итоги в чате", progress=1.0)
            from .chat import engine as CH
            from .agent import profile as P

            summ = model_ref or P.load(vault).get("scribe_summary_model") or ""  # chosen in the meeting window
            r = CH.send(
                vault,
                f"Расшифровка: «{name}». Коротко: о чём это, что решили, какие задачи и за кем. "
                f"Если чего-то в записи нет — так и скажи.",
                model=summ,
                files=[{"name": "Расшифровка.md", "data": base64.b64encode(md.encode("utf-8")).decode()}],
                learn=False,
            )  # learning takes the transcript itself, below
            _learn(vault, segs, name)
            from .agent import profile as P

            if not P.load(vault).get("scribe_keep_audio"):  # the owner didn't ask to keep the recording itself
                for p, _ in tracks:
                    try:
                        Path(p).unlink(missing_ok=True)
                    except OSError:
                        pass
            s.update(status="done", chat=r["chat"], file=str(d / "Расшифровка.md"), phase="")
            SC.notify(f"Mnemai: расшифровка «{name}» готова")
        except Exception as e:
            s.update(status="error", error=human_error(e), phase="")
            SC.notify(f"Mnemai: расшифровка «{name}» не вышла")

    threading.Thread(target=work, daemon=True, name="mnema-scribe").start()


def _learn(vault: Vault, segs: list[dict], name: str) -> None:
    """The owner's own words teach Mnemai; the other side is context."""
    from .learn import engine as LE
    from .learn.sources import Episode

    mine = "\n".join(s["text"] for s in segs if s["speaker"] in ("Я", "Запись"))[:6000]
    other = "\n".join(s["text"] for s in segs if s["speaker"] == "Собеседник")[:1500]
    if mine.strip():
        threading.Thread(
            target=lambda: LE.learn_episodes(
                vault,
                [
                    Episode(
                        "mnema_chat",
                        f"meeting:{name}",
                        dt.datetime.now().isoformat(timespec="seconds"),
                        mine,
                        prev=other,
                        title=f"Встреча: {name}",
                    )
                ],
                "mnema_chat",
            ),
            daemon=True,
        ).start()
