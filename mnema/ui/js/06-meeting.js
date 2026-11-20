// ---------------------------------------------------------------- meeting: one window, three steps — record, transcribe, sum up
const MEET_Q = {
  auto: "авто",
  small: "быстрее",
  medium: "точнее",
  "large-v3": "максимум",
};
async function meetModal(fileToImport) {
  if ($(".meetm")) return;
  const [sc, ag, ms] = await Promise.all([api("/api/scribe/settings"), api("/api/agent"), api("/api/models")]);
  const prof = ag.profile || {},
    models = ms.providers
      .filter((p) => p.ready)
      .flatMap((p) =>
        p.models
          .filter((m) => m.id || p.id !== "claude_code")
          .map((m) => ({
            v: p.id + ":" + m.id,
            l:
              (p.id === "local" ? "На компьютере · " : p.id === "claude_code" ? "" : p.name + " · ") +
              m.name +
              (p.id === "claude_code" ? " · подписка" : ""),
            local: p.id === "local",
          })),
      );
  let st = {
    upload: false,
    file: null,
    mode: sc.mode,
    quality: sc.quality,
    keep: !!prof.scribe_keep_audio,
    model:
      prof.scribe_summary_model && models.some((m) => m.v === prof.scribe_summary_model)
        ? prof.scribe_summary_model
        : CHAT.model || (models[0] || {}).v || "",
    name: "",
  };
  const pop = document.createElement("div");
  pop.className = "modal meetm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  const hour = sc.rtf ? Math.max(1, Math.round(sc.rtf * 60)) : 0;
  const draw = () => {
    const cloudMode = st.mode === "quality" || st.mode === "fast",
      noKey = cloudMode && !sc.cloud_ready,
      sm = models.find((m) => m.v === st.model);
    pop.innerHTML = `<div class="card"><div class="mmhead"><div><h2>${fileToImport ? tr("Расшифровать запись") : tr("Запись встречи")}${hq("scribe")}</h2><p class="hint">${fileToImport ? esc(fileToImport.name) : tr("Три шага, всё настраивается здесь и запоминается.")}</p></div><a href="#" class="mmset" data-mset title="${tr("Настройки расшифровки и итогов")}">${ic("set")}${tr("Настроить")}</a><button class="lmx" data-x>×</button></div>
     <div class="mpipe">
      <div class="mstep s1"><div class="msh"><span class="mn">1</span><div class="mico rec">${ic("mic")}<i></i><i></i></div><b>${fileToImport ? tr("Запись") : tr("Запись")}</b></div>
        <p>${fileToImport ? tr("Готовый файл: аудио или видео.") : tr("Микрофон и звук компьютера пишутся отдельно — в расшифровке видно, кто говорит.") + " " + tr("Запись длится не дольше 5 часов.")}</p>
        ${fileToImport ? "" : `<label class="mchk"><input type="checkbox" data-k="upload" ${st.upload ? "checked" : ""}><span>${tr("Запись уже есть — загрузить")}<small>${tr("аудио или видео с компьютера")}</small></span></label>`}
        ${st.upload && !fileToImport ? `<div class="mfile"><button class="btn l sm" data-k="pick">${ic("folder")}${st.file ? tr("Другой файл…") : tr("Выбрать файл…")}</button><span>${st.file ? esc(st.file.name) : tr("файл не выбран")}</span><input type="file" data-k="fin" accept="audio/*,video/*,.m4a,.ogg,.opus,.amr,.mp3,.wav,.mp4,.mkv,.webm" hidden></div>` : ""}
        <label class="mchk"><input type="checkbox" data-k="keep" ${st.keep ? "checked" : ""}><span>${tr("Сохранить аудиозапись")}<small>${tr("иначе после расшифровки останется только текст")}</small></span></label>
        ${fileToImport ? "" : `<input class="inp" data-k="name" placeholder="${tr("Название встречи, необязательно")}" value="${esc(st.name)}">`}</div>
      <div class="marrow"><i></i></div>
      <div class="mstep s2"><div class="msh"><span class="mn">2</span><div class="mico">${ic("wave")}</div><b>${tr("Расшифровка")}</b></div>
        ${scribePlans(sc, st.mode, true)}
        ${
          st.mode !== "quality"
            ? `<div class="mrowq"><span>${tr("Точность на компьютере")}</span><div class="seg sm">${Object.entries(
                MEET_Q,
              )
                .map(([k, l]) => `<button data-q="${k}" class="${k === st.quality ? "on" : ""}">${tr(l)}</button>`)
                .join("")}</div></div>`
            : ""
        }
        <div class="mfact">${hour && st.mode !== "quality" ? `${ic("gear")}${tr("Этот компьютер расшифровывает час записи примерно за")} ${hour} ${tr("мин")}` : st.mode !== "quality" ? `${ic("gear")}${tr("Скорость замерю на первой записи")}` : ""}${cloudMode ? `<span class="${sc.cloud_ready ? "ok" : "no"}">${ic(sc.cloud_ready ? "check" : "x")}${sc.cloud_ready ? tr("Облачный Whisper готов") + ": " + esc(tr(sc.cloud_from)) : tr("Нет ключа для облачного Whisper")}</span>${noKey ? `<a href="#" data-gokey>${tr("Подключить")}</a>` : ""}` : ""}</div></div>
      <div class="marrow"><i></i></div>
      <div class="mstep s3"><div class="msh"><span class="mn">3</span><div class="mico">${ic("chat")}</div><b>${tr("Итоги")}</b></div>
        <p>${tr("Коротко: о чём говорили, что решили, какие задачи и за кем. Появятся в новом разговоре.")}</p>
        <select class="inp" data-k="model">${models.map((m) => `<option value="${esc(m.v)}" ${m.v === st.model ? "selected" : ""}>${esc(m.l)}</option>`).join("") || `<option value="">${tr("Нет подключённых моделей")}</option>`}</select>
        <div class="mfact">${sm && sm.local ? `${ic("lock")}${tr("Итоги тоже делаются на компьютере: ничего не уходит наружу")}` : sm ? `${ic("globe")}${tr("Текст расшифровки уйдёт этой модели, секреты будут скрыты")}` : ""}</div></div>
     </div>
     <div class="mmfoot"><span class="hint">${tr("Расшифровка и итоги лягут в папку «80 Meetings», итоги — ещё и в разговор.")}</span><button class="btn g" data-x>${tr("Отмена")}</button><button class="btn mgo" id="mgo" ${noKey || !st.model || (st.upload && !st.file && !fileToImport) ? "disabled" : ""}>${fileToImport || st.upload ? `${ic("wave")}${tr("Расшифровать")}` : `<i class="rd"></i>${tr("Начать запись")}`}</button></div></div>`;
    $$("[data-x]", pop).forEach((b) => (b.onclick = () => pop.remove()));
    $$("[data-mset]", pop).forEach(
      (b) =>
        (b.onclick = (e) => {
          e.preventDefault();
          pop.remove();
          goSet("meetings/scrcard");
        }),
    );
    $$("[data-plan]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          st.mode = b.dataset.plan;
          draw();
        }),
    );
    $$("[data-q]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          st.quality = b.dataset.q;
          draw();
        }),
    );
    $('[data-k="keep"]', pop).onchange = (e) => {
      st.keep = e.target.checked;
    };
    if ($('[data-k="upload"]', pop))
      $('[data-k="upload"]', pop).onchange = (e) => {
        st.upload = e.target.checked;
        draw();
      };
    if ($('[data-k="pick"]', pop)) {
      $('[data-k="pick"]', pop).onclick = () => $('[data-k="fin"]', pop).click();
      $('[data-k="fin"]', pop).onchange = (e) => {
        st.file = e.target.files[0] || null;
        draw();
      };
    }
    if ($('[data-k="name"]', pop))
      $('[data-k="name"]', pop).oninput = (e) => {
        st.name = e.target.value;
      };
    $('[data-k="model"]', pop).onchange = (e) => {
      st.model = e.target.value;
      draw();
    };
    if ($("[data-gokey]", pop))
      $("[data-gokey]", pop).onclick = (e) => {
        e.preventDefault();
        pop.remove();
        goSet("meetings/scrcard");
      };
    $("#mgo", pop).onclick = async () => {
      const b = $("#mgo", pop);
      b.disabled = true;
      try {
        await post("/api/scribe/settings", {
          mode: st.mode,
          model: st.quality,
        });
        await post("/api/agent", {
          scribe_keep_audio: st.keep,
          scribe_summary_model: st.model,
        });
        MIC_KEEP = st.keep;
        const f = fileToImport || (st.upload ? st.file : null);
        if (f) {
          const data = await new Promise((r) => {
            const fr = new FileReader();
            fr.onload = () => r(fr.result);
            fr.readAsDataURL(f);
          });
          await post("/api/scribe/import", {
            filename: f.name,
            data,
            model: st.model,
            name: st.name,
          });
          toast(tr("Расшифровываю запись"));
        } else {
          await post("/api/scribe/start", { name: st.name });
          toast(tr("Пишу встречу: микрофон и звук компьютера"));
        }
        pop.remove();
        scribeWatch();
      } catch (e) {
        b.disabled = false;
        toast(e.message);
      }
    };
  };
  draw();
}
