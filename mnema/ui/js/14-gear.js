// ---------------------------------------------------------------- the gear: learning, theme, language, tutorial, achievements
function statusText() {
  if ((CHAT.chat && CHAT.chat.private) || (!CHAT.id && CHAT.newPrivate))
    return tr("Без обучения — этот разговор Mnemai не запоминает");
  if (!STATUS.label) return tr("Напиши что угодно — я помню тебя и учусь по ходу");
  return STATUS.label + (STATUS.when ? " · " + STATUS.when : "");
}
function statusLine() {
  const i = $("#inp");
  if (i && !compCfg().placeholder) i.placeholder = statusText();
}
function achOn() {
  return LS.get("ach_on", true);
}
function applyAch() {
  const on = achOn(),
    b = $("#achbtn");
  if (b) b.hidden = !on;
  document.body.classList.toggle("noach", !on);
}
function drawGear() {
  let b = $("#gearbtn");
  if (!b) {
    topRight().querySelector("#gslot").innerHTML =
      `<button id="gearbtn" class="gearbtn" data-menu title="${tr("Обучение, тема, язык, туториал")}">${ic("gear")}<i class="gdot"></i><em class="gq" hidden></em></button>`;
    b = $("#gearbtn");
    b.onclick = (e) => gearMenu(e.currentTarget);
  }
  // a conversation without learning: the dot turns orange while it is open
  const priv = !!$("#msgs") && typeof isPrivate === "function" && isPrivate();
  $(".gdot", b).className = "gdot " + (priv ? "priv" : STATUS.dot || "");
  b.title = priv ? tr("Без обучения — этот разговор Mnemai не запоминает") : tr("Обучение, тема, язык, туториал");
  const q = $(".gq", b);
  q.hidden = true;
  if ($(".gearm")) gearFill($(".gearm"));
}
function gearMenu(anchor) {
  if ($(".gearm")) {
    $(".gearm").remove();
    return;
  }
  closeMenus();
  MENU_ANCHOR = anchor;
  const m = document.createElement("div");
  m.className = "menu gearm";
  document.body.appendChild(m);
  gearFill(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.right - m.offsetWidth)) + "px";
  m.style.top = r.bottom + 8 + "px";
  refreshStatus();
}
function gearFill(m) {
  const { ls } = STATUS,
    s = ls ? ls.settings : {},
    cur = s.paused ? "pause" : (Object.values(s.sources || {}).find((x) => x.enabled) || {}).mode || "mixed",
    th = themeCfg().mode,
    lg = LANGS.find((x) => x[0] === I18N.lang) || LANGS[0];
  // the memory itself is switched in one place, the memory block on the left; here only learning can pause
  m.innerHTML = `<div class="ghead"><span class="ld ${STATUS.dot || ""}"></span><div><b>${esc(STATUS.label || tr("Mnemai учится"))}</b><small>${esc(STATUS.when || "")}</small></div>${MEM.on ? `<button class="sw ${s.paused ? "" : "on"}" id="glon" title="${tr(s.paused ? "Продолжить обучение" : "Поставить обучение на паузу")}"></button>` : ""}</div>
    <div class="gmodes ${MEM.on ? "" : "dimmed"}">${QUICK.filter((q) => q[0] !== "pause")
      .map(
        ([k, t, d]) =>
          `<button data-q="${k}" class="${k === cur ? "cur" : ""}" ${s.paused ? "disabled" : ""}><i></i><span><b>${tr(t)}</b><small>${tr(d)}</small></span></button>`,
      )
      .join("")}</div>
    <div class="gsep"></div>
    <div class="gline"><span>${tr("Тема")}</span><div class="gseg">${[
      ["light", "sun", "Светлая"],
      ["dark", "moon", "Тёмная"],
      ["system", "auto", "Как в Windows"],
    ]
      .map(([k, i, t]) => `<button data-th="${k}" class="${k === th ? "on" : ""}" title="${tr(t)}">${ic(i)}</button>`)
      .join(
        "",
      )}<button data-th="custom" class="${th === "custom" ? "on" : ""}" title="${tr("Своя")}">${ic("palette")}</button></div></div>
    <div class="gline"><span>${tr("Язык")}</span><button class="glang" data-g="lang" data-noi18n>${flagSvg(lg[0])}<span>${lg[1]}</span>${ic("chev")}</button></div>
    <div class="gline"><span>${tr("Достижения")}</span><button class="sw ${achOn() ? "on" : ""}" id="gach"></button></div>
    ${LS.get("costtip", true) === false ? `<div class="gline"><span>${tr("Совет о дорогом разговоре")}</span><button class="sw" id="gcost"></button></div>` : ""}
    ${LS.get("tour", true) ? "" : `<div class="gline"><span>${tr("Туториал в новых разговорах")}</span><button class="sw" id="gtour"></button></div><button class="gbig" data-g="tour">${ic("book")}<span>${tr("Как устроена Mnemai")}</span><small>${tr("6 шагов, минута")}</small></button>`}
    <button class="gbig" data-g="memtour">${ic("lock")}<span>${tr("Как работает память")}</span><small>${tr(`${MEMTOUR.length} шагов`)}</small></button>
    <button class="gbig" data-g="kb">${ic("book")}<span>${tr("Справочник Mnemai")}</span><small>${tr("как всё устроено")}</small></button>
    <button class="gbig" data-g="settings">${ic("set")}<span>${tr("Все настройки")}</span></button>`;
  if ($("#glon", m))
    $("#glon", m).onclick = async (e) => {
      const on = !e.currentTarget.classList.contains("on");
      e.currentTarget.classList.toggle("on", on);
      await post("/api/learn/settings", { paused: !on });
      refreshStatus();
    };
  $$("[data-q]", m).forEach(
    (b) =>
      (b.onclick = async () => {
        await post("/api/agent", { simple: { autonomy: b.dataset.q } });
        refreshStatus();
      }),
  );
  $$("[data-th]", m).forEach(
    (b) =>
      (b.onclick = () => {
        const k = b.dataset.th;
        if (k === "custom") {
          m.remove();
          setTheme({ mode: "custom" });
          goSet("app/themecard");
          return;
        }
        setTheme({ mode: k });
        gearFill(m);
      }),
  );
  if ($("#gcost", m))
    $("#gcost", m).onclick = (e) => {
      LS.set("costtip", true);
      e.currentTarget.classList.add("on");
      setTimeout(() => {
        m.remove();
        if (CHAT.chat && $("#msgs")) renderChat(CHAT.chat);
      }, 250);
    };
  if ($("#gtour", m))
    $("#gtour", m).onclick = () => {
      m.remove();
      setTour(true);
    };
  $("#gach", m).onclick = (e) => {
    const on = !achOn();
    LS.set("ach_on", on);
    e.currentTarget.classList.toggle("on", on);
    applyAch();
    drawAchCard();
    toast(on ? tr("Достижения включены") : tr("Достижения выключены: ни наград, ни раздела"));
  };
  $$("[data-g]", m).forEach(
    (b) =>
      (b.onclick = () => {
        const g = b.dataset.g;
        if (g === "lang") {
          m.remove();
          langMenu($("#gearbtn"));
          return;
        }
        m.remove();
        ({
          feed: () => toggleDrawer(true),
          queue: () => go("memory"),
          learn: () => goSet("learn/c-learn"),
          tour: () => tourModal(),
          memtour: () => memTour(),
          kb: () => kbModal(),
          settings: () => go("settings"),
        })[g]();
      }),
  );
}
const TOUR_STEPS = [
  [
    "Одна память для всех ИИ",
    "Пишешь здесь любой модели — она уже знает, кто ты, над чем работаешь и как с тобой говорить. Меняешь модель — память та же.",
    "memory",
    "Открыть память",
  ],
  [
    "Всё лежит у тебя",
    "Память — обычные файлы Markdown в папке на этом компьютере. Их можно открыть, поправить или удалить. В облако что-то уходит, только если ты сам выбрал облачную модель.",
    "folder",
    "Открыть папку",
  ],
  [
    "Учится сама, по ходу разговора",
    "Замечает факты о тебе. Уверенное записывает сама, спорное спрашивает. Что поняла и почему — в шестерёнке справа вверху. Разговор «без обучения» ничему её не учит.",
    "feed",
    "Показать ленту",
  ],
  [
    "Модель выбираешь ты",
    "Встроенная работает на компьютере бесплатно и без интернета. Claude и ChatGPT подключаются подпиской или ключом, Gemini — ключом. Переключатель — слева вверху.",
    "model",
    "Выбрать модель",
  ],
  [
    "Документы и интернет",
    "Прикрепи PDF, Excel, Word или презентацию — читаю на компьютере и отдаю модели только нужные места. Кнопка «Интернет» разрешает искать в авторитетных источниках, когда вопрос про внешние факты.",
    "file",
    "Прикрепить файл",
  ],
  [
    "Настрой под себя",
    "Разделы слева: модели, как отвечает, обучение, безопасность, движок, встречи, программа. Любая ссылка в программе ведёт прямо к нужному блоку.",
    "settings",
    "Открыть настройки",
  ],
];
// with memory off the first steps say so and offer to turn it on
function tourSteps() {
  if (MEM.on) return TOUR_STEPS;
  const t = TOUR_STEPS.slice();
  t[0] = [
    "Память выключена",
    "Сейчас это обычный чат: модель не знает, кто ты, и ничего не запоминается. Включи — и любая модель будет знать тебя, а сменишь модель — память та же.",
    "memon",
    "Включить память",
  ];
  t[2] = [
    "Учится сама, когда память включена",
    "Тогда Mnemai замечает факты о тебе, уверенное записывает сама, спорное спрашивает. Сейчас память выключена — ничего не записывается.",
    "feed",
    "Показать ленту",
  ];
  return t;
}
function tourModal() {
  const pop = document.createElement("div");
  pop.className = "modal tourm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  pop.innerHTML = `<div class="tour"><div class="tc"><button class="lmx" data-x>×</button><h3>${tr("Как устроена Mnemai")}</h3><div class="sub">${tr("6 шагов, минута чтения")}</div>${tourSteps()
    .map(
      ([b, t, a, l], i) =>
        `<div class="st"><span class="n">${i + 1}</span><div><b>${esc(tr(b))}</b><p>${esc(tr(t))}</p></div><button data-tour="${a}">${esc(tr(l))}</button></div>`,
    )
    .join("")}</div></div>`;
  const TA = {
    memory: () => go("memory"),
    folder: () => post("/api/memory/open", {}).catch((e) => toast(e.message)),
    feed: () => toggleDrawer(true),
    model: () => {
      go("chat");
      setTimeout(() => modelMenu($("#model")), 300);
    },
    file: () => {
      go("chat");
      setTimeout(() => $("#fpick").click(), 300);
    },
    settings: () => go("settings"),
    memon: () => memSet(true),
  };
  $("[data-x]", pop).onclick = () => pop.remove();
  $$("[data-tour]", pop).forEach(
    (b) =>
      (b.onclick = () => {
        pop.remove();
        TA[b.dataset.tour]();
      }),
  );
}

// «Справочник Mnemai»: the knowledge base Mnemai answers from about itself, sections on the left, search on top
async function kbModal(q0) {
  let secs = [];
  try {
    secs = (await api("/api/knowledge")).sections || [];
  } catch (e) {
    toast(e.message);
    return;
  }
  if (!secs.length) return toast(tr("Справочник не найден"));
  const pop = document.createElement("div");
  pop.className = "modal kbm";
  pop.innerHTML = `<div class="card kbc"><div class="kbh"><span class="kbic">${ic("book")}</span><div><h2>${tr("Справочник Mnemai")}</h2><small>${tr("Как устроена и работает Mnemai. По нему она отвечает на вопросы о себе.")}</small></div><button class="lmx" data-x>×</button></div>
    <div class="kbs">${ic("search")}<input id="kbq" placeholder="${tr("Поиск по справочнику")}" value="${esc(q0 || "")}"></div>
    <div class="kbb"><nav class="kbn" id="kbn"></nav><article class="kbt" id="kbt"></article></div></div>`;
  document.body.appendChild(pop);
  const close = () => {
    pop.remove();
    removeEventListener("keydown", key);
  };
  const key = (e) => {
    if (e.key === "Escape") close();
  };
  addEventListener("keydown", key);
  pop.onclick = (e) => {
    if (e.target === pop) close();
  };
  $$("[data-x]", pop).forEach((b) => (b.onclick = close));
  let cur = 0;
  const show = (k, q) => {
    cur = k;
    $$("#kbn button", pop).forEach((b) => b.classList.toggle("on", +b.dataset.k === k));
    const t = $("#kbt", pop);
    t.innerHTML = `<div class="md">${md(secs[k].text.replace(/^## /, "# "))}</div>`;
    if (q) {
      const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
      const w = document.createTreeWalker(t, NodeFilter.SHOW_TEXT);
      const hits = [];
      const one = new RegExp(re.source, "i");
      while (w.nextNode()) if (one.test(w.currentNode.nodeValue)) hits.push(w.currentNode);
      hits.forEach((n) => {
        const s = document.createElement("span");
        s.innerHTML = esc(n.nodeValue).replace(re, (m) => `<mark>${m}</mark>`);
        n.replaceWith(s);
      });
      const m = $("mark", t);
      if (m) m.scrollIntoView({ block: "center" });
    } else t.scrollTop = 0;
    t.classList.remove("kbin");
    void t.offsetWidth;
    t.classList.add("kbin");
  };
  const list = (q) => {
    const ql = (q || "").trim().toLowerCase();
    const idx = secs
      .map((s, k) => k)
      .filter((k) => !ql || secs[k].text.toLowerCase().includes(ql))
      .sort((a, b) => (ql ? secs[b].title.toLowerCase().includes(ql) - secs[a].title.toLowerCase().includes(ql) : 0));
    $("#kbn", pop).innerHTML = idx.length
      ? idx
          .map(
            (k) =>
              `<button data-k="${k}" style="--d:${Math.min(idx.indexOf(k), 20) * 0.015}s">${esc(secs[k].title)}</button>`,
          )
          .join("")
      : `<div class="hint" style="padding:8px">${tr("Ничего не нашла")}</div>`;
    $$("#kbn button", pop).forEach((b) => (b.onclick = () => show(+b.dataset.k, ql)));
    if (idx.length) show(idx.includes(cur) && !ql ? cur : idx[0], ql);
    else $("#kbt", pop).innerHTML = "";
  };
  $("#kbq", pop).oninput = (e) => list(e.target.value);
  list(q0);
  setTimeout(() => $("#kbq", pop).focus(), 50);
}
