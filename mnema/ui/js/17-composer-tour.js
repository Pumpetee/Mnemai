// ---------------------------------------------------------------- «?» over the input line: a spotlight walks over every button
const COMP_TOUR = [
  [
    "#inp",
    "Поле ввода",
    "Пиши как человеку. Здесь же видно, учится ли Mnemai и когда обновилась память. Enter — отправить, Shift+Enter — новая строка.",
    "💬",
  ],
  [
    "#clip",
    "Скрепка",
    "Файл, скриншот из буфера, заметка из памяти или страница по ссылке. Файл можно и просто перетащить в поле или вставить Ctrl+V.",
    "📎",
  ],
  ["#plusb", "Ещё", "Запись встречи, расшифровка аудио, подсказки к терминам и другие действия.", "➕"],
  ["#privchip", "Без обучения", "Включи, и этот разговор ничему не научит память — для личного или разового.", "🙈"],
  [
    "#conschip",
    "Консорциум",
    "Совет из нескольких ИИ: каждый отвечает, проверяет других, в конце — общий ответ. Работает и в уже идущем разговоре.",
    "👥",
  ],
  [
    "#ccfg",
    "Настроить строку",
    "Какие кнопки показывать и в каком порядке, высота поля, отправка Enter или Ctrl+Enter.",
    "⚙️",
  ],
  ["#micb", "Голос", "Нажми и говори — Mnemai напишет текст. Отсюда же запись встреч: расшифровка и итоги.", "🎙️"],
  [
    "#send",
    "Отправить",
    "Пока ИИ отвечает, это кнопка «Стоп». В консорциуме она останавливает того, кто говорит.",
    "➤",
  ],
];
function compTour() {
  const steps = COMP_TOUR.filter(([sel]) => {
    const e = $(sel);
    return e && e.offsetParent !== null;
  });
  if (!steps.length) return;
  let k = 0;
  const ov = document.createElement("div");
  ov.className = "ctour";
  ov.innerHTML = '<div class="ctspot"></div><div class="ctcard"></div>';
  document.body.appendChild(ov);
  const spot = $(".ctspot", ov),
    card = $(".ctcard", ov);
  const close = () => {
      ov.classList.add("out");
      setTimeout(() => ov.remove(), 250);
      removeEventListener("keydown", key);
      removeEventListener("resize", place);
    },
    key = (e) => {
      if (e.key === "ArrowRight" || e.key === "Enter") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "Escape") close();
    };
  addEventListener("keydown", key);
  addEventListener("resize", () => place());
  const go = (d) => {
    k += d;
    if (k >= steps.length) return close();
    k = Math.max(0, k);
    place();
  };
  function place() {
    const [sel, t, d, emo] = steps[k],
      el = $(sel);
    if (!el) return;
    const r = el.getBoundingClientRect(),
      pad = sel === "#inp" ? 6 : 5;
    spot.style.cssText = `left:${r.left - pad}px;top:${r.top - pad}px;width:${r.width + pad * 2}px;height:${r.height + pad * 2}px`;
    card.innerHTML = `<div class="ctemo">${emo}</div><div class="ctstep">${k + 1} / ${steps.length}</div><b>${tr(t)}</b><p>${tr(d)}</p><div class="ctdots">${steps.map((_, i) => `<i class="${i === k ? "on" : i < k ? "done" : ""}"></i>`).join("")}</div>
      <div class="ctnav"><button class="btn g sm" data-x>${tr("Закрыть")}</button><span>${k ? `<button class="btn g sm" data-p>←</button>` : ""}<button class="btn sm" data-n>${k === steps.length - 1 ? tr("Понятно") : tr("Дальше") + " →"}</button></span></div>`;
    card.classList.remove("ctin");
    void card.offsetWidth;
    card.classList.add("ctin");
    const cw = 330,
      ch = card.offsetHeight || 200;
    let left = Math.min(innerWidth - cw - 12, Math.max(12, r.left + r.width / 2 - cw / 2)),
      top = r.top - ch - 22;
    if (top < 12) top = r.bottom + 22;
    card.style.left = left + "px";
    card.style.top = top + "px";
    card.style.setProperty("--ax", Math.max(18, Math.min(cw - 18, r.left + r.width / 2 - left)) + "px");
    $("[data-x]", card).onclick = close;
    $("[data-n]", card).onclick = () => go(1);
    if ($("[data-p]", card)) $("[data-p]", card).onclick = () => go(-1);
  }
  ov.onclick = (e) => {
    if (e.target === ov || e.target === spot) go(1);
  };
  requestAnimationFrame(() => {
    ov.classList.add("in");
    place();
  });
}
