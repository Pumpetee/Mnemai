// ---------------------------------------------------------------- navigation
// ---------------------------------------------------------------- engine: tokens and computer load
const ENG_MODES = {
  eco: ["Эконом", "Меньше токенов и нагрузки. Ответы короче, компьютер почти не занят"],
  balance: ["Баланс", "Золотая середина. Подходит большинству"],
  max: ["Максимум", "Вся память в запросе, длинные ответы, все ядра. Дороже и тяжелее"],
};
const ENG_LOOK = {
  eco: ["🍃", "#22c55e", "#14b8a6", 1],
  balance: ["⚖️", "#6366f1", "#22d3ee", 2],
  max: ["🚀", "#f97316", "#ef4444", 3],
};
const LEARN_STEPS = [5, 10, 15, 30, 60, 120, 240, 720, 1440];
function fmtN(n) {
  return Number(n || 0).toLocaleString(locale());
}
function learnL(m) {
  return m < 60 ? m + " " + tr("мин") : m < 1440 ? m / 60 + " " + tr("ч.") : tr("раз в сутки");
}
const PRECISE_L = ["самый экономный", "экономнее", "баланс", "точнее", "максимально точно"];
const PRECISE_ASK = [
  "только когда без этого никак",
  "когда без этого никак",
  "когда нужно",
  "чаще",
  "при любой неясности",
];
function engineCard(e) {
  if (!e) return "";
  const pr = e.precise ?? 2;
  const u = e.usage || { cloud: 0, local: 0 },
    pct = e.month ? Math.min(100, Math.round((u.cloud / e.month) * 100)) : 0;
  const sl = (k, label, min, max, step, val, shown, hint) =>
    `<div class="engsl"><div class="engh"><span>${label}</span><b data-ev="${k}">${shown}</b></div><input type="range" data-ek="${k}" min="${min}" max="${max}" step="${step}" value="${val}"><div class="hint">${hint}</div></div>`;
  const li = Math.max(
    0,
    LEARN_STEPS.indexOf(e.learn) < 0 ? LEARN_STEPS.findIndex((x) => x >= e.learn) : LEARN_STEPS.indexOf(e.learn),
  );
  return `<div id="engwrap"><div class="card" data-sec="engine" id="engcard"><h2>Движок${hq("engine")}</h2>
   <div class="yprs engmodes">${Object.entries(ENG_MODES)
     .map(([k, [t, s]], n) => {
       // the same cards as «Характер»: a medal in the mode's colours, the name, what it does and how heavy it is
       const [em, c1, c2, lvl] = ENG_LOOK[k];
       return `<button data-em="${k}" class="ypr ${e.mode === k ? "on" : ""}" style="--c1:${c1};--c2:${c2};--d:${n * 0.06}s"><span class="medal2"><span>${em}</span><i class="spark"></i><i class="spark"></i><i class="spark"></i></span><span class="yprt"><b>${tr(t)}</b><span>${tr(s)}</span><span class="ylvl">${tr("Нагрузка")}<i>${[1, 2, 3].map((x) => `<em class="${x <= lvl ? "f" : ""}"></em>`).join("")}</i></span></span>${e.mode === k ? `<span class="yok">${ic("check")}</span>` : ""}</button>`;
     })
     .join("")}</div>
   ${e.mode === "custom" ? `<div class="hint" style="margin-top:8px">${tr("Сейчас своя настройка: ползунки сдвинуты вручную.")}</div>` : ""}
   <div class="engmeter"><div>${tr("В этом месяце облачные ИИ потратили")} <b>${fmtN(u.cloud)}</b> ${tr("токенов")}${e.month ? ` ${tr("из")} ${fmtN(e.month)}` : ""}. ${tr("На компьютере")} — ${fmtN(u.local)}, ${tr("бесплатно")}.</div>${e.month ? `<div class="engbar ${pct >= 90 ? "hot" : ""}"><i style="width:${pct}%"></i></div>` : ""}</div>
   <details class="engfine" ${LS.get("engfine", false) ? "open" : ""}><summary>${tr("Тонкая настройка")}</summary>
    <div class="engcol1">
     <h4>${tr("Токены")}</h4>
      <div class="engsl engprec"><div class="engh"><span>${tr("Точнее ↔ Экономнее")}${hq("economy")}</span><b data-ev="precise">${tr(PRECISE_L[pr])}</b></div>
       <div class="precrow"><small>${tr("Точнее")}</small><input type="range" data-ek="precise" min="0" max="4" step="1" value="${4 - pr}"><small>${tr("Экономнее")}</small></div>
       <div class="hint">${tr("Сверяется")}: ${tr("память")} — ${fmtN(e.memory)} ${tr("знаков")}, ${tr("документ")} — ${tr("до")} ${fmtN(e.docs)} ${tr("знаков")}${pr >= 4 ? ` (${tr("целиком, без сокращений")})` : ""}. ${tr("Уточняет")}: ${tr(PRECISE_ASK[pr])}.</div>
       <div class="hint">${tr("Точнее — ИИ видит больше памяти и документа и чаще переспрашивает. Это дороже.")}</div></div>
      ${sl("answer", tr("Самый длинный ответ"), 300, 16000, 100, e.answer, fmtN(e.answer) + " " + tr("токенов"), tr("Работает для ИИ по ключу и локальной модели. Claude по подписке так не ограничить, но он и не тратит сверх подписки."))}
      <div class="engsl"><div class="engh"><span>${tr("Лимит на месяц")}</span></div><div class="row"><input class="inp" type="number" min="0" step="100000" id="engmonth" value="${e.month || ""}" placeholder="${tr("без лимита")}" style="width:160px"><span class="hint">${tr("токенов облачных ИИ. Дошли до лимита — облачные ИИ ждут следующего месяца, локальная модель работает.")}</span></div></div>
     <h4>${tr("Компьютер")}</h4>
      ${sl("threads", tr("Ядра процессора"), 1, e.cores, 1, e.threads, e.threads + " " + tr("из") + " " + e.cores, tr("Сколько ядер берут локальная модель и расшифровка встреч. Меньше — компьютер свободнее, ответ дольше."))}
      ${sl("ctx", tr("Сколько держит в голове"), 2048, 32768, 2048, e.ctx, fmtN(e.ctx) + " " + tr("токенов"), tr("Длина разговора, которую локальная модель видит целиком. Больше — нужно больше оперативной памяти."))}
    </div></details></div>
   <div class="card" data-sec="engine" id="engbg"><h2>${tr("В фоне")}</h2>
    <div class="tg"><button class="sw ${e.low ? "on" : ""}" id="englow"></button><div><b>${tr("Не мешать работе")}</b><p>${tr("Локальная модель работает с низким приоритетом: окна и браузер не тормозят.")}</p></div></div>
    <div class="engcol1">${sl("learn", tr("Обучение в фоне"), 0, LEARN_STEPS.length - 1, 1, li, learnL(e.learn), tr("Как часто Mnemai проверяет источники обучения."))}</div>
   </div></div>`;
}
function bindEngine() {
  const c = $("#engwrap");
  if (!c) return;
  const redraw = (e) => {
    c.outerHTML = engineCard(e);
    bindEngine();
    decorateToggles($("#engwrap"));
  };
  const set = async (patch) => {
    try {
      redraw(await post("/api/engine", patch));
    } catch (err) {
      toast(err.message);
    }
  };
  $("details", c).ontoggle = (ev) => LS.set("engfine", ev.target.open);
  $$("[data-em]", c).forEach((b) => (b.onclick = () => set({ mode: b.dataset.em })));
  $$("[data-ek]", c).forEach((r) => {
    const k = r.dataset.ek,
      val = () => (k === "learn" ? LEARN_STEPS[+r.value] : k === "precise" ? 4 - +r.value : +r.value);
    r.oninput = () => {
      const v = val(),
        lab = $(`[data-ev="${k}"]`, c);
      lab.textContent =
        k === "learn"
          ? learnL(v)
          : k === "precise"
            ? tr(PRECISE_L[v])
            : k === "threads"
              ? v + " " + tr("из") + " " + r.max
              : fmtN(v) + " " + tr("токенов");
    };
    r.onchange = () => set({ [k]: val() });
  });
  $("#engmonth", c).onchange = (e) => set({ month: parseInt(e.target.value) || 0 });
  $("#englow", c).onclick = (e) => set({ low: !e.currentTarget.classList.contains("on") });
}
// ---------------------------------------------------------------- what left the computer
const PURPOSE_RU = {
  "ответ в чате": "ответ в чате",
  консорциум: "консорциум",
  обучение: "обучение",
  "проверка ответа": "проверка ответа",
  служебное: "служебное",
  "поиск в интернете": "поиск в интернете",
  "название разговора": "название разговора",
  портрет: "портрет",
};
const SCOPE_RU = {
  profile: "обо мне",
  rules: "правила",
  projects: "проекты",
  cards: "карточки",
  people: "люди",
  decisions: "события",
  inbox: "входящие",
  money: "деньги",
  health: "здоровье",
  private: "личное",
};
const RED_RU = {
  card: "номера карт",
  secret: "ключи и токены",
  password: "пароли",
  phone: "телефоны",
  passport: "паспорта",
  snils: "СНИЛС",
  inn: "ИНН",
  account: "номера счетов",
};
function provName(pid) {
  return (
    {
      claude_code: "Claude",
      anthropic: "Anthropic",
      openai: "ChatGPT",
      gemini: "Gemini",
      openrouter: "OpenRouter",
      deepseek: "DeepSeek",
      yandex: "YandexGPT",
      strata: "Strata",
      api: "ИИ по ключу",
      web: "Поисковики",
    }[pid] || pid
  );
}
function redLine(r) {
  return Object.entries(r || {})
    .map(([k, v]) => `${tr(RED_RU[k] || k)}: ${v}`)
    .join(", ");
}
async function outgoingModal(days) {
  days = days || 7;
  const d = await api("/api/outgoing?days=" + days);
  const pop = document.createElement("div");
  pop.className = "modal outm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  const by = Object.entries(d.by)
    .map(([p, n]) => `${esc(provName(p))} — ${n}`)
    .join(", ");
  const rows = d.events
    .map(
      (e) =>
        `<tr><td>${esc(e.ts.slice(5, 16).replace("T", " "))}</td><td>${esc(provName(e.pid))}</td><td>${esc(tr(PURPOSE_RU[e.purpose] || e.purpose))}</td><td>${fmtN(e.chars)}</td><td>${e.memory_full ? `${fmtN(e.memory_sent)} ${tr("из")} ${fmtN(e.memory_full)}` : "—"}</td><td>${[...(e.hidden_parts || []), ...(e.hidden_tags || [])].map((x) => tr(SCOPE_RU[x] || x)).join(", ") || "—"}</td><td>${redLine(e.redacted) || "—"}</td></tr>`,
    )
    .join("");
  pop.innerHTML = `<div class="card"><h2>${tr("Что ушло наружу")}<span class="hint">${tr("за")} ${days} ${tr("дн.")}</span><button class="mx" id="outx">×</button></h2>
   <div class="outsum"><div><b>${d.requests}</b><span>${tr("запросов к облачным ИИ")}</span></div><div><b>${fmtN(d.memory_kept)}</b><span>${tr("знаков памяти остались на компьютере")}</span></div><div><b>${fmtN(Object.values(d.redacted).reduce((a, b) => a + b, 0))}</b><span>${tr("секретов скрыто")}</span></div></div>
   ${by ? `<p class="hint">${tr("Кому")}: ${by}${Object.keys(d.redacted).length ? ` · ${tr("скрыто")}: ${redLine(d.redacted)}` : ""}</p>` : ""}
   <div class="tg" style="padding:6px 0 10px;border:0"><button class="sw ${d.redact ? "on" : ""}" id="outred"></button><div><b>${tr("Скрывать секреты от облачных ИИ")}</b><p>${tr("Номера карт, пароли, ПИН-коды, ключи, телефоны, паспорта, СНИЛС, ИНН и счета заменяются метками до отправки, в том числе в поиске. Настоящие значения Mnemai возвращает в ответ уже на компьютере. В этот отчёт они тоже не попадают.")}</p></div></div>
   ${rows ? `<div class="outtbl"><table><tr><th>${tr("Когда")}</th><th>${tr("Кому")}</th><th>${tr("Зачем")}</th><th>${tr("Знаков")}</th><th>${tr("Память")}</th><th>${tr("Не видел")}</th><th>${tr("Скрыто")}</th></tr>${rows}</table></div>` : `<p class="hint">${tr("За эти дни ничего не уходило: работала только локальная модель или ты не писал.")}</p>`}
   <p class="hint">${tr("Локальная модель в отчёт не попадает: она на этом компьютере и ничего не отправляет.")}</p></div>`;
  $("#outx", pop).onclick = () => pop.remove();
  $("#outred", pop).onclick = async (ev) => {
    const on = !ev.currentTarget.classList.contains("on");
    await post("/api/agent", { redact: on });
    ev.currentTarget.classList.toggle("on", on);
    refreshStatus();
  };
}
// ---------------------------------------------------------------- meetings: presets Private / Quality / Fast
// the meetings card: the way a meeting goes — recording → transcript → summary → memory — drawn as four steps.
// Each step says what happens and holds its own settings; the presets set the whole way at once.
let SCR_X = { models: [], summary: "", keep: false, step: "text" };
const SCR_PRESETS = [
  [
    "private",
    "🔒",
    "#10b981",
    "#14b8a6",
    "Private",
    [
      ["Где", "Бесплатно на компьютере"],
      ["Кто подводит", "модель на компьютере"],
      ["Хранить аудио", "нет"],
    ],
  ],
  [
    "quality",
    "☁️",
    "#0ea5e9",
    "#6366f1",
    "Quality",
    [
      ["Где", "Облачный Whisper"],
      ["", "≈ $0.36 за час записи"],
    ],
  ],
  [
    "fast",
    "⚡",
    "#f59e0b",
    "#f97316",
    "Fast",
    [
      ["Где", "короткие здесь, длинные в облако"],
      ["", "≈ $0.36 за час длинной записи"],
    ],
  ],
];
// the same names as on the cards below the steps, so the step and its settings read alike
const SCR_WHERE = {
  private: "Бесплатно на компьютере",
  quality: "Облачный Whisper",
  fast: "Короткие — здесь, длинные — в облако",
};
function scribePreset(c) {
  return { private: "private", quality: "quality", fast: "fast" }[c.mode] || "";
}
function scribeFlow(c) {
  const q = (SQ.find((x) => x[0] === c.quality) || SQ[0])[1];
  const hour = c.rtf ? Math.max(1, Math.round(c.rtf * 60)) : 0;
  const mod = SCR_X.models.find((m) => m.v === SCR_X.summary);
  const text =
    `${tr("Где")}: ${tr(SCR_WHERE[c.mode] || "")}` +
    (c.mode !== "quality"
      ? `
${tr("Точность")}: ${tr(q)}`
      : "") +
    (hour && c.mode !== "quality"
      ? `
${tr("час записи ≈")} ${hour} ${tr("мин")}`
      : "");
  const steps = [
    ["rec", "🎙️", "#ec4899", "#f97316", "Запись", `${tr("Хранить аудио")}: ${SCR_X.keep ? tr("да") : tr("нет")}`],
    ["text", "📝", "#0ea5e9", "#6366f1", "Расшифровка", text],
    ["sum", "✨", "#6366f1", "#a855f7", "Итоги", `${tr("Кто подводит")}: ${mod ? mod.l : tr("модель текущего чата")}`],
    ["mem", "🧠", "#10b981", "#14b8a6", "Память", tr("учится на твоих словах")],
  ];
  return `<div class="mflow">${steps
    .map(
      ([k, em, c1, c2, t, v], n) =>
        `${n ? `<i class="mfar"><em></em></i>` : ""}<button class="mfs ${SCR_X.step === k ? "on" : ""}" data-mfs="${k}" style="--c1:${c1};--c2:${c2};--d:${n * 0.08}s"><span class="mfn">${n + 1}</span><span class="medal2"><span>${em}</span></span><b>${tr(t)}</b><small>${esc(v)}</small></button>`,
    )
    .join("")}</div>`;
}
function scribeStep(c) {
  const s = SCR_X.step;
  if (s === "rec")
    return `<p class="mfd">${tr("Mnemai пишет микрофон и звук компьютера двумя дорожками: в расшифровке сразу видно, где ты, а где собеседник, без угадывания по голосу. Можно не записывать, а загрузить готовый файл: mp3, m4a, wav, видео. Всё ложится в папку памяти «80 Meetings», в папку с датой и названием встречи.")} ${tr("Запись длится не дольше 5 часов.")}</p>
   <div class="tg" style="padding:6px 0 0;border:0"><button class="sw ${SCR_X.keep ? "on" : ""}" id="scrkeep"></button><div><b>${tr("Хранить аудио")}</b><p>${tr("Выключено: остаётся только текст, запись удаляется. Включено: файл встречи лежит рядом с расшифровкой.")}</p></div></div>`;
  if (s === "text")
    return `<p class="mfd">${tr("Речь превращается в текст. На компьютере работает Whisper: бесплатно, запись никуда не уходит. Облачный Whisper быстрее и не грузит компьютер, но платный и получает запись. Тишину, выдуманные фразы и эхо из колонок Mnemai вырезает сама.")}</p>
   <div class="shd"><b>${tr("Где")}</b><span class="hint">${tr("где расшифровывать")}</span></div>${scribePlans(c, c.mode, false, true)}
   ${c.mode !== "quality" ? `<div class="shd"><b>${tr("Точность")}</b><span class="hint">${tr("на компьютере")}</span></div>${scribeQuality(c.quality)}` : ""}
   <details class="scrown"><summary>${tr("Облачный Whisper: свой адрес и ключ")}${c.cloud_ready ? ` · ✓ ${tr("готов")}: ${tr(c.cloud_from)}` : ""}</summary><div class="row" style="margin-top:6px"><input class="inp" id="scrbase" placeholder="https://…/v1" value="${esc(c.base || "")}" style="min-width:260px"><input class="inp" id="scrmodel" placeholder="whisper-1" value="${esc(c.model || "")}" style="width:150px"><input class="inp" id="scrkey" type="password" placeholder="${tr("ключ")}" style="width:200px"><button class="btn g sm" id="scrsave">${tr("Сохранить")}</button></div></details>`;
  if (s === "sum")
    return `<p class="mfd">${tr("Готовая расшифровка уходит одним сообщением выбранной модели: о чём встреча, что решили, какие задачи и за кем. Итоги приходят новым разговором в чате — там же можно попросить письмо участникам или план. Локальная модель — бесплатно и без интернета.")}</p>
   <div class="shd"><b>${tr("Кто подводит")}</b><span class="hint">${tr("итоги встречи")}</span></div><select class="inp" id="scrsum" style="max-width:420px"><option value="">${tr("модель текущего чата")}</option>${SCR_X.models.map((m) => `<option value="${esc(m.v)}" ${m.v === SCR_X.summary ? "selected" : ""}>${esc(m.l)}</option>`).join("")}</select>`;
  return `<p class="mfd">${tr("Из встречи Mnemai учится на твоих словах: решения, сроки, договорённости. Слова собеседника — только контекст, за тебя они не записываются. Насколько смело записывать — как в остальном обучении.")}</p>
   <button class="btn g sm" id="scrlearn">${ic("book")}${tr("Настройки обучения")}</button>`;
}
function scribeCard(c) {
  if (!c) return "";
  const pr = scribePreset(c);
  return `<div class="card" data-sec="meetings" id="scrcard"><h2>${tr("Записи встреч")}${hq("scribe")}</h2>
   <p class="hint" style="margin:-4px 0 12px">${tr("Как встреча становится итогами и памятью. Нажми на шаг — ниже его настройки.")}</p>
   <div class="shd"><b>${tr("Готовые настройки")}</b></div><div class="yprs mpres">${SCR_PRESETS.map(
     ([k, em, c1, c2, t, d], n) =>
       `<button class="ypr ${pr === k ? "on" : ""}" data-mpre="${k}" style="--c1:${c1};--c2:${c2};--d:${n * 0.06}s"><span class="medal2"><span>${em}</span><i class="spark"></i><i class="spark"></i><i class="spark"></i></span><span class="yprt"><b>${tr(t)}</b><span>${d.map(([a, b]) => (a ? `${tr(a)}: ${tr(b)}` : tr(b))).join(" · ")}</span></span>${pr === k ? `<span class="yok">${ic("check")}</span>` : ""}</button>`,
   ).join("")}</div>
   <div class="shd"><b>${tr("Как идёт встреча")}</b></div>${scribeFlow(c)}
   <div class="mfpanel" data-step="${SCR_X.step}">${scribeStep(c)}</div></div>`;
}
function bindScribeCard() {
  const c = $("#scrcard");
  if (!c) return;
  tileToggles(c); // «Хранить аудио» looks like every other switch
  const cur = () => bindScribeCard.last;
  const redraw = (d) => {
    if (d) bindScribeCard.last = d;
    if (!cur()) return;
    c.outerHTML = scribeCard(cur());
    bindScribeCard();
  };
  const set = async (patch) => {
    try {
      redraw(await post("/api/scribe/settings", patch));
    } catch (e) {
      toast(e.message);
    }
  };
  const agent = async (patch) => {
    try {
      await post("/api/agent", patch);
    } catch (e) {
      toast(e.message);
    }
  };
  $$("[data-mfs]", c).forEach(
    (b) =>
      (b.onclick = () => {
        SCR_X.step = b.dataset.mfs;
        redraw();
      }),
  );
  $$("[data-mpre]", c).forEach(
    (b) =>
      (b.onclick = async () => {
        const k = b.dataset.mpre;
        if (k === "private") {
          const loc = SCR_X.models.find((m) => m.v.startsWith("local:") || m.v.startsWith("ollama:"));
          if (loc) {
            SCR_X.summary = loc.v;
            await agent({ scribe_summary_model: loc.v });
          }
          SCR_X.keep = false;
          await agent({ scribe_keep_audio: false });
        }
        await set({ mode: k });
        toast(tr("Сохранено"));
      }),
  );
  $$("[data-plan]", c).forEach((b) => (b.onclick = () => set({ mode: b.dataset.plan })));
  $$("[data-sq]", c).forEach((b) => (b.onclick = () => set({ model: b.dataset.sq })));
  if ($("#scrsave", c))
    $("#scrsave", c).onclick = () =>
      set({
        base: $("#scrbase", c).value,
        cloud_model: $("#scrmodel", c).value,
        key: $("#scrkey", c).value,
      });
  if ($("#scrkeep", c))
    $("#scrkeep", c).onclick = async () => {
      SCR_X.keep = !SCR_X.keep;
      await agent({ scribe_keep_audio: SCR_X.keep });
      redraw();
    };
  if ($("#scrsum", c))
    $("#scrsum", c).onchange = async (e) => {
      SCR_X.summary = e.target.value;
      await agent({ scribe_summary_model: SCR_X.summary });
      toast(tr("Сохранено"));
      redraw();
    };
  if ($("#scrlearn", c)) $("#scrlearn", c).onclick = () => viewSettings("learn");
}
// ---------------------------------------------------------------- free sync
function syncLast(l) {
  if (!l || !l.ts) return tr("ещё не синхронизировалось");
  if (l.error) return tr("не вышло") + ": " + l.error;
  return `${l.ts.slice(5, 16).replace("T", " ")} · ${tr("отправлено")} ${l.sent || 0}, ${tr("получено")} ${l.got || 0}${(l.conflicts || []).length ? `, ${tr("обе версии сохранены")}: ${l.conflicts.length}` : ""}`;
}
function syncCard(d) {
  if (!d) return "";
  const on = (k) => d.targets.find((t) => t.kind === k);
  const cloud = (k, name) => {
    const t = on(k),
      path = d.detected[k];
    return `<div class="syncrow"><div><b>${name}</b><span class="hint" data-noi18n>${esc(t ? t.where : path ? path + "\\Mnemai" : "")}</span>${t ? `<span class="hint">${esc(syncLast(t.last))}</span>` : path ? "" : `<span class="hint">${tr("Приложение не найдено на компьютере. Установи его и войди — папка появится сама.")}</span>`}</div>${t ? `<button class="btn g sm" data-sdel="${t.id}">${tr("Отключить")}</button>` : path ? `<button class="btn l sm" data-sadd="${k}">${tr("Включить")}</button>` : `<a class="btn g sm" href="${k === "gdrive" ? "https://www.google.com/drive/download/" : "https://www.dropbox.com/install"}" target="_blank">${tr("Скачать")}</a>`}</div>`;
  };
  const others = d.targets.filter((t) => t.kind === "folder" || t.kind === "station");
  return `<div class="card" data-sec="sync" id="synccard"><h2>${tr("Синхронизация")}${hq("sync")}<span class="hint">${tr("бесплатно")}</span></h2>
   <p class="hint" style="margin-top:0">${tr("Та же память на всех твоих компьютерах. Заметки и разговоры лежат в облаке обычными файлами. Ключи от ИИ не уезжают: они в хранилище Windows.")}</p>
   ${cloud("gdrive", "Google Drive")}${cloud("dropbox", "Dropbox")}
   ${others.map((t) => `<div class="syncrow"><div><b>${esc(tr(t.name))}</b><span class="hint" data-noi18n>${esc(t.where)}</span><span class="hint">${esc(syncLast(t.last))}</span></div><button class="btn g sm" data-sdel="${t.id}">${tr("Отключить")}</button></div>`).join("")}
   <details style="margin-top:10px"><summary class="hint" style="cursor:pointer">${tr("Своя папка или MCP-станция")}</summary>
    <div class="row" style="margin-top:8px"><input class="inp" id="sfold" placeholder="D:\\Облако\\Mnemai" style="min-width:300px"><button class="btn l sm" id="sfadd">${tr("Добавить папку")}</button></div>
    <div class="row" style="margin-top:8px"><input class="inp" id="surl" placeholder="https://mnema.example.com" style="min-width:300px"><input class="inp" id="stok" type="password" placeholder="${tr("ключ синхронизации")}" style="width:220px"><button class="btn l sm" id="ssadd">${tr("Подключить станцию")}</button></div>
    <div class="hint" style="margin-top:6px">${tr("Станция — твой сервер с копией памяти: компьютеры синхронизируются через неё, а любой агент подключается к памяти по MCP со своим ключом. Запуск на сервере")}: <code data-noi18n>mnema station --host 0.0.0.0</code></div></details>
   <div class="row" style="margin-top:12px"><button class="btn sm" id="snow" ${d.targets.length ? "" : "disabled"}>${tr("Синхронизировать сейчас")}</button><span class="hint">${tr("Сама — каждые")}</span><select class="inp" id="smin" style="width:auto">${[5, 10, 15, 30, 60].map((m) => `<option value="${m}" ${m === d.minutes ? "selected" : ""}>${m} ${tr("мин")}</option>`).join("")}</select></div></div>`;
}
function bindSyncCard() {
  const c = $("#synccard");
  if (!c) return;
  const redraw = (d) => {
    c.outerHTML = syncCard(d);
    bindSyncCard();
  };
  const go = async (path, body, msg) => {
    try {
      const d = await post("/api/sync/" + path, body || {});
      redraw(d);
      if (msg) toast(msg);
    } catch (e) {
      toast(e.message);
    }
  };
  $$("[data-sadd]", c).forEach(
    (b) => (b.onclick = () => go("add", { kind: b.dataset.sadd }, tr("Синхронизация включена"))),
  );
  $$("[data-sdel]", c).forEach((b) => (b.onclick = () => go("remove", { id: b.dataset.sdel })));
  $("#sfadd", c).onclick = () => {
    const v = $("#sfold", c).value.trim();
    if (!v) {
      toast(tr("Укажи папку для синхронизации"));
      $("#sfold", c).focus();
      return;
    }
    go("add", { kind: "folder", path: v }, tr("Папка добавлена"));
  };
  $("#ssadd", c).onclick = () => {
    const u = $("#surl", c).value.trim(),
      k = $("#stok", c).value.trim();
    if (!u || !k) {
      toast(tr("Укажи адрес станции и ключ"));
      $(u ? "#stok" : "#surl", c).focus();
      return;
    }
    go("add", { kind: "station", url: u, token: k }, tr("Станция подключена"));
  };
  $("#snow", c).onclick = (e) => {
    e.currentTarget.disabled = true;
    e.currentTarget.textContent = tr("синхронизирую…");
    go("now", {});
  };
  $("#smin", c).onchange = (e) => go("minutes", { minutes: +e.target.value });
}
