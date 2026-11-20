"""Where a meeting is transcribed: on this computer (free, private, as fast as the processor) or by a cloud Whisper
(fast, paid by the owner's own key, the audio leaves the computer).

Presets (Настройки → Записи встреч):
- private — only local models: always on this computer, nothing leaves it.
- quality — quality: the cloud Whisper when there is a key, otherwise here.
- fast    — the fastest models: short recordings here, long ones to the cloud without asking (the owner is told).
Every choice is shown to the owner: in the bar above the chat and, if the window is hidden, as a tray notification.
"""

from __future__ import annotations

import io
import json
import time
import uuid
import wave
from pathlib import Path

from .vault import Vault

MODES = ("private", "quality", "fast")
OLD_MODES = {"local": "private", "cloud": "quality", "partial": "fast", "auto": "quality"}  # presets before 20.11.2026
SR = 16000
CHUNK_S = 600  # 10 minutes of 16 kHz mono wav ≈ 19 MB: under the 25 MB upload limit
SAMPLE_S = 60  # how much of the recording the speed test reads
NOTIFY = [None]  # set by the desktop app: show a tray notification when the window is hidden


def settings(vault: Vault) -> dict:
    from .agent import profile as P

    p = P.load(vault)
    raw = p.get("scribe_mode") or "quality"
    mode = raw if raw in MODES else OLD_MODES.get(raw, "quality")
    return {
        "mode": mode,
        "base": (p.get("scribe_base") or "").rstrip("/"),
        "model": p.get("scribe_cloud_model") or "",
        "rtf": p.get("scribe_rtf") or 0,
    }


def creds(vault: Vault) -> tuple[str, str, str] | None:
    """(base, key, model) of the cloud Whisper: the owner's own address and key, or the OpenAI key already connected."""
    from .chat import providers as PR
    from .learn import secrets_store
    from .learn.settings import _vid

    s = settings(vault)
    if s["base"]:
        key = secrets_store.get(_vid(vault), "scribe.cloud")
        return (s["base"], key, s["model"] or "whisper-1") if key else None
    key = PR.key_of(vault, "openai")
    return (PR.base_of(vault, "openai") or "https://api.openai.com/v1", key, "whisper-1") if key else None


def notify(text: str) -> None:
    if NOTIFY[0]:
        try:
            NOTIFY[0](text)
        except Exception:
            pass


def minutes(sec: float) -> str:
    m = max(1, round(sec / 60))
    return f"{m} мин" if m < 60 else f"{m // 60} ч {m % 60} мин"


# ---------------------------------------------------------------- audio


def load(path: Path):
    """Any recording → 16 kHz mono float32 (the same decoder the local model uses)."""
    from faster_whisper.audio import decode_audio

    return decode_audio(str(path), sampling_rate=SR)


def wav_bytes(samples) -> bytes:
    import numpy as np

    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)
    return buf.getvalue()


# ---------------------------------------------------------------- how fast is this computer


def measure(model, audio) -> tuple[float, list]:
    """Seconds of work per second of audio, on the first minute of this recording (silence is skipped as in real work).
    The recognised minute is returned too: it is not recognised twice."""
    piece = audio[: SR * SAMPLE_S]
    if len(piece) < SR * 10:
        return 0.0, []
    t = time.time()
    segments, _ = model.transcribe(piece, vad_filter=True, vad_parameters={"min_silence_duration_ms": 700})
    segs = list(segments)
    return (time.time() - t) / (len(piece) / SR), segs


def fits(est_s: float, total_s: float) -> bool:
    """On this computer is fine when it is done within the length of the meeting itself, or within 10 minutes."""
    return est_s <= max(600.0, total_s)


# ---------------------------------------------------------------- the cloud Whisper


def _multipart(fields: dict, file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    out.write(
        f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: audio/wav\r\n\r\n".encode()
    )
    out.write(file_bytes)
    out.write(f"\r\n--{b}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={b}"


def cloud_transcribe(vault: Vault, audio, speaker: str, progress=None) -> list[dict]:
    """10-minute pieces to the cloud Whisper, segments put back on one time line."""
    import urllib.request
    from . import net

    c = creds(vault)
    if not c:
        raise RuntimeError("нет ключа для облачного Whisper: Настройки → Записи встреч")
    base, key, model = c
    out = []
    step = SR * CHUNK_S
    n = max(1, -(-len(audio) // step))
    for i in range(n):
        piece = audio[i * step : (i + 1) * step]
        if len(piece) < SR:
            continue
        body, ctype = _multipart(
            {"model": model, "response_format": "verbose_json", "temperature": "0"},
            wav_bytes(piece),
            f"part{i + 1}.wav",
        )
        req = urllib.request.Request(
            base + "/audio/transcriptions",
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {key}", "Content-Type": ctype},
        )
        with net.urlopen(req, timeout=600) as r:
            d = json.loads(r.read())
        off = i * CHUNK_S
        segs = d.get("segments") or (
            [{"start": 0, "end": len(piece) / SR, "text": d.get("text", "")}] if d.get("text") else []
        )
        for sg in segs:
            txt = str(sg.get("text") or "").strip()
            if len(txt) < 3 or float(sg.get("no_speech_prob") or 0) > 0.6:
                continue
            out.append(
                {
                    "start": off + float(sg.get("start") or 0),
                    "end": off + float(sg.get("end") or 0),
                    "speaker": speaker,
                    "text": txt,
                }
            )
        if progress:
            progress((i + 1) / n)
    from . import outgoing as OG

    OG.log(vault, "whisper", model, 0, {}, {"purpose": f"расшифровка встречи, {minutes(len(audio) / SR)} аудио"})
    return out
