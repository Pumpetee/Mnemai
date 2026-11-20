// ---------------------------------------------------------------- meetings: how to transcribe, as presets — what it costs, how fast, where the audio goes
// Cloud price: OpenAI whisper-1, $0.006 per minute (OpenAI price list) → $0.36 per hour of recording.
function scribePlans(sc, mode, compact, bare) {
  const hour = sc.rtf ? Math.max(1, Math.round(sc.rtf * 60)) : 0,
    spd = hour ? tr("час записи ≈") + " " + hour + " " + tr("мин") : tr("замерю на первой записи");
  const P = [
    [
      "private",
      "🔒",
      "Private",
      "free",
      "Бесплатно",
      [
        ["💰", "0 ₽"],
        ["⏱", spd],
        ["🔒", tr("только локальные модели: запись не уходит с компьютера")],
      ],
    ],
    [
      "quality",
      "☁️",
      "Quality",
      "paid",
      "Платно",
      [
        ["💰", tr("≈ $0.36 за час записи, по твоему ключу")],
        ["⏱", tr("качественная расшифровка, компьютер не грузит")],
        ["☁️", tr("запись уходит в облако")],
      ],
    ],
    [
      "fast",
      "⚡",
      "Fast",
      "mix",
      "Частично платно",
      [
        ["💰", tr("что не успевает компьютер — ≈ $0.36 за час")],
        ["⏱", tr("не дольше самой встречи")],
        ["☁️", tr("длинные записи уходят в облако")],
      ],
    ],
  ];
  const LOOK = {
    private: ["#10b981", "#14b8a6"],
    quality: ["#0ea5e9", "#6366f1"],
    fast: ["#f59e0b", "#f97316"],
  };
  const ul = (rows) =>
    `<ul>${rows.map(([i, x]) => `<li>${ic({ "💰": "coin", "⏱": "clock", "🔒": "lock", "☁️": "cloud" }[i])}<span>${x}</span></li>`).join("")}</ul>`;
  return `<div class="splans ${compact ? "cmp" : ""}">${P.map(
    (
      [k, icn, t, cls, tag, rows],
      n,
    ) => `<button class="splan ${k === mode ? "on" : ""}" data-plan="${k}" style="--d:${n * 0.05}s;--c1:${LOOK[k][0]};--c2:${LOOK[k][1]}"><span class="medal2 spi"><span>${icn}</span></span><b>${tr(t)}</b><em class="stag ${cls}">${tr(tag)}</em>
    ${compact || bare ? "" : ul(rows)}${k === mode ? `<i class="spck">${ic("check")}</i>` : ""}</button>`,
  ).join("")}</div>${compact ? `<div class="spdet">${ul((P.find((x) => x[0] === mode) || P[0])[5])}</div>` : ""}
    ${(mode === "quality" || mode === "fast") && !sc.cloud_ready ? `<div class="snokey">${ic("x")}${tr("Для облака нужен ключ OpenAI или свой адрес — без него расшифрую на компьютере бесплатно.")}</div>` : ""}`;
}
const SQ_MED = {
  auto: ["🤖", "#6366f1", "#a855f7"],
  small: ["⚡", "#f59e0b", "#eab308"],
  medium: ["🎯", "#10b981", "#14b8a6"],
  "large-v3": ["🏆", "#ec4899", "#a855f7"],
};
const SQ = [
  ["auto", "Авто", "сама выберет: «Точнее», если уже скачана", 0, 0, ""],
  ["small", "Быстрее", "для чистого звука и одного голоса", 2, 4, "464 МБ"],
  ["medium", "Точнее", "шум, несколько голосов, термины", 3, 2, "1,5 ГБ"],
  ["large-v3", "Максимум", "самое точное, нужен мощный компьютер", 4, 1, "≈ 3 ГБ"],
];
function scribeQuality(q) {
  const dots = (n, c) =>
    `<span class="sqd ${c}">${[1, 2, 3, 4].map((i) => `<i class="${i <= n ? "f" : ""}"></i>`).join("")}</span>`;
  return `<div class="sqs">${SQ.map(
    ([
      k,
      t,
      d,
      acc,
      sp,
      size,
    ]) => `<button class="sq ${k === q ? "on" : ""}" data-sq="${k}" title="${esc(tr(d))}" style="--c1:${SQ_MED[k][1]};--c2:${SQ_MED[k][2]}"><span class="medal2 sqmd"><span>${SQ_MED[k][0]}</span></span><b>${tr(t)}</b>
    ${acc ? `<div class="sqm"><span>${tr("точность")}</span>${dots(acc, "a")}</div><div class="sqm"><span>${tr("скорость")}</span>${dots(sp, "s")}</div><em>${size} · ${tr("бесплатно")}</em>` : `<small>${tr(d)}</small><em>${tr("бесплатно")}</em>`}</button>`,
  ).join("")}</div>`;
}
