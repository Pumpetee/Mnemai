// ---------------------------------------------------------------- chat
const CHAT = {
  id: "",
  model: "",
  polling: null,
  feedSince: "",
  feedTimer: null,
  open: new Set(),
  files: [],
  tab: LS.get("ptab", "feed"),
  detail: LS.get("detail", false),
  newPrivate: false,
  chat: null,
};
// while there are no words yet: three dots, no "Claude думает" (who speaks is shown only in a consortium)
const TYPING = '<span class="typing"><i></i><i></i><i></i></span>',
  QUIET_PHASE = new Set(["", "думаю", "пишу"]);
const SEND_ICON = '<svg viewBox="0 0 24 24"><path d="M3 20l18-8L3 4v6l12 2-12 2z"/></svg>';
async function viewChat(id) {
  const [cl, mdl] = await Promise.all([api("/api/chats"), api("/api/models")]);
  CHAT.model = CHAT.model || cl.default_model;
  const opts = mdl.providers
    .filter((p) => p.ready)
    .flatMap((p) =>
      p.models.map((m) => ({
        v: p.id + ":" + m.id,
        l: (p.id === "claude_code" ? "" : p.id === "local" ? "На компьютере · " : p.name + " · ") + m.name,
      })),
    );
  if (!opts.find((o) => o.v === CHAT.model) && opts.length) CHAT.model = opts[0].v;
  if (!window.__warmed) {
    window.__warmed = 1;
    setTimeout(() => warmLocal(CHAT.model), 1500);
  }
  const L = LS.get("left", true);
  $("#view").innerHTML = `<div class="chat ${L ? "" : "noleft"}" id="chatgrid">
   <aside class="side"><div class="side-h"><div class="sidebtns"><button class="newbtn" id="newc">${ic("plus")}Новый разговор</button><button class="sessbtn" id="news">${ic("session")}<span>Новая сессия</span></button></div><div class="sidecol"><button class="ib" id="hideleft" title="Скрыть список">${ic("left")}</button><button class="sessq" id="sessq" title="${tr("Чем отличаются разговор и сессия")}"><i>?</i></button></div></div>
     <div class="search">${ic("search")}<input id="csearch" placeholder="Поиск по разговорам"></div><div class="sortrow"><div class="sortbar" id="sortbar"><button data-sort="date">по дате</button><button data-sort="tokens">по токенам</button></div><button class="aibtn" id="aibtn" data-menu title="Показать разговоры с одним ИИ"><span id="ailbl">ИИ</span>${ic("chev")}</button></div><div class="clist" id="clist"></div><div class="localcard" id="localcard"></div></aside>
   <section class="main"><div class="top">
     <button class="ib" id="tleft" title="Список разговоров" ${L ? "hidden" : ""}>${ic("left")}</button>
     <button class="modelpill" id="model" data-menu title="Модель"><span class="mdot"></span><span class="mtxt"><b id="mlabel"></b><small id="mfree"></small></span>${ic("chev")}${hq("models")}</button><button class="heatpill" id="heat" data-menu hidden data-level="idle">${ic("thermo")}<i class="hdot"></i>${hq("heat")}</button>
     <div class="tcenter"><div class="title" id="ctitle" title="${tr("Нажми дважды, чтобы переименовать")}"></div><span class="tside"><button class="ib rename" id="crn" title="Переименовать">${ic("edit")}</button><span id="privtag"></span></span></div>
</div>
     <div id="ctable"></div><div class="msgs" id="msgs"></div>
     <div class="composer" id="composer"><div id="recbar"></div><div class="cbox"><button class="hq chelp" id="chelp" title="${tr("Что умеет строка ввода")}">?</button><button class="ccfg" id="ccfg" title="Настроить строку ввода">${ic("gear")}</button><div class="qbar" id="qbar" hidden></div><div class="fbar" id="fbar" hidden></div><textarea id="inp" rows="1" placeholder="Напиши что угодно — я помню тебя и учусь по ходу" title="Enter — отправить, Shift+Enter — новая строка"></textarea>
       <div class="cbar"><button class="ib" id="clip" title="Прикрепить файл">${ic("clip")}</button><input type="file" id="fpick" multiple hidden>
       <input type="file" id="apick" accept="audio/*,video/*,.m4a,.ogg,.opus,.amr" hidden>
       <button class="ib tog ${LS.get("web", true) ? "on" : ""}" id="webchip" title="Интернет — когда вопрос про внешние факты">${ic("globe")}</button>
       <button class="ib" id="plusb" data-menu title="Ещё">${ic("plus")}<i class="pdot" hidden></i></button>
       <button class="cchip" id="privchip" title="Этот разговор не учит память">${ic("eyeoff")}<span>Без обучения</span></button>
       <button class="cchip" id="conschip" title="Несколько ИИ обсуждают вопрос">${ic("users")}<span>Консорциум</span><i class="cgear" id="consgear" title="${tr("Настройки консорциума")}">${ic("gear")}</i></button>
       <span class="cstate" id="cstate"></span>
       <button class="micbig" id="micb" data-menu title="Голос">${ic("mic")}</button><button class="send" id="send" title="Отправить">${SEND_ICON}</button></div></div></div></section>
   </div><aside class="panel drawer" id="panel" hidden></aside>`;
  $("#newc").onclick = () => {
    CHAT.pendingCons = null;
    viewChat();
  };
  $("#sessq").onclick = () => sessExplain();
  $("#news").onclick = async () => {
    await post("/api/session/new", {});
    CHAT.pendingCons = null;
    viewChat();
  };
  $("#plusb").onclick = (e) => plusMenu(e.currentTarget);
  $("#heat").onclick = (e) => heatMenu(e.currentTarget);
  heatPoll();
  $("#privchip").onclick = async () => {
    if (!MEM.on) return toast(tr("Память выключена — разговоры и так ничего не учат"));
    await togglePrivate();
    drawChips();
  };
  // the chip opens the simple view, its gear — the full settings
  $("#conschip").onclick = (e) => consortModal(!!e.target.closest("#consgear"));
  drawChips();
  $("#ccfg").onclick = () => compModal();
  $("#chelp").onclick = () => compTour();
  applyComposer();
  document.body.classList.toggle("noterms", !LS.get("terms", true));

  $("#composer").addEventListener("mousedown", (e) => {
    if (!e.target.closest("button,input,label,.qbar,.fbar,#recbar") && e.target.id !== "inp") {
      e.preventDefault();
      $("#inp").focus();
    }
  });
  $("#webchip").onclick = (e) => {
    const on = !LS.get("web", true);
    LS.set("web", on);
    e.currentTarget.classList.toggle("on", on);
    drawState();
  };
  $("#hideleft").onclick = () => setLeft(false);
  $("#tleft").onclick = () => setLeft(true);
  if (L) sideGrip();

  CHAT.providers = mdl.providers;
  drawModelLabel();
  $("#model").onclick = (e) => (CHAT.cons ? consortModal() : modelMenu(e.currentTarget));
  let st;
  $("#csearch").oninput = (e) => {
    clearTimeout(st);
    st = setTimeout(() => drawList(e.target.value), 200);
  };
  const inp = $("#inp");
  inp.oninput = () => {
    inp.style.height = "auto";
    inp.style.height = Math.min(240, inp.scrollHeight) + "px";
  };
  inp.onkeydown = (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (e.key !== "Enter" || e.isComposing) return;
    const ctrl = compCfg().send === "ctrl";
    if (ctrl ? e.ctrlKey || e.metaKey : !e.shiftKey) {
      e.preventDefault();
      sendMsg();
    }
  };
  $("#send").onclick = () =>
    CHAT.polling
      ? CHAT.cons && !$("#inp").value.trim()
        ? consAct("pause")
        : CHAT.cons
          ? sendMsg()
          : post("/api/chat/stop", { chat: CHAT.id }).then(() => $("#inp").focus())
      : sendMsg();
  CHAT.files = [];
  drawFiles();
  setQuote("");
  $("#clip").setAttribute("data-menu", "");
  $("#clip").onclick = (e) => clipMenu(e.currentTarget);
  $("#fpick").onchange = (e) => {
    const fs = [...e.target.files];
    e.target.value = "";
    addFiles(fs);
  };
  $("#micb").onclick = (e) => micMenu(e.currentTarget);
  $("#apick").onchange = (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (f) scribeImport(f);
  };
  scribeWatch();
  const comp = $("#composer");
  comp.ondragover = (e) => {
    e.preventDefault();
    comp.classList.add("drag");
  };
  comp.ondragleave = () => comp.classList.remove("drag");
  comp.ondrop = (e) => {
    e.preventDefault();
    comp.classList.remove("drag");
    addFiles([...e.dataTransfer.files]);
  };
  inp.onpaste = (e) => {
    const fs = [...((e.clipboardData || {}).files || [])];
    if (fs.length) {
      e.preventDefault();
      addFiles(fs);
    }
  };

  $("#ctitle").ondblclick = renameInline;
  $("#crn").onclick = renameInline;
  clearInterval(CHAT.polling);
  CHAT.polling = null;
  CHAT.id = id || "";
  if (CHAT.id) LS.set("lastchat", CHAT.id); // «Чаты» on the rail comes back here
  CHAT.chat = null;
  CHAT.newPrivate = false;
  CHAT.pendingTitle = "";
  CHAT.cons = id ? null : CHAT.pendingCons || null;
  CHAT.pendingCons = null;
  drawModelLabel();
  drawList("");
  let c = null;
  const known = !CHAT.id || !cl.chats || cl.chats.some((x) => x.id === CHAT.id); // deleted meanwhile: not asked for
  if (CHAT.id && known) c = await api("/api/chat?id=" + CHAT.id).catch(() => null);
  if (c) {
    renderChat(c);
    const s2 = await api("/api/chat/poll?id=" + CHAT.id);
    if (!s2.done) poll();
  } else {
    if (CHAT.id) LS.set("lastchat", ""); // deleted meanwhile: a new conversation instead
    CHAT.id = "";
    renderEmpty();
  }
  drawPrivate();
  refreshStatus();
  inp.focus();
}
function sideGrip() {
  const g = $("#chatgrid");
  if (!g) return;
  const w = LS.get("sidew", 268);
  g.style.setProperty("--lw", w + "px");
  const side = $(".side", g);
  if (!side || $(".sgrip", side)) return;
  const h = document.createElement("div");
  h.className = "sgrip";
  h.title = tr("Потяни, чтобы изменить ширину");
  side.appendChild(h);
  h.onmousedown = (e) => {
    e.preventDefault();
    const x0 = e.clientX,
      w0 = side.getBoundingClientRect().width;
    g.classList.add("resizing");
    document.body.style.cursor = "col-resize";
    const mv = (ev) => {
      const nw = Math.max(200, Math.min(520, w0 + ev.clientX - x0));
      g.style.setProperty("--lw", nw + "px");
    };
    const up = () => {
      removeEventListener("mousemove", mv);
      removeEventListener("mouseup", up);
      g.classList.remove("resizing");
      document.body.style.cursor = "";
      LS.set("sidew", Math.round(side.getBoundingClientRect().width));
      setTimeout(fitTitle, 0);
    };
    addEventListener("mousemove", mv);
    addEventListener("mouseup", up);
  };
  h.ondblclick = () => {
    LS.set("sidew", 268);
    g.style.setProperty("--lw", "268px");
  };
}
function setLeft(on) {
  LS.set("left", on);
  $("#chatgrid").classList.toggle("noleft", !on);
  if (on) sideGrip();
  else $("#chatgrid").style.removeProperty("--lw");
  $("#tleft").hidden = on;
}
// ---------------- learning status, timers, local storage
function logoGlow(on) {
  $$(".logo,#gearbtn").forEach((l) => {
    l.classList.remove("glow-on", "glow-off");
    void l.offsetWidth;
    l.classList.add(on ? "glow-on" : "glow-off");
    setTimeout(() => l.classList.remove("glow-on", "glow-off"), 1700);
  });
}
function ago(ts) {
  if (!ts) return "";
  const m = Math.round((Date.now() - new Date(ts)) / 6e4);
  return m < 1
    ? tr("только что")
    : m < 60
      ? m + " " + tr("мин назад")
      : m < 1440
        ? Math.round(m / 60) + " " + tr("ч назад")
        : Math.round(m / 1440) + " " + tr("дн назад");
}
function inMin(ts) {
  if (!ts) return "";
  const m = Math.round((new Date(ts) - Date.now()) / 6e4);
  return m <= 0 ? "сейчас" : "через " + m + " мин";
}
let STATUS = {},
  STIMER = null;
async function refreshStatus() {
  try {
    const [ms, ls, br] = await Promise.all([
      api("/api/memory/status"),
      api("/api/learn/status"),
      api("/api/learn/brain"),
    ]);
    STATUS = { ms, ls, br, lon: STATUS.lon, wait: STATUS.wait };
    const s = ls.settings,
      st = s.demo
        ? ["info", "демо"]
        : s.paused
          ? ["pause", "на паузе"]
          : !ms.chat_learning && !ms.background.length
            ? ["info", "выключено"]
            : br.level === "bad"
              ? ["bad", "не работает"]
              : br.ok
                ? ["", ""]
                : ["info", "только явное"];
    if (ls.memory_on !== undefined) {
      MEM.on = ls.memory_on;
      document.body.classList.toggle("mem-off", !MEM.on);
    }
    const lon = MEM.on && !s.demo && !s.paused && !(!ms.chat_learning && !ms.background.length) && br.level !== "bad";
    // memory off: the dot by the gear turns yellow — a plain chat, nothing is remembered
    STATUS.dot = !MEM.on ? "pause" : st[0] === "info" && lon ? "" : st[0];
    STATUS.label = tr(
      !MEM.on
        ? "Память выключена"
        : lon
          ? br.ok
            ? "Mnemai учится"
            : "Mnemai запоминает только сказанное прямо"
          : s.paused
            ? "Mnemai на паузе"
            : "Mnemai не учится",
    );
    STATUS.when = !MEM.on
      ? tr("обычный чат, ничего не запоминается")
      : st[1] && !lon
        ? tr(st[1])
        : ms.updated
          ? tr("память обновлена") + " " + ago(ms.updated)
          : "";
    if (STATUS.lon !== undefined && STATUS.lon !== lon) logoGlow(lon);
    STATUS.lon = lon;
    drawGear();
    statusLine();
    ACH.folder = ms.folder;
    ACH.safety = ms.safety || null;
    achRefresh();
    badge();
  } catch (e) {}
  clearTimeout(STIMER);
  STIMER = setTimeout(refreshStatus, 30000);
}
function timersHtml() {
  const { ms, ls } = STATUS;
  if (!ms) return "";
  return `<div class="timers"><span>Память</span><div>${esc(ms.folder)}</div><span>Обновлена</span><div>${ms.updated ? ms.updated.replace("T", " ").slice(0, 16) + " · " + ago(ms.updated) : "ещё нет"}</div>
   <span>В чате</span><div>${ms.chat_learning ? "учусь сразу, пока ты пишешь" : "не учусь"}</div>
   <span>Источники</span><div>${ms.background.length ? esc(ms.background.join(", ")) : "не подключены"}</div>
   ${ms.background.length ? `<span>Проверка</span><div>${ms.paused ? "на паузе" : `каждые ${ms.interval} мин${ms.next_check ? " · следующая " + inMin(ms.next_check) : ""}${ms.last_check ? " · прошлая " + ago(ms.last_check) : ""}`}</div>` : ""}</div>`;
}
const QUICK = [
  ["mixed", "Учится сама", "Уверенное записывает сама, спорное и личное спрашивает"],
  ["approve", "Всё спрашивает", "Ничего не пишет без твоего «да»"],
  ["quiet", "Всё сама", "Записывает всё, ты только смотришь ленту"],
  ["observe", "Только смотрит", "Замечает и показывает, но ничего не пишет"],
  ["pause", "Пауза", "Не учится совсем, память при этом работает"],
];
function quickModes(anchor) {
  if ($(".qmodes")) {
    $(".qmodes").remove();
    return;
  }
  closeMenus();
  const p0 = $(".pop");
  if (p0) p0.remove();
  const { ls } = STATUS;
  if (!ls) return;
  const s = ls.settings;
  MENU_ANCHOR = anchor;
  const cur = s.paused ? "pause" : (Object.values(s.sources).find((x) => x.enabled) || {}).mode || "mixed";
  const m = document.createElement("div");
  m.className = "menu qmodes";
  m.innerHTML = `<div class="qh"><b>Как Mnemai учится</b>${hq("learn")}<button class="sw ${s.paused ? "" : "on"}" id="qlon" title="${tr(s.paused ? "Включить обучение" : "Поставить на паузу")}" style="margin-left:auto"></button></div>${QUICK.map(([k, t, d]) => `<button data-q="${k}" class="${k === cur ? "cur" : ""}"><span><b>${t}</b><small>${d}</small></span>${k === cur ? ic("check") : ""}</button>`).join("")}
    <hr><button data-q="feed">${ic("eye")}<span>Что поняла и почему</span></button><button data-q="tune">${ic("gear")}<span>Настроить</span></button>`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, Math.min(window.innerWidth - m.offsetWidth - 8, r.right - m.offsetWidth)) + "px";
  m.style.top = r.bottom + 8 + "px";
  $("#qlon", m).onclick = async (e) => {
    const b = e.currentTarget;
    b.classList.toggle("on");
    await post("/api/learn/settings", { paused: !b.classList.contains("on") });
    m.remove();
    await refreshStatus();
  };
  $$("[data-q]", m).forEach(
    (b) =>
      (b.onclick = async () => {
        const k = b.dataset.q;
        if (k === "feed") {
          m.remove();
          toggleDrawer(true);
          return;
        }
        if (k === "tune") {
          m.remove();
          learnPop(anchor);
          return;
        }
        if (k === "pause") {
          if (!s.paused) await post("/api/learn/settings", { paused: true });
        } else {
          if (s.paused) await post("/api/learn/settings", { paused: false });
          await post("/api/agent", { simple: { autonomy: k } });
        }
        m.remove();
        await refreshStatus();
      }),
  );
}
function learnPop(anchor) {
  closeMenus();
  if ($(".pop")) {
    $(".pop").remove();
    return;
  }
  const { ls, br } = STATUS;
  if (!ls) return;
  const s = ls.settings;
  MENU_ANCHOR = anchor;
  const seg = (key, choices, val) =>
    `<div class="seg" data-pseg="${key}">${Object.entries(choices)
      .map(([k, l]) => `<button data-v="${k}" class="${k === val ? "on" : ""}">${esc(l)}</button>`)
      .join("")}</div>`;
  const auto = (Object.values(s.sources).find((x) => x.enabled) || {}).mode || "mixed";
  const p = document.createElement("div");
  p.className = "pop";
  p.innerHTML = `<div class="row" style="margin:0;justify-content:space-between"><h4>Как Mnemai учится</h4><button class="sw ${s.paused ? "" : "on"}" id="pp" title="Учиться"></button></div>
   <div class="hint">${s.paused ? "Обучение на паузе" : "Учусь, пока ты пишешь, и проверяю подключённые источники"}</div>
   <div class="lab">Чем понимает речь</div>${seg("brain", BRAINS, s.brain.kind)}${br.level !== "ok" ? `<div class="hint" style="margin-top:6px;color:${br.level === "bad" ? "var(--bad)" : "var(--ink3)"}">${esc(br.message)}</div>` : ""}
   <div class="lab">Насколько сама учится</div>${seg("autonomy", { observe: "смотрит", approve: "спрашивает", mixed: "уверенное сама", quiet: "всё сама" }, auto)}
   ${timersHtml()}
   <div class="row" style="margin-top:12px"><button class="btn l sm" id="pall">Источники и все настройки обучения</button><button class="btn g sm" id="pfeed">Что поняла и почему</button></div>`;
  document.body.appendChild(p);
  const r = anchor.getBoundingClientRect();
  p.style.left = Math.max(8, r.right - p.offsetWidth) + "px";
  p.style.top = r.bottom + 8 + "px";
  $("#pp", p).onclick = async () => {
    await post("/api/learn/settings", { paused: !s.paused });
    p.remove();
    await refreshStatus();
    toast(s.paused ? "Учусь дальше" : "Обучение на паузе");
  };
  $$("[data-pseg]", p).forEach((sg) =>
    $$("button", sg).forEach(
      (b) =>
        (b.onclick = async () => {
          const k = sg.dataset.pseg,
            v = b.dataset.v;
          if (k === "brain") await post("/api/learn/settings", { brain: { kind: v } });
          else await post("/api/agent", { simple: { autonomy: v } });
          p.remove();
          await refreshStatus();
          learnPop(anchor);
        }),
    ),
  );
  $("#pall", p).onclick = () => {
    p.remove();
    location.hash = "settings";
  };
  $("#pfeed", p).onclick = () => {
    p.remove();
    toggleDrawer(true);
  };
}
function toggleDrawer(force) {
  const d = $("#panel");
  if (!d) return;
  const open = force !== undefined ? force : d.hidden;
  d.hidden = !open;
  document.body.classList.toggle("drawer-open", open);
  if (open) buildPanel();
  else {
    clearInterval(CHAT.feedTimer);
    CHAT.feedTimer = null;
  }
}
document.addEventListener("mousedown", (e) => {
  const d = $("#panel");
  if (!d || d.hidden || e.target.closest("#panel,#gearbtn,.menu,.pop,.modal,.hqpop,#toast")) return;
  toggleDrawer(false);
});
// Escape closes overlays; with no overlay open it stops the answer, like the white stop button.
document.addEventListener(
  "keydown",
  (e) => {
    if (e.key !== "Escape" || !CHAT.polling) return;
    const vis = (x) =>
      x.isConnected && getComputedStyle(x).display !== "none" && getComputedStyle(x).visibility !== "hidden";
    const overlay = $$(".modal, .menu, .mmenu, .hqpop, .pop").some(vis);
    if (overlay) return; // let the overlay's own Escape handler close it
    e.preventDefault();
    e.stopImmediatePropagation();
    if (CHAT.cons && !$("#inp").value.trim()) consAct("pause");
    else if (CHAT.cons) sendMsg();
    else post("/api/chat/stop", { chat: CHAT.id }).then(() => $("#inp").focus());
  },
  true,
);
window.addEventListener(
  "keydown",
  (e) => {
    if (e.key !== "Escape" || e.defaultPrevented) return;
    const vis = (x) =>
      x.isConnected && getComputedStyle(x).display !== "none" && getComputedStyle(x).visibility !== "hidden";
    const top = $$(".modal, .menu, .mmenu, .hqpop, .pop").filter(vis).pop();
    if (!top) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    const x = top.querySelector("[data-x], .lmx, .mx, [data-close], [data-skip], .ctx, #bk");
    if (x && top.classList.contains("modal")) return x.click();
    if (top.classList.contains("modal")) {
      top.dispatchEvent(new MouseEvent("click", { bubbles: true })); // like a click beside the card
      if (top.isConnected) top.remove();
      return;
    }
    top.remove();
  },
  true,
);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $("#lmx")) {
    $("#lmx").click();
    return;
  }
  if (e.key === "Escape") {
    const d = $("#panel");
    if (d && !d.hidden) toggleDrawer(false);
    const p = $(".pop");
    if (p) p.remove();
  }
});
function dayGroup(ts) {
  if (!ts) return "Раньше";
  const d = new Date(ts),
    n = new Date();
  const days = Math.floor((new Date(n.toDateString()) - new Date(d.toDateString())) / 864e5);
  return days <= 0 ? "Сегодня" : days === 1 ? "Вчера" : days < 7 ? "На этой неделе" : "Раньше";
}
// what an answer cost, as the provider counted it: input, read from its cache, the answer itself
function tokSpent(t) {
  const names = { in: "вход", input: "вход", cache: "из кеша", out: "ответ", output: "ответ" };
  const total = Object.values(t).reduce((a, b) => a + (+b || 0), 0);
  if (!total) return "";
  const parts = Object.entries(t)
    .filter(([, v]) => +v)
    .map(([k, v]) => `${tr(names[k] || k)}: ${(+v).toLocaleString(locale())}`)
    .join(" · ");
  return `<span class="saved spent" title="${esc(parts)}">${ic("coin")}${tr("потрачено")} ${fmtTok(total, true)}</span>`;
}
function fmtTok(n, bare) {
  if (!n) return tr("токенов нет");
  const word = bare ? "" : " " + tr("токенов");
  if (n < 1000) return n + word;
  const k = (n / 1000).toLocaleString(locale(), { maximumFractionDigits: n < 10000 ? 1 : 0 });
  return (I18N.lang === "ru" ? k + " тыс." : k + tr("тыс.")) + word;
}
function locale() {
  return I18N.lang === "ru" ? "ru-RU" : I18N.lang;
}
// the line of an action: its words in the owner's language, the path exactly as it is on disk
function actText(m) {
  return esc(tr(m.text || ""));
}
function actTip(m) {
  const rows = [];
  if (m.command) rows.push([tr("Команда"), `<code>${esc(m.command)}</code>`]);
  if (m.detail && m.detail !== m.text) rows.push([tr("Что сделала"), esc(m.detail)]);
  if (m.path) rows.push([tr("Папка"), esc(m.path)]);
  if (!rows.length) return "";
  return `<div class="acttip" role="tooltip"><table>${rows
    .map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`)
    .join("")}</table></div>`;
}
function fmtDate(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return (
    d.toLocaleDateString(locale(), { day: "numeric", month: "short" }).replace(".", "") +
    ", " +
    d.toTimeString().slice(0, 5)
  );
}
function family(model) {
  const pid = String(model || "").split(":")[0];
  return (
    {
      consortium: "Консорциум",
      local: "Локальная",
      claude_code: "Claude",
      anthropic: "Claude",
      openai: "ChatGPT",
      gemini: "Gemini",
      openrouter: "OpenRouter",
      deepseek: "DeepSeek",
      yandex: "YandexGPT",
      ollama: "Ollama",
      strata: "Strata",
    }[pid] || ""
  );
}
function aiMenu(anchor, fams, fam) {
  if ($(".aimenu")) {
    $(".aimenu").remove();
    return;
  }
  closeMenus();
  MENU_ANCHOR = anchor;
  const m = document.createElement("div");
  m.className = "mmenu menu aimenu";
  m.innerHTML =
    `<div class="gh">ИИ</div>` +
    ["", ...fams]
      .map(
        (f) =>
          `<button data-fam="${esc(f)}" class="${f === fam ? "cur" : ""}"><i class="rd"></i>${esc(f || "Все")}</button>`,
      )
      .join("") +
    (fams.length ? "" : '<div class="hint" style="padding:6px 10px">Разговоров пока нет</div>') +
    `<hr><button data-byday class="${LS.get("byday", false) ? "cur" : ""}"><i class="ck"></i>${tr("Группировать по дням")}</button>`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.width = "200px";
  m.style.left = Math.max(8, r.right - 200) + "px";
  m.style.top = r.bottom + 6 + "px";
  $$("[data-fam]", m).forEach(
    (b) =>
      (b.onclick = () => {
        m.remove();
        LS.set("fam", b.dataset.fam);
        drawList(($("#csearch") || {}).value || "");
      }),
  );
  $("[data-byday]", m).onclick = () => {
    m.remove();
    LS.set("byday", !LS.get("byday", false));
    drawList(($("#csearch") || {}).value || "");
  };
}
async function drawList(q) {
  const sort = LS.get("sort", "date");
  $$("#sortbar [data-sort]").forEach((b) => {
    b.classList.toggle("on", b.dataset.sort === sort);
    b.onclick = () => {
      LS.set("sort", b.dataset.sort);
      drawList(($("#csearch") || {}).value || "");
    };
  });
  const cl = await api("/api/chats?q=" + encodeURIComponent(q || "") + "&sort=" + sort);
  const box = $("#clist");
  if (!box) return;
  let last = "",
    html = "";
  const fams = [...new Set(cl.chats.map((c) => family(c.model)).filter(Boolean))];
  let fam = LS.get("fam", "");
  if (fam && !fams.includes(fam)) fam = "";
  const ab = $("#aibtn");
  if (ab) {
    ab.classList.toggle("on", !!fam);
    $("#ailbl").textContent = fam ? "ИИ: " + fam : "ИИ";
    ab.onclick = (e) => aiMenu(e.currentTarget, fams, fam);
  }
  const byday = LS.get("byday", false);
  const item = (c) =>
    `<div class="citem ${c.id === CHAT.id ? "on" : ""}" data-c="${c.id}"><div class="t"><div class="tr">${c.pinned ? ic("pin", "s") : ""}${c.private ? ic("eyeoff", "s") : ""}<b>${esc(c.title || "Без названия")}</b></div><span class="meta3">${family(c.model) ? `<span class="ctag2">${esc(family(c.model))}</span>` : ""}<span>${esc(fmtDate(c.updated))}</span>${c.tokens ? `<span class="tk" title="${esc(tr("потрачено") + " " + fmtTok(c.tokens) + (c.saved ? " · " + tr("сэкономлено") + " ≈ " + fmtTok(c.saved) : ""))}">${esc(fmtTok(c.tokens, true))}${c.saved >= 100 ? `<em class="tksv">−${esc(fmtTok(c.saved, true))}</em>` : ""}</span>` : ""}</span>${c.hit ? `<span class="hit">${esc(c.hit)}</span>` : ""}</div><div class="acts2"><button data-rn="${c.id}" title="Переименовать">${ic("edit")}</button><button class="more2" data-menu data-cm="${c.id}" title="Действия">${ic("dots")}</button></div></div>`;
  const chats = cl.chats.filter((c) => !fam || family(c.model) === fam);
  if (sort === "date" && !byday && !q) {
    // sessions: the conversations started after one «Новая сессия» press, joined by a line on the left
    const cur = (cl.session || {}).id || "",
      fold = LS.get("sfold", []),
      groups = new Map();
    chats.filter((c) => c.pinned).forEach((c) => (html += item(c)));
    if (cur && chats.length && !chats.some((c) => !c.pinned && c.session === cur)) groups.set(cur, []);
    chats
      .filter((c) => !c.pinned)
      .forEach((c) => {
        const k = c.session || "old";
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(c);
      });
    if (groups.has("old")) {
      const o = groups.get("old");
      groups.delete("old");
      groups.set("old", o);
    }
    if (cur && groups.has(cur)) {
      // the current session always on top: an old one goes down even when one of its conversations was just continued
      const c = groups.get(cur);
      groups.delete(cur);
      const rest = [...groups];
      groups.clear();
      groups.set(cur, c);
      rest.forEach(([k, v]) => groups.set(k, v));
    }
    // a session just started has no conversations yet: no empty line for it — the newest group stays «Текущая
    // сессия» until the first conversation of the new one; older sessions are named by their day
    let top = true;
    for (const [k, cs] of groups) {
      // conversations started before sessions existed form one more session, the last one
      if (!cs.length) continue;
      const now = k === cur || top,
        day = String(fmtDate(cs[0].updated) || "").split(",")[0],
        name = (cl.session_names || {})[k] || (now ? tr("Текущая сессия") : tr("Сессия") + (day ? " · " + day : ""));
      top = false;
      html += `<div class="csess ${now ? "cur" : ""} ${fold.includes(k) ? "fold" : ""}" data-s="${esc(k)}"><div class="cshrow"><button class="csh" title="${tr("Свернуть или развернуть")}"><b data-noi18n>${esc(name)}</b><em>${cs.length}</em>${ic("chev")}</button><button class="cshm kebab" data-sm="${esc(k)}" title="${tr("Ещё")}">${ic("dots")}</button></div><div class="csl">${cs.map(item).join("")}</div></div>`;
    }
  } else
    chats.forEach((c) => {
      if (byday) {
        const g = c.pinned ? "Закреплённые" : sort === "tokens" ? "Больше всего токенов" : dayGroup(c.updated);
        if (g !== last) {
          html += `<div class="cgroup">${g}</div>`;
          last = g;
        }
      }
      html += item(c);
    });
  box.innerHTML =
    html || `<div class="hint" style="padding:10px">${q ? "Ничего не нашла" : "Разговоров пока нет"}</div>`;
  $$("[data-sm]", box).forEach(
    (b) =>
      (b.onclick = (e) => {
        e.stopPropagation();
        const k = b.dataset.sm,
          n = cl.chats.filter((c) => (c.session || "old") === k && !c.pinned).length,
          named = (cl.session_names || {})[k] || "";
        menu(b, [
          {
            label: tr("Переименовать"),
            icon: "edit",
            run: async () => {
              const name = await askText("Как назвать сессию?", named);
              if (name === null) return;
              await post("/api/session/rename", { id: k, name }).catch((err) => toast(err.message));
              drawList("");
            },
          },
          {
            label: tr("Удалить"),
            icon: "trash",
            danger: true,
            run: async () => {
              if (!n) return toast(tr("В этой сессии нет разговоров"));
              if (
                !(await ask(
                  "Удалить сессию?",
                  tr("Разговоров в ней") +
                    ": " +
                    n +
                    ". " +
                    tr("Закреплённые останутся. Выученное из разговоров останется в памяти."),
                ))
              )
                return;
              await post("/api/session/delete", { id: k }).catch((err) => toast(err.message));
              if (cl.chats.some((c) => c.id === CHAT.id && (c.session || "old") === k && !c.pinned)) go("chat");
              else drawList("");
            },
          },
        ]);
      }),
  );
  $$(".csh", box).forEach(
    (b) =>
      (b.onclick = () => {
        const g = b.closest(".csess"),
          k = g.dataset.s,
          f = LS.get("sfold", []).filter((x) => x !== k);
        if (!g.classList.toggle("fold")) LS.set("sfold", f);
        else LS.set("sfold", [...f, k].slice(-50));
      }),
  );
  $$(".citem", box).forEach(
    (a) =>
      (a.onclick = (e) => {
        if (e.target.closest(".acts2")) return;
        viewChat(a.dataset.c);
      }),
  );
  $$("[data-rn]", box).forEach(
    (b) =>
      (b.onclick = async (e) => {
        e.stopPropagation();
        if (b.dataset.rn === CHAT.id) return renameInline();
        const it = b.closest(".citem"),
          cur = $(".t b", it).textContent;
        const t = await askText("Как назвать разговор?", cur);
        if (t && t.trim()) {
          await post("/api/chat/update", { id: b.dataset.rn, title: t.trim() });
          drawList(($("#csearch") || {}).value || "");
        }
      }),
  );
  $$("[data-cm]", box).forEach(
    (b) =>
      (b.onclick = (e) => {
        e.stopPropagation();
        chatMenu(b, b.dataset.cm);
      }),
  );
}
async function chatMenu(anchor, cid) {
  if (!cid) return;
  const c = await api("/api/chat?id=" + cid);
  const rel = () => drawList(($("#csearch") || {}).value || "");
  menu(anchor, [
    {
      label: "Переименовать",
      icon: "edit",
      run: async () => {
        if (cid === CHAT.id) return renameInline();
        const t = await askText("Как назвать разговор?", c.title);
        if (t) {
          await post("/api/chat/update", { id: cid, title: t });
          rel();
        }
      },
    },
    {
      label: c.pinned ? "Открепить" : "Закрепить",
      icon: "pin",
      run: async () => {
        await post("/api/chat/update", { id: cid, pinned: !c.pinned });
        rel();
      },
    },
    {
      label: "Не учиться на этом разговоре",
      icon: "eyeoff",
      check: !!c.private,
      run: async () => {
        await post("/api/chat/update", { id: cid, private: !c.private });
        if (cid === CHAT.id && CHAT.chat) {
          CHAT.chat.private = !c.private;
          drawPrivate();
        }
        rel();
        toast(!c.private ? "На этом разговоре не учусь" : "Снова учусь на этом разговоре");
      },
    },
    {
      label: "Скачать как текст",
      icon: "down",
      run: async () => {
        const d = await api("/api/chat/export?id=" + cid);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([d.markdown], { type: "text/markdown" }));
        a.download = (c.title || "разговор").slice(0, 60) + ".md";
        a.click();
      },
    },
    "-",
    {
      label: "Удалить разговор",
      icon: "trash",
      danger: true,
      run: async () => {
        if (
          !(await ask(
            "Удалить разговор?",
            (c.title ? "«" + c.title + "». " : "") + tr("Выученное из него останется в памяти."),
          ))
        )
          return;
        await post("/api/chat/delete", { id: cid });
        toast("Удалила");
        if (cid === CHAT.id) viewChat();
        else rel();
      },
    },
  ]);
}
function renameInline() {
  const t = $("#ctitle");
  if (!t || t.isContentEditable) return;
  const fresh = !CHAT.id || !CHAT.chat; // a new chat: the name waits for the first message
  const was = fresh ? CHAT.pendingTitle || "" : CHAT.chat.title;
  t.contentEditable = "true";
  t.focus();
  document.getSelection().selectAllChildren(t);
  const done = async (save) => {
    t.contentEditable = "false";
    t.onblur = t.onkeydown = null;
    const v = t.textContent.trim();
    if (fresh) {
      CHAT.pendingTitle = save && v && v !== tr("Новый разговор") ? v : was;
      t.textContent = CHAT.pendingTitle || tr("Новый разговор");
      if (save && CHAT.pendingTitle) toast(tr("Название сохранится с первым сообщением"));
      return;
    }
    if (save && v && v !== was) {
      try {
        await post("/api/chat/update", { id: CHAT.id, title: v });
        CHAT.chat.title = v;
        drawList(($("#csearch") || {}).value || "");
      } catch (e) {
        toast(e.message);
        t.textContent = was;
      }
    } else t.textContent = was;
  };
  t.onkeydown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      done(true);
    }
    if (e.key === "Escape") done(false);
  };
  t.onblur = () => done(true);
}
function isPrivate() {
  return CHAT.chat ? !!CHAT.chat.private : CHAT.newPrivate;
}
function drawPrivate() {
  setTimeout(statusLine, 0);
  drawState();
  drawChips();
  drawGear();
}
function drawState() {
  const box = $("#cstate");
  if (!box) return;
  const items = [];
  // "без обучения" and "консорциум" are buttons of their own now; the dot on "+" means a setting inside it is off
  box.innerHTML = items.join("");
  const d = $("#plusb .pdot");
  if (d) d.hidden = LS.get("terms", true);
  $$("[data-st]", box).forEach((b) => (b.onclick = () => (b.dataset.st === "priv" ? togglePrivate() : consortModal())));
}
function drawChips() {
  const p = $("#privchip"),
    c = $("#conschip");
  if (p) {
    p.classList.toggle("on", MEM.on && isPrivate());
    p.classList.toggle("dis", !MEM.on);
    p.title = MEM.on ? tr("Этот разговор не учит память") : tr("Память выключена — разговоры и так ничего не учат");
  }
  if (c) {
    c.classList.toggle("on", !!CHAT.cons);
    $("span:not(.hq)", c).textContent = tr("Консорциум"); // who is in it shows at the top, above the conversation
  }
}
function plusMenu(anchor) {
  if ($(".pmenu")) {
    $(".pmenu").remove();
    return;
  }
  closeMenus();
  MENU_ANCHOR = anchor;
  const m = document.createElement("div");
  m.className = "pmenu menu";
  const terms = LS.get("terms", true),
    tour = LS.get("tour", true),
    priv = isPrivate();
  m.innerHTML = `<button data-p="terms" class="${terms ? "on" : ""}">${ic("hint")}<span>Подсказки к терминам</span>${hq("hints")}<i class="sw2"></i></button>
    <div class="sep"></div><div class="mhead">${tr("Попробовать")}</div>
    <button data-p="roast">${ic("fire")}<span>${tr("Прожарка")}<small>${tr("несколько ИИ жёстко и по делу разбирают идею, резюме или текст")}</small></span></button>
    <button data-p="compare">${ic("eye")}<span>${tr("С памятью и без")}<small>${tr("один вопрос — два ответа рядом")}</small></span></button>
    <button data-p="quiz">${ic("check")}<span>${tr("Насколько Mnemai тебя знает")}<small>${tr("квиз по твоей памяти")}</small></span></button>
    <button data-p="interview">${ic("user")}<span>${tr("Знакомство")}<small>${tr("пара минут вопросов — и память не пустая")}</small></span></button>
`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, r.left) + "px";
  m.style.top = r.top - m.offsetHeight - 8 + "px";
  $$("[data-p]", m).forEach(
    (b) =>
      (b.onclick = async () => {
        const k = b.dataset.p;
        if (k === "terms") {
          const on = !LS.get("terms", true);
          LS.set("terms", on);
          document.body.classList.toggle("noterms", !on);
          b.classList.toggle("on", on);
          drawState();
          applyComposer();
          return;
        }
        if (k === "tour") {
          const on = !LS.get("tour", true);
          LS.set("tour", on);
          b.classList.toggle("on", on);
          if (!CHAT.id && $(".startline")) renderEmpty();
          return;
        }
        if (k === "priv") {
          await togglePrivate();
          b.classList.toggle("on", isPrivate());
          return;
        }
        m.remove();
        if (k === "roast") return consortModal(false, "roast");
        if (k === "compare") return compareView();
        if (k === "quiz") return quizView();
        if (k === "interview") return interviewView();
        if (k === "cons") consortModal();
        if (k === "audio") $("#apick").click();
      }),
  );
}
function micMenu(anchor) {
  if (VOICE.on) {
    voiceStop();
    return;
  }
  if ($(".pmenu")) {
    $(".pmenu").remove();
    return;
  }
  closeMenus();
  MENU_ANCHOR = anchor;
  const m = document.createElement("div");
  m.className = "pmenu menu";
  m.innerHTML = `<button data-v="cmd">${ic("mic")}<span>Сказать команду<small>распознаю на компьютере и отправлю</small></span></button>
    <button data-v="meet">${ic("users")}<span>Записать встречу<small>расшифровка и итоги</small></span>${hq("scribe")}</button>`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, Math.min(window.innerWidth - m.offsetWidth - 8, r.right - m.offsetWidth)) + "px";
  m.style.top = r.top - m.offsetHeight - 8 + "px";
  $$("[data-v]", m).forEach(
    (b) =>
      (b.onclick = () => {
        m.remove();
        b.dataset.v === "cmd" ? voiceStart() : scribeStart();
      }),
  );
}
let MIC_KEEP = false;
api("/api/agent")
  .then((a) => {
    MIC_KEEP = !!(a.profile || {}).scribe_keep_audio;
  })
  .catch(() => {});
const VOICE = { on: false, t: 0 };
async function voiceStart() {
  try {
    await post("/api/voice/start", {});
  } catch (e) {
    toast(e.message);
    return;
  }
  VOICE.on = true;
  VOICE.t = Date.now();
  $("#micb").classList.add("rec");
  const bar = $("#recbar");
  bar.innerHTML = `<div class="vbar"><i></i><b>Слушаю</b><span id="vtime">0:00</span><span class="sp"></span><button class="btn g sm" id="vcancel">Отмена</button><button class="btn sm" id="vdone">Готово</button></div>`;
  $("#vcancel").onclick = voiceCancel;
  $("#vdone").onclick = voiceStop;
  clearInterval(VOICE.timer);
  VOICE.timer = setInterval(() => {
    const s = Math.round((Date.now() - VOICE.t) / 1000);
    const el = $("#vtime");
    if (el) el.textContent = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
    if (s >= 120) voiceStop();
  }, 500);
}
async function voiceCancel() {
  clearInterval(VOICE.timer);
  VOICE.on = false;
  $("#micb") && $("#micb").classList.remove("rec");
  $("#recbar").innerHTML = "";
  await post("/api/voice/cancel", {}).catch(() => {});
}
async function voiceStop() {
  if (!VOICE.on) return;
  clearInterval(VOICE.timer);
  VOICE.on = false;
  $("#micb") && $("#micb").classList.remove("rec");
  $("#recbar").innerHTML = `<div class="vbar"><span class="phase"><i></i>распознаю на компьютере</span></div>`;
  try {
    const r = await post("/api/voice/stop", { lang: LS.get("lang", "") || "" });
    $("#recbar").innerHTML = "";
    if (!r.text) {
      toast("Не расслышала — попробуй ещё раз");
      return;
    }
    $("#inp").value = r.text;
    sendMsg();
  } catch (e) {
    $("#recbar").innerHTML = "";
    toast(e.message);
  }
}
async function togglePrivate() {
  if (CHAT.chat && CHAT.id) {
    CHAT.chat.private = !CHAT.chat.private;
    await post("/api/chat/update", { id: CHAT.id, private: CHAT.chat.private });
    drawList(($("#csearch") || {}).value || "");
  } else CHAT.newPrivate = !CHAT.newPrivate;
  drawPrivate();
  (() => 0)(isPrivate() ? "На этом разговоре не учусь" : "Учусь на этом разговоре");
}
async function renderEmpty() {
  $("#ctitle").textContent = tr("Новый разговор");
  let ls = {},
    ms = {};
  try {
    [ls, ms] = await Promise.all([api("/api/learn/status"), api("/api/memory/status")]);
  } catch (e) {}
  const src = (ls.settings || {}).sources || {},
    cc = src.claude_code && src.claude_code.enabled,
    gpt = src.chatgpt_export && src.chatgpt_export.enabled;
  const lbl = modelLabel(CHAT.model),
    isLocal = String(CHAT.model).startsWith("local:");

  const TOUR = tourSteps();
  const firstTime = LS.get("tour", true) && !LS.get("tour_seen", false);
  if (firstTime) LS.set("tour_seen", true);
  const tour = firstTime
    ? `<div class="tour"><div class="tc"><h3>Как устроена Mnemai</h3><div class="sub">6 шагов, минута чтения</div>${TOUR.map(([b, t, a, l], i) => `<div class="st"><span class="n">${i + 1}</span><div><b>${esc(b)}</b><p>${esc(t)}</p></div><button data-tour="${a}">${esc(l)}</button></div>`).join("")}<div class="foot"><a href="#" id="tourx">${tr("Больше не показывать")}</a> · ${tr("вернуть — в шестерёнке справа вверху")}</div></div></div>`
    : "";
  if (CHAT.cons) {
    $("#msgs").innerHTML =
      `<div class="conline seats pre">${CHAT.cons.members.map((r, i) => `<div class="seat" style="--sc:${spkColor(r)};--i:${i}"><span class="sav">${esc(spkGlyph(r, consName(r)))}</span><b data-noi18n>${esc(consName(r))}</b><small>${i === 0 ? tr("начнёт") : i + 1 + "-й"}</small></div>`).join("")}</div><div class="startline">Задай вопрос — ${CHAT.cons.members.length} ИИ ответят по очереди и обсудят друг с другом${CHAT.cons.rounds > 1 ? ", кругов: " + CHAT.cons.rounds : ""}. Вмешаться можно в любой момент.</div>`;
    return;
  }
  $("#msgs").innerHTML =
    `<div class="emptyw">${tour}<div class="esp"></div><div class="ebot"><div class="startline">${tr("Начни диалог")}</div>${CHAT.model ? `<div class="opener"><button class="btn l" id="opener">${ic("chat")}${tr("Пусть Mnemai начнёт сама")}</button></div>` : ""}</div></div>`;
  statusLine();
  const TA = {
    memory: () => go("memory"),
    folder: () => post("/api/memory/open", {}).catch((e) => toast(e.message)),
    feed: () => toggleDrawer(),
    model: () => modelMenu($("#model")),
    file: () => $("#fpick").click(),
    settings: () => go("settings"),
    memon: () => memSet(true).then(() => renderEmpty()),
  };
  $$("[data-tour]").forEach(
    (b) =>
      (b.onclick = (e) => {
        e.stopPropagation();
        TA[b.dataset.tour]();
      }),
  );
  if ($("#opener")) $("#opener").onclick = () => startByMnema();
  if ($("#tourx"))
    $("#tourx").onclick = (e) => {
      e.preventDefault();
      setTour(false);
    };
}

// ---------------- meeting scribe
let SCRIBE_T = null;
async function scribeStart() {
  try {
    const st = await api("/api/scribe/status");
    if (!st.available) {
      toast("Распознавание речи не установлено");
      return;
    }
    if (st.status === "recording") {
      return scribeStop();
    }
    meetModal();
  } catch (e) {
    toast(e.message);
  }
}
async function scribeStop() {
  try {
    await post("/api/scribe/stop", {});
    scribeWatch();
  } catch (e) {
    toast(e.message);
  }
}
async function scribeImport(f) {
  try {
    const st = await api("/api/scribe/status");
    if (!st.available) {
      toast("Распознавание речи не установлено");
      return;
    }
    meetModal(f);
  } catch (e) {
    toast(e.message);
  }
}
async function scribeWatch() {
  clearTimeout(SCRIBE_T);
  const bar = $("#recbar");
  if (!bar) return;
  let st;
  try {
    st = await api("/api/scribe/status");
  } catch (e) {
    return;
  }
  const mb = $("#micb");
  if (mb) {
    mb.classList.toggle("on", st.status === "recording");
    mb.title = st.status === "recording" ? "Остановить запись" : "Записать встречу — распознаю на этом компьютере";
  }
  if (st.status === "recording") {
    const e = st.elapsed || 0;
    bar.innerHTML = `<div class="recbar"><span class="rd"></span><b>${String(Math.floor(e / 60)).padStart(2, "0")}:${String(e % 60).padStart(2, "0")}</b><span>Идёт запись · микрофон и звук компьютера</span><div class="sp"></div><button class="btn sm" id="recstop">Остановить и расшифровать</button></div>`;
    $("#recstop").onclick = scribeStop;
    SCRIBE_T = setTimeout(scribeWatch, 1000);
    return;
  }
  if (st.status === "ask") {
    if (!$("#scrask", bar))
      bar.innerHTML = `<div class="recbar ask" id="scrask"><span>${esc(st.question || "")}</span><div class="sp"></div><label class="hint" style="display:flex;gap:5px;align-items:center;white-space:nowrap"><input type="checkbox" id="scrrem">${tr("запомнить")}</label><button class="btn sm" data-sa="cloud">${tr("В облако")}</button><button class="btn g sm" data-sa="local">${tr("На компьютере")}</button></div>`;
    $$("[data-sa]", bar).forEach(
      (b) =>
        (b.onclick = async () => {
          await post("/api/scribe/answer", { choice: b.dataset.sa, remember: $("#scrrem").checked });
          scribeWatch();
        }),
    );
    SCRIBE_T = setTimeout(scribeWatch, 1500);
    return;
  }
  if (st.status === "transcribing") {
    const p = Math.round((st.progress || 0) * 100);
    bar.innerHTML = `<div class="recbar"><span>${esc(st.phase || "Расшифровываю")} · «${esc(st.name || "")}»${st.notice ? `<small class="scrnote">${esc(st.notice)}</small>` : ""}</span><div class="bar"><i style="width:${p}%"></i></div><b>${p}%</b></div>`;
    SCRIBE_T = setTimeout(scribeWatch, 1000);
    return;
  }
  if (st.status === "done" && st.chat) {
    bar.innerHTML = "";
    await post("/api/scribe/reset", {});
    toast("Расшифровка готова — файл в папке «80 Meetings»");
    viewChat(st.chat);
    return;
  }
  if (st.status === "error") {
    bar.innerHTML = `<div class="recbar"><span style="color:var(--bad)">Не вышло: ${esc(st.error || "")}</span><div class="sp"></div><button class="btn g sm" id="recok">Понятно</button></div>`;
    $("#recok").onclick = async () => {
      await post("/api/scribe/reset", {});
      bar.innerHTML = "";
    };
    return;
  }
  bar.innerHTML = "";
}

const AUDIO = /\.(mp3|wav|m4a|ogg|oga|opus|amr|flac|aac|wma|webm|mp4|m4v|mkv|mov|avi|3gp)$/i;
async function addFiles(list) {
  for (const f of list) {
    if (AUDIO.test(f.name)) {
      scribeImport(f);
      continue;
    }
    if (f.size > 25 * 1024 * 1024) {
      toast(f.name + ": больше 25 МБ");
      continue;
    }
    const data = await new Promise((r) => {
      const fr = new FileReader();
      fr.onload = () => r(fr.result);
      fr.readAsDataURL(f);
    });
    (CHAT.files = CHAT.files || []).push({ name: f.name, data, size: f.size });
  }
  drawFiles();
  $("#inp").focus();
}
function drawFiles() {
  const b = $("#fbar");
  if (!b) return;
  b.hidden = !CHAT.files.length;
  b.innerHTML = CHAT.files
    .map((f, i) => `<span class="chipf">${ic("file")}${esc(f.name)}<b data-rm="${i}">×</b></span>`)
    .join("");
  $$("[data-rm]", b).forEach(
    (x) =>
      (x.onclick = () => {
        CHAT.files.splice(+x.dataset.rm, 1);
        drawFiles();
      }),
  );
}
// an action the model asks for: what exactly, with which file — «Да», «Нет», «Да для этого разговора»
function actionAsk(cid, p) {
  const old = $("#actask");
  if (!p) {
    if (old) old.remove();
    return;
  }
  if (old && old.dataset.id === p.id) return;
  if (old) old.remove();
  const live = $("#live");
  if (!live) return;
  live.insertAdjacentHTML(
    "afterend",
    `<div class="actask" id="actask" data-id="${esc(p.id)}"><div class="actaskh">${ic(p.write ? "edit" : "file")}<b>${tr("Mnemai хочет")}</b></div>
     <div class="actwhat" data-noi18n>${esc(p.what)}</div>
     <div class="row"><button class="btn sm" data-act="yes">${tr("Да")}</button><button class="btn g sm" data-act="always">${tr("Да для этого разговора")}</button><button class="btn g sm" data-act="no">${tr("Нет")}</button></div>
     <p class="hint">${tr("Программы не запускаются, в интернет ничего не уходит. Запись можно откатить в «Память» → «История».")}</p></div>`,
  );
  $$("#actask [data-act]").forEach(
    (b) =>
      (b.onclick = async () => {
        $$("#actask [data-act]").forEach((x) => (x.disabled = true));
        try {
          await post("/api/chat/action", { chat: cid, id: p.id, choice: b.dataset.act });
        } catch (e) {
          toast(e.message);
        }
        if ($("#actask")) $("#actask").remove();
      }),
  );
  scrollEnd();
}
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[data-reveal]");
  if (b) post("/api/files/reveal", { path: b.dataset.reveal }).catch((err) => toast(err.message));
  const o = e.target.closest && e.target.closest("[data-fopen]");
  if (o) post("/api/files/open", { path: o.dataset.fopen }).catch((err) => toast(err.message));
});
// a document path in an answer («PDF готов: C:\…\отчёт.pdf») gets an «Открыть» button next to it
const OPENABLE = /\.(pdf|docx?|xlsx?|pptx|csv|md|txt|png|jpe?g|odt|rtf)$/i;
const PATH_RE =
  /(?<![\w/"'=])(?:[A-Za-z]:\\|(?<![\w:/.])\/(?:Users|home|tmp|Volumes)\/)[^<>\n"|?*]*?\.(?:pdf|docx?|xlsx?|pptx|csv|md|txt|png|jpe?g|odt|rtf)(?![\w])/g;
function fileButtons(html) {
  return html
    .replace(PATH_RE, (p) => {
      const raw = p.replace(/&amp;/g, "&");
      return `${p}<button class="btn sm fopen" data-fopen="${esc(raw)}">${ic("file")}${tr("Открыть")}</button>`;
    })
    .replace(/(<button class="btn sm fopen"[^>]*>[\s\S]*?<\/button>)<\/code>/g, "</code>$1"); // after the code, not in it
}
// the quoted answer above a message: one line of plain text, no Markdown marks, no empty lines
function quoteLine(s) {
  return String(s || "")
    .replace(/\s*\n\s*/g, " ")
    .replace(/[*_#>`|]+/g, "")
    .replace(/:?-{3,}:?/g, "") // table rules
    .replace(/\s{2,}/g, " ")
    .trim();
}
function msgHtml(m, last, i, lastAi) {
  if (m.hidden) return "";
  if (m.kind === "action") {
    const showFolder = m.path && !m.failed && !["run_command", "open_app"].includes(m.tool);
    return `<div class="actline ${m.refused || m.failed ? "bad" : ""}">${ic(m.refused || m.failed ? "x" : "check")}<span class="actone"><span data-noi18n>${actText(m)}</span>${showFolder ? `<a class="actlink" data-reveal="${esc(m.path)}">${tr("папка")}</a>` : ""}</span>${actTip(m)}</div>`;
  }
  if (m.role === "user")
    return `<div class="msg user">${m.quote ? `<div class="uq">${ic("reply")}<span>${esc(quoteLine(m.quote))}</span></div>` : ""}${(m.files || []).length ? `<div class="fchips">${m.files.map((f) => `<span class="chipf" title="${f.kind === "text" ? "прочитан на этом компьютере" : ""}">${ic("file")}${esc(f.name)}${f.info && f.info.pages ? ` · ${f.info.pages} стр.` : f.info && f.info.sheets ? ` · листов ${f.info.sheets}` : f.info && f.info.slides ? ` · слайдов ${f.info.slides}` : ""}</span>`).join("")}</div>` : ""}<div class="b">${esc(m.text)}</div></div>`;
  const srcs = (m.sources || []).length
    ? `<div class="srcs">${m.sources.map((s, k) => `<a href="${esc(s.url)}" target="_blank" title="${esc(s.url)}"><b>${k + 1}</b><span>${esc(s.title || s.url)}</span></a>`).join("")}</div>`
    : "";
  const redc = m.redacted ? Object.values(m.redacted).reduce((a, b) => a + b, 0) : 0;
  const hidden = redc
    ? `<span class="saved" title="${esc(tr("Скрыто до отправки") + ": " + redLine(m.redacted))}">${ic("lock")}${tr("скрыто")}: ${redc}</span>`
    : "";
  const saved =
    (m.tokens ? tokSpent(m.tokens) : "") +
    (m.saved >= 100
      ? `<span class="saved sv" title="${esc(tr("Документы, память и страницы прочитаны на компьютере, модели ушли только нужные части"))}">${ic("down")}${tr("сэкономлено")} ≈ ${fmtTok(m.saved, true)}</span>`
      : "");
  const spk = m.speaker
    ? `<div class="spk"><i style="background:${spkColor(m.model)}"></i>${esc(m.speaker)}${m.summary ? `<em>${tr("итог")}</em>` : ""}${m.cut ? `<span>· ${tr("перебит")}</span>` : ""}</div>`
    : "";
  if (m.kind === "cons_start")
    return `<div class="cdiv">${ic("users")}<span>${tr("К разговору подключились")}: <b data-noi18n>${(m.members || []).map(consName).map(esc).join(", ")}</b> · ${tr("кругов")}: ${m.rounds || 2}</span></div>`;
  if (m.kind === "cons_end")
    return `<div class="cdiv">${ic("chat")}<span>${tr("Консорциум завершён, дальше отвечает")} <b data-noi18n>${esc(consName(m.model || ""))}</b></span></div>`;
  if (m.error && !m.text)
    return `<div class="msg ai"><div class="av"></div><div>${spk}<p class="err">${linkSettings(esc(m.error))}</p></div></div>`;
  if (m.kind === "self_ask") {
    const q = m.ask || {};
    const opts = q.options || [];
    return `<div class="msg ai"><div class="av"></div><div class="offer selfask" data-sa="${i}"><p>${ic("hint")}<span>${esc(tr(m.text))}</span></p>${
      q.done
        ? `<p class="done">${esc(tr(q.done))}</p>`
        : `${q.type === "goal" ? `<input class="inp" data-satext placeholder="${tr("Цель одной фразой")}">` : `<input class="inp" data-satext hidden placeholder="${tr("Что изменилось — одной фразой")}">`}
        <div class="row">${opts.map(([k, l], n) => `<button class="btn ${n ? "g " : ""}sm" data-saa="${k}">${tr(l)}</button>`).join("")}<button class="btn g sm" data-saa="skip">${tr("Не сейчас")}</button><button class="btn g sm sanever" data-saa="never">${tr("Не спрашивать так")}</button></div>`
    }</div></div>`;
  }
  if (m.kind === "prompt_offer") {
    const o = m.offer || {};
    return `<div class="msg ai"><div class="av"></div><div class="offer"><p>${o.similar ? `${tr("Похожая задача уже была:")} «<span data-noi18n>${esc(o.similar.length > 140 ? o.similar.slice(0, 140) + "…" : o.similar)}</span>». ` : tr("Похоже, эта задача будет повторяться.") + " "}${tr("Записать рецепт этой задачи? В следующий раз сделаю так же — без объяснений и уточнений.")}${hq("prompts")}</p>${
      o.choice
        ? `<p class="done">${o.choice === "write" ? "Записала рецепт «" + esc(o.name || "") + "». Он в настройках: «Как отвечает» → «Повторяющиеся задачи»." : o.choice === "never" ? "Хорошо, для таких больше не предлагаю." : "Делаю без рецепта."}</p>`
        : `<div class="row"><button class="btn sm" data-offer="write">Записать рецепт</button><button class="btn g sm" data-offer="skip">Просто сделать</button><button class="btn g sm" data-offer="never">Не предлагать для таких</button></div>`
    }</div></div>`;
  }
  const needWeb =
    m.needs_web && last
      ? `<div class="needweb">${ic("globe")}<div><b>${tr("Тут нужны свежие данные из интернета")}</b><span>${tr("Ответ — по тому, что ИИ знает сам. С поиском будет точнее.")}</span></div><button class="btn sm" data-webredo>${tr("Включить интернет и ответить заново")}</button></div>`
      : "";
  const cav = m.speaker
    ? `<div class="av cav" style="--sc:${spkColor(m.model)}">${esc(spkGlyph(m.model, m.speaker))}</div>`
    : '<div class="av"></div>';
  const sumh = m.summary
    ? `<div class="sumh">${ic("trophy")}<b>${tr("Итог обсуждения")}</b><span>${tr("в чём сошлись, в чём разошлись, что советуют")}</span></div>`
    : "";
  const asked =
    m.speaker &&
    last &&
    CHAT.cons &&
    ((CHAT.chat || {}).consortium || {}).state &&
    CHAT.chat.consortium.state.status === "waiting" &&
    /```ask/.test(m.text)
      ? `<div class="cwait">${ic("pause")}<span>${esc(m.speaker)} ${tr("спрашивает тебя — остальные ждут твоего ответа")}</span></div>`
      : "";
  return (
    asked +
    `<div class="msg ai ${m.summary ? "sum" : ""} ${m.speaker ? "cmsg" : ""}" style="${m.speaker ? "--sc:" + spkColor(m.model) : ""}" ${i !== undefined ? `data-i="${i}"` : ""}>${cav}<div>${sumh}${spk}<div class="md">${fileButtons(md(m.text, last))}</div>${m.error ? `<p class="err">${linkSettings(esc(m.error))}</p>` : ""}${needWeb}${m.prompt ? `<div class="byprompt">${ic("book")}по рецепту «${esc(m.prompt)}»</div>` : ""}${srcs}${i !== undefined ? `<div class="acts ${m.useful ? "keep" : ""}"><button data-copy="${i}">${ic("copy")}Копировать</button><button data-reply="${i}">${ic("reply")}Ответить</button>${!m.speaker && !m.summary && !(CHAT.chat && CHAT.chat.consortium) ? `<button data-debate="${i}">${ic("users")}Поспорить с разными ИИ</button>` : ""}${m.summary && m.text ? `<button data-share="${i}">${ic("right")}${tr("Поделиться")}</button>` : ""}${m.checked ? '<span class="meta" style="align-self:center;margin-left:6px">перепроверено перед отправкой</span>' : ""}${saved}${hidden}</div>` : ""}</div></div>`
  );
}
// ---------------- a question from the model as a card
function askAnswer(card, text) {
  if (!text || card.classList.contains("done")) return;
  card.classList.replace("live", "done");
  markAsk(card, text);
  const draft = $("#inp").value.trim();
  $("#inp").value = text;
  const p = sendMsg();
  if (draft && p && p.finally)
    p.finally(() => {
      if (!$("#inp").value.trim()) $("#inp").value = draft;
    });
}
function markAsk(card, text) {
  const hit = $$(".askopt", card).find((b) => b.dataset.ans === text);
  if (hit) hit.classList.add("chosen");
  $(".askdone span", card).textContent = hit ? tr("Выбрано") + ": " + text : tr("Ответ") + ": " + text;
  card.classList.add("answered");
}
// the conversation got expensive: one answer costs three times the first one in this conversation (the owner's decision, 21.10)
const tipCost = (m) => {
  const t = m.tokens || {};
  return (t.in || 0) + (t.out || 0) + (t.cache || 0);
};
function costTip(c) {
  const ms = ((c && c.messages) || []).filter((m) => m.kind !== "self_ask");
  if (!c || c.consortium || !ms.length || ms[ms.length - 1].role !== "assistant" || ms[ms.length - 1].speaker)
    return null;
  if (LS.get("costtip", true) === false || (LS.get("costtip_hide", []) || []).includes(c.id)) return null;
  const lastModel = (ms[ms.length - 1] || {}).model || "";
  if (/^(local|ollama):/.test(lastModel)) return null; // free on this computer: nothing gets expensive
  const ai = ms.filter((m) => m.role === "assistant" && !m.speaker && tipCost(m) > 0 && m.model === lastModel);
  if (ai.length < 2 || ai[ai.length - 1] !== ms[ms.length - 1]) return null;
  const first = tipCost(ai[0]),
    last = tipCost(ai[ai.length - 1]);
  return last >= first * 3 ? { first, last, x: last / first } : null;
}
function costTipHtml(c) {
  const t = costTip(c);
  if (!t) return "";
  const k = (t.x < 10 ? t.x.toFixed(1) : Math.round(t.x) + "").replace(".", ",");
  const w = Math.max(4, Math.round((100 * t.first) / t.last));
  const go = c.private ? tr("Начать новую сессию") : tr("Обновить память и начать новую сессию");
  return `<div class="ask live lask ctip" data-ctip>
    <div class="askh"><span class="aski">${ic("coin")}</span><span class="askl">${tr("Совет")}</span><button class="ctx" data-ct="hide" title="${tr("Скрыть в этом разговоре")}">${ic("x")}</button></div>
    <div class="askq">${tr("Разговор стал дорогим")}</div>
    <div class="ctbars"><div class="ctrow"><span>${tr("Первый ответ")}</span><i style="--w:${w}%"></i><b>${esc(fmtTok(t.first, true))}</b></div><div class="ctrow hot"><span>${tr("Последний")}</span><i style="--w:100%"></i><b>${esc(fmtTok(t.last, true))}</b></div></div>
    <div class="askw">${tr("Последний ответ обошёлся")} <b>${tr("в")} ${k} ${tr("раза дороже первого")}</b>: ${tr("каждый ответ заново перечитывает весь разговор.")} ${c.private ? tr("Новая сессия начнётся с чистого листа, память и правила останутся.") : tr("Mnemai сначала выучит этот разговор, потом начнёт новую сессию с чистого листа — память и правила останутся.")}</div>
    <div class="laskacts"><button class="btn sm" data-ct="go">${go}</button><button class="btn g sm" data-ct="off">${tr("Больше не показывать")}</button></div></div>`;
}
function bindCostTip() {
  const card = $("[data-ctip]");
  if (!card) return;
  const cid = CHAT.id;
  $$("[data-ct]", card).forEach(
    (b) =>
      (b.onclick = async () => {
        const a = b.dataset.ct;
        if (a === "hide" || a === "off") {
          if (a === "off") {
            LS.set("costtip", false);
            toast(tr("Совет выключен. Вернуть — в шестерёнке"));
          } else LS.set("costtip_hide", [...(LS.get("costtip_hide", []) || []).slice(-49), cid]);
          card.classList.add("gone");
          setTimeout(() => card.remove(), 220);
          return;
        }
        $$("[data-ct]", card).forEach((x) => (x.disabled = true));
        let r = {};
        if (!(CHAT.chat && CHAT.chat.private)) {
          $(".laskacts", card).innerHTML = `<span class="phase"><i></i>${tr("Учу этот разговор…")}</span>`;
          try {
            r = await post("/api/chat/learn_now", { id: cid });
          } catch (e) {
            r = { error: String(e.message || e) };
          }
        }
        await post("/api/session/new", {});
        CHAT.pendingCons = null;
        await viewChat();
        toast(
          r.error
            ? tr("Не получилось выучить разговор, новая сессия началась")
            : r.skipped === "off"
              ? tr("Обучение выключено — новая сессия началась без него")
              : r.written
                ? `${tr("Память обновлена")}: +${r.written}. ${tr("Новая сессия началась")}`
                : tr("Новая сессия началась, память уже знала всё из этого разговора"),
          4500,
        );
      }),
  );
}
function learnAskHtml(q) {
  if (!q) return "";
  const head = {
    conflict: tr("Это расходится с тем, что я помню"),
    personal: tr("Это личное — запомнить?"),
    confirm: tr("Запомнить это?"),
  }[q.kind];
  const acts =
    q.kind === "conflict"
      ? [
          ["keep", tr("Теперь так")],
          ["keep_old", tr("Было верно")],
          ["keep_both", tr("Верно и то, и то")],
        ]
      : [
          ["keep", tr("Запомнить")],
          ["keep_all", tr("Запомнить всё")],
          ["reject", tr("Не надо")],
        ];
  return `<div class="ask live lask" data-lask="${esc(q.item)}">
    <div class="askh"><span class="aski">${ic("mem")}</span><span class="askl">${tr("Уточню для памяти")}</span></div>
    <div class="askq">${esc(head)}</div>
    ${q.kind === "conflict" ? `<div class="askw">${tr("Было")}: ${esc(q.old)}</div>` : ""}
    <div class="lasktext">${esc(q.text)}</div>
    ${q.kind === "personal" ? `<div class="askw">${tr("Попадёт в скрытую часть: её видят только ИИ, которым ты разрешил")}</div>` : ""}
    <div class="laskacts">${acts.map(([a, l], k) => `<button class="btn ${k ? "g" : ""} sm" data-la="${a}">${l}</button>`).join("")}</div></div>`;
}
function learnAsksHtml(c) {
  const qs = c && c.learn_asks && c.learn_asks.length ? c.learn_asks : c && c.learn_ask ? [c.learn_ask] : [];
  return qs
    .slice(0, 3)
    .map((q) => learnAskHtml(q))
    .join("");
}
async function answerLearnAsk(card, action) {
  const body = { id: card.dataset.lask, action, chat: CHAT.id };
  if (action === "edit") {
    const t = await askText("Как правильно?", $(".lasktext", card).textContent);
    if (!t) return;
    body.text = t;
  }
  try {
    const r = await post("/api/learn/review", body);
    card.remove();
    if (action === "keep_all") {
      // «Запомнить всё» answers every question standing under this conversation: the rest of the queue goes too
      $$("[data-lask]").forEach((c) => c.remove());
      toast(`${tr("Запомнила")}: ${r.done || 1}`, 4500);
      return;
    }
    toast(
      {
        keep: tr("Запомнила"),
        edit: tr("Запомнила с поправкой"),
        keep_both: tr("Запомнила оба"),
        keep_old: tr("Оставила как было"),
        reject: tr("Не запоминаю"),
      }[action],
    );
  } catch (e) {
    toast(e.message);
  }
}
function bindAsk() {
  $$("[data-lask] [data-la]").forEach(
    (b) => (b.onclick = () => answerLearnAsk(b.closest("[data-lask]"), b.dataset.la)),
  );
  $$(".ask.live:not(.lask)").forEach((card) => {
    $$(".askopt", card).forEach((b) => (b.onclick = () => askAnswer(card, b.dataset.ans)));
    $(".askown", card).onsubmit = (e) => {
      e.preventDefault();
      askAnswer(card, $("input", card).value.trim());
    };
  });
  $$("[data-askset]").forEach((b) => (b.onclick = (e) => (e.stopPropagation(), askSettings(b))));
  // past questions: show what was answered (the owner's next message)
  $$(".ask.done:not(.answered)").forEach((card) => {
    let m = card.closest(".msg");
    while (m && (m = m.nextElementSibling) && !m.classList.contains("user"));
    const t = m && $(".b", m) ? $(".b", m).textContent.trim() : "";
    if (t) markAsk(card, t);
  });
}
// digits 1–9 choose an option of the open question, unless the owner is typing
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.altKey || e.metaKey || !/^[1-9]$/.test(e.key)) return;
  if (e.target.closest && e.target.closest("input,textarea,select,[contenteditable=true]")) return;
  const cards = $$(".ask.live:not(.lask)");
  const card = cards[cards.length - 1];
  const b = card && $$(".askopt", card)[+e.key - 1];
  if (b) {
    e.preventDefault();
    askAnswer(card, b.dataset.ans);
  }
});
async function askSettings(anchor) {
  const ag = await api("/api/agent");
  const on = Object.fromEntries(ag.catalog.flatMap((s) => s.items).map((i) => [i.id, i.on]));
  const flip = async (id) => {
    await post("/api/agent", { toggles: { [id]: !on[id] } });
    toast(tr("Сохранено. Сработает со следующего ответа"));
  };
  menu(anchor, [
    { label: tr("Задавать вопросы вариантами"), icon: "chat", check: !!on.ask_options, run: () => flip("ask_options") },
    {
      label: tr("Пояснять варианты и зачем спрашиваю"),
      icon: "hint",
      check: !!on.ask_hints,
      run: () => flip("ask_hints"),
    },
    { label: tr("Спрашивать только по делу"), icon: "check", check: !!on.ask_when, run: () => flip("ask_when") },
    "-",
    { label: tr("Все правила общения"), icon: "set", run: () => goSet("style/c-rules") },
  ]);
}
function renderChat(c) {
  CHAT.chat = c;
  CHAT.cons = c.consortium || null;
  drawModelLabel();
  $("#ctitle").textContent = c.title || tr("Разговор");
  const ms = c.messages || [];
  // a question card of Mnemai's own under the answer doesn't take «the last answer» away from it
  const tail = ms.length - 1 - (ms.length && ms[ms.length - 1].kind === "self_ask" ? 1 : 0);
  const lastAi = ms
    .slice(0, tail + 1)
    .map((m) => m.role)
    .lastIndexOf("assistant");
  let rnd = 0;
  const stick = msgsNearBottom();
  $("#msgs").innerHTML =
    ms
      .map((m, i) => {
        let sep = "";
        if (m.kind === "cons_start" || m.kind === "cons_end") rnd = 0;
        if (m.speaker && m.round && m.round !== rnd) {
          rnd = m.round;
          sep = `<div class="rsep"><span>${tr("Круг")} ${m.round}${m.stage && m.stage !== "Итог" ? " · " + tr(m.stage) : ""}</span></div>`;
        }
        return sep + msgHtml(m, i === tail, i, i === lastAi && i === tail);
      })
      .join("") +
    [learnAsksHtml(c), costTipHtml(c)].map((h) => (h ? `<div class="msg lwrap">${h}</div>` : "")).join("");
  bindMsg();
  bindCostTip();
  if (stick) scrollEnd();
  drawPrivate();
  drawTable();
}
function markTerms() {
  const ms = (CHAT.chat && CHAT.chat.messages) || [];
  $$("#msgs .msg.ai[data-i]").forEach((el) => {
    const m = ms[+el.dataset.i];
    if (!m || !m.terms || el.dataset.t) return;
    el.dataset.t = 1;
    const md = $(".md", el);
    if (!md) return;
    for (const { t, d } of [...m.terms].sort((a, b) => b.t.length - a.t.length)) {
      const re = new RegExp(
        "(^|[^\\p{L}\\p{N}])(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?=[^\\p{L}\\p{N}]|$)",
        "iu",
      );
      const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) =>
          n.parentElement.closest("code,pre,a,.term") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
      });
      let n;
      while ((n = w.nextNode())) {
        const x = re.exec(n.nodeValue);
        if (!x) continue;
        const start = x.index + x[1].length,
          r = document.createRange();
        r.setStart(n, start);
        r.setEnd(n, start + x[2].length);
        const sp = document.createElement("span");
        sp.className = "term";
        sp.dataset.t = t;
        sp.dataset.d = d;
        r.surroundContents(sp);
        break;
      }
    }
  });
}
document.addEventListener("mouseover", (e) => {
  const t = e.target.closest && e.target.closest(".term");
  const old = $(".ttip");
  if (!t || document.body.classList.contains("noterms")) {
    if (old) old.remove();
    return;
  }
  if (old && old._for === t) return;
  if (old) old.remove();
  const tip = document.createElement("div");
  tip.className = "ttip";
  tip._for = t;
  tip.innerHTML = `<b>${esc(t.dataset.t)}</b>${esc(t.dataset.d)}`;
  document.body.appendChild(tip);
  const r = t.getBoundingClientRect(),
    w = tip.offsetWidth,
    h = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px";
  tip.style.top = (r.top - h - 8 < 8 ? r.bottom + 8 : r.top - h - 8) + "px";
});
document.addEventListener(
  "scroll",
  () => {
    const o = $(".ttip");
    if (o) o.remove();
  },
  true,
);
function bindMsg() {
  markTerms();
  $$("[data-webredo]").forEach((b) => (b.onclick = webRedo));
  $$("[data-sa]").forEach((card) =>
    $$("[data-saa]", card).forEach(
      (b) =>
        (b.onclick = async () => {
          const act = b.dataset.saa,
            inp = $("[data-satext]", card);
          if (act === "changed" && inp.hidden) {
            inp.hidden = false;
            inp.focus();
            b.dataset.saa = "changed";
            return;
          }
          if ((act === "changed" || act === "goal") && !inp.value.trim()) return inp.focus();
          $$("[data-saa]", card).forEach((x) => (x.disabled = true));
          try {
            renderChat(
              await post("/api/chat/self_ask", {
                chat: CHAT.id,
                i: +card.dataset.sa,
                action: act,
                text: inp ? inp.value : "",
              }),
            );
          } catch (e) {
            toast(e.message);
            $$("[data-saa]", card).forEach((x) => (x.disabled = false));
          }
        }),
    ),
  );
  $$("[data-offer]").forEach(
    (b) =>
      (b.onclick = async () => {
        $$("[data-offer]").forEach((x) => (x.disabled = true));
        try {
          await post("/api/prompts/answer", { chat: CHAT.id, choice: b.dataset.offer });
          $("#msgs").insertAdjacentHTML(
            "beforeend",
            `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`,
          );
          scrollEnd();
          poll();
        } catch (e) {
          toast(e.message);
        }
      }),
  );
  bindAsk();
  $$("[data-copy]").forEach(
    (b) =>
      (b.onclick = () => {
        navigator.clipboard.writeText(CHAT.chat.messages[+b.dataset.copy].text).then(() => toast("Скопировано"));
      }),
  );
  $$("[data-debate]").forEach((b) => (b.onclick = () => debateAnswer(+b.dataset.debate)));
  $$("[data-share]").forEach((b) => (b.onclick = () => shareSummary(+b.dataset.share)));
  $$("[data-reply]").forEach((b) => (b.onclick = () => setQuote(CHAT.chat.messages[+b.dataset.reply].text)));
}
function setQuote(t) {
  CHAT.quote = String(t || "").trim();
  const q = $("#qbar");
  if (!q) return;
  q.hidden = !CHAT.quote;
  q.innerHTML = CHAT.quote
    ? `${ic("quote")}<div>${esc(CHAT.quote.length > 600 ? CHAT.quote.slice(0, 600) + "…" : CHAT.quote)}</div><b title="Убрать цитату">×</b>`
    : "";
  if (CHAT.quote) {
    $("b", q).onclick = () => setQuote("");
    $("#inp").focus();
  }
}
// select a piece of an answer → «Цитировать»
document.addEventListener("mouseup", (e) => {
  setTimeout(() => {
    const old = $(".selq");
    if (old && old.contains(e.target)) return;
    if (old) old.remove();
    const sel = window.getSelection();
    const t = String(sel || "").trim();
    if (!t || !sel.rangeCount) return;
    const node = sel.anchorNode && (sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentElement);
    if (!node || !node.closest(".msg.ai .md")) return;
    const r = sel.getRangeAt(0).getBoundingClientRect();
    const b = document.createElement("button");
    b.className = "selq";
    b.innerHTML = ic("quote") + "Цитировать";
    b.style.left = Math.max(8, r.left + r.width / 2 - 55) + "px";
    b.style.top = Math.max(8, r.top - 40) + "px";
    b.onmousedown = (ev) => ev.preventDefault();
    b.onclick = () => {
      setQuote(t);
      b.remove();
      sel.removeAllRanges();
    };
    document.body.appendChild(b);
  }, 10);
});
document.addEventListener("mousedown", (e) => {
  const q = $(".selq");
  if (q && !q.contains(e.target)) q.remove();
});
function scrollEnd() {
  const m = $("#msgs");
  if (m) m.scrollTop = m.scrollHeight;
}
// follow the answer only when the owner is at the bottom: reading above must not be interrupted by a jump
function msgsNearBottom() {
  const m = $("#msgs");
  return !m || m.scrollHeight - m.scrollTop - m.clientHeight < 200;
}
function scrollIfNear() {
  if (msgsNearBottom()) scrollEnd();
}
async function startByMnema() {
  if (CHAT.polling || CHAT.id) return;
  $("#msgs").innerHTML =
    `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`;
  try {
    const r = await post("/api/chat/send", {
      opener: true,
      model: CHAT.model,
      terms: !!LS.get("terms", true),
      ...(CHAT.newPrivate ? { private: true } : {}),
    });
    CHAT.id = r.chat;
    LS.set("lastchat", r.chat);
    if (CHAT.pendingTitle) {
      const nt = CHAT.pendingTitle;
      CHAT.pendingTitle = "";
      r.title = nt;
      post("/api/chat/update", { id: r.chat, title: nt })
        .then(() => drawList(($("#csearch") || {}).value || ""))
        .catch(() => {});
    }
    $("#ctitle").textContent = r.title;
    CHAT.chat = { id: r.chat, title: r.title, private: CHAT.newPrivate, messages: [] };
    if (CHAT.newPrivate) await post("/api/chat/update", { id: r.chat, private: true });
    drawList("");
    poll();
  } catch (e) {
    $("#live") && $("#live").remove();
    toast(e.message);
    renderEmpty();
  }
}
async function webRedo() {
  LS.set("web", true);
  const wc = $("#webchip");
  if (wc) wc.classList.add("on");
  const last = $$("#msgs .msg.ai").pop();
  if (last) last.remove();
  $("#msgs").insertAdjacentHTML(
    "beforeend",
    `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`,
  );
  scrollEnd();
  try {
    await post("/api/chat/redo", { chat: CHAT.id, web: true });
    poll();
  } catch (e) {
    $("#live") && $("#live").remove();
    toast(e.message);
  }
}
async function sendMsg() {
  const inp = $("#inp"),
    text = inp.value.trim(),
    files = CHAT.files || [];
  if (!text && !files.length) return;
  if (CHAT.polling) {
    if (!CHAT.cons) {
      // the answer is still being written: hold the message and send it when the answer is done, never swallow it
      CHAT.queue = CHAT.queue || [];
      CHAT.queue.push({ text, files, quote: CHAT.quote || "" });
      inp.value = "";
      inp.style.height = "auto";
      CHAT.files = [];
      drawFiles();
      setQuote("");
      toast(tr("Ответ ещё пишется — это сообщение уйдёт сразу после него"), 4000);
      return;
    }
    clearInterval(CHAT.polling);
    CHAT.polling = null;
    $("#live") && $("#live").remove();
  } // stepping into the discussion
  const pr = (CHAT.providers || []).find((x) => x.id === String(CHAT.model || "").split(":")[0]);
  if (!CHAT.cons && (!CHAT.model || (CHAT.providers && (!pr || !pr.ready)))) {
    // no model yet: say what to do and open the list where one is connected — the text stays in the field
    toast(
      pr && pr.problem && !pr.disabled
        ? pr.problem
        : pr && pr.disabled
          ? tr("Этот ИИ выключен. Выбери другой слева вверху или включи его — Настройки → ИИ и модели.")
          : tr("Сначала выбери, с каким ИИ говорить: скачай бесплатную модель на компьютер или укажи ключ"),
      7000,
    );
    if ($("#model") && !$(".mmenu")) modelMenu($("#model"));
    return;
  }
  const quote = CHAT.quote || "";
  inp.value = "";
  inp.style.height = "auto";
  CHAT.files = [];
  drawFiles();
  setQuote("");
  if (!CHAT.id) $("#msgs").innerHTML = "";
  $("#msgs").insertAdjacentHTML(
    "beforeend",
    msgHtml({ role: "user", text: text || "Посмотри прикреплённое.", files, quote }) +
      `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`,
  );
  scrollEnd();
  try {
    const fresh = !CHAT.id;
    const r = await post("/api/chat/send", {
      chat: CHAT.id,
      model: CHAT.model,
      text,
      quote,
      web: !!LS.get("web", true),
      terms: !!LS.get("terms", true),
      files: files.map((f) => ({ name: f.name, data: f.data })),
      ...(!CHAT.id && CHAT.cons ? { consortium: CHAT.cons } : {}),
      ...(!CHAT.id && CHAT.newPrivate ? { private: true } : {}), // «Без обучения» holds from the first message
    });
    CHAT.id = r.chat;
    LS.set("lastchat", r.chat);
    if (CHAT.pendingTitle) {
      const nt = CHAT.pendingTitle;
      CHAT.pendingTitle = "";
      r.title = nt;
      post("/api/chat/update", { id: r.chat, title: nt })
        .then(() => drawList(($("#csearch") || {}).value || ""))
        .catch(() => {});
    }
    $("#ctitle").textContent = r.title;
    if (fresh) {
      if (CHAT.newPrivate) await post("/api/chat/update", { id: r.chat, private: true });
      CHAT.chat = {
        id: r.chat,
        title: r.title,
        private: CHAT.newPrivate,
        messages: [],
        consortium: CHAT.cons || undefined,
      };
      drawList("");
    }
    poll();
  } catch (e) {
    const lv = $("#live"); // the reason stays where the answer would be, not in a toast that fades
    if (lv)
      lv.outerHTML = `<div class="msg ai"><div class="av"></div><p class="err">${linkSettings(esc(e.message))}</p></div>`;
    else toast(e.message, 6000);
  }
}
function poll() {
  const btn = $("#send");
  btn.classList.add("stop");
  btn.innerHTML = '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
  const cid = CHAT.id;
  const T = { target: "", shown: 0, phase: "думаю", done: false, error: "", raf: 0, last: "", seq: -1, speaker: "" };
  const frame = () => {
    const live = $("#live");
    if (!live || CHAT.id !== cid) {
      T.raf = 0;
      return;
    }
    const left = T.target.length - T.shown;
    if (left > 0) T.shown += Math.max(1, Math.ceil(left / (T.done ? 6 : 18)));
    const key = T.shown + "|" + T.phase;
    if (key !== T.last) {
      T.last = key;
      const shown = T.target.slice(0, T.shown);
      const sp = $(".spk", live);
      if (T.speaker && !sp) {
        $(".md", live).insertAdjacentHTML(
          "beforebegin",
          `<div class="spk"><i style="background:${spkColor(T.ref)}"></i>${esc(T.speaker)}</div>`,
        );
        live.classList.add("cmsg");
        live.style.setProperty("--sc", spkColor(T.ref));
        const av = $(".av", live);
        if (av) {
          av.classList.add("cav");
          av.style.setProperty("--sc", spkColor(T.ref));
          av.textContent = spkGlyph(T.ref, T.speaker);
        }
      } else if (sp && T.speaker) sp.lastChild.textContent = T.speaker;
      $(".md", live).innerHTML =
        (shown ? md(shown, false) : "") +
        (!shown
          ? QUIET_PHASE.has(T.phase || "")
            ? TYPING
            : `<span class="phase"><i></i>${esc(T.phase)}</span>`
          : "") +
        (T.phase === "проверяю ответ" && shown ? '<span class="phase"><i></i>проверяю ответ</span>' : "");
      const m = $("#msgs");
      if (m && m.scrollHeight - m.scrollTop - m.clientHeight < 200) scrollEnd();
    }
    if (T.done && T.shown >= T.target.length) {
      T.raf = 0;
      finish();
      return;
    }
    T.raf = requestAnimationFrame(frame);
  };
  const finish = async () => {
    btn.classList.remove("stop");
    btn.innerHTML = SEND_ICON;
    CHAT.live = null;
    setTimeout(achRefresh, 600);
    setTimeout(badge, 2500);
    const c = await api("/api/chat?id=" + cid);
    if (CHAT.id !== cid) return;
    renderChat(c);
    drawList($("#csearch") ? $("#csearch").value : "");
    const savedErr = (c.messages || []).some((m) => m.error && m.error === T.error);
    if (T.error && !savedErr)
      // the error is part of the conversation now; this is only for one that was not saved
      $("#msgs").insertAdjacentHTML(
        "beforeend",
        `<div class="msg ai"><div class="av"></div><p class="err">${linkSettings(esc(T.error))}</p></div>`,
      );
    scrollIfNear();
    $("#inp").focus();
    if (CHAT.id === cid && (CHAT.queue || []).length) {
      const q = CHAT.queue.shift();
      $("#inp").value = q.text;
      CHAT.files = q.files || [];
      if (q.quote) setQuote(q.quote);
      drawFiles();
      sendMsg();
      return;
    }
  };
  T.raf = requestAnimationFrame(frame);
  CHAT.polling = setInterval(async () => {
    if (CHAT.id !== cid || !$("#msgs")) {
      clearInterval(CHAT.polling);
      CHAT.polling = null;
      return;
    }
    let st;
    try {
      st = await api("/api/chat/poll?id=" + cid);
    } catch (e) {
      return;
    }
    if (st.seq !== undefined && T.seq !== -1 && st.seq !== T.seq) {
      const c = await api("/api/chat?id=" + cid);
      if (CHAT.id !== cid) return;
      renderChat(c);
      T.shown = 0;
      T.last = "";
    } // a speaker finished
    if (st.status !== undefined) {
      CHAT.live = st;
      drawTable();
    }
    if (st.seq !== undefined) {
      T.seq = st.seq;
      if (st.speaker !== T.speaker) {
        T.speaker = st.speaker;
        T.ref = (CHAT.cons && CHAT.cons.members.find((r) => consName(r) === st.speaker)) || "";
        T.shown = 0;
        T.last = "";
        const lv = $("#live");
        if (lv) lv.remove();
      }
    }
    if (!$("#live"))
      $("#msgs").insertAdjacentHTML(
        "beforeend",
        '<div class="msg ai" id="live"><div class="av"></div><div><div class="md"></div></div></div>',
      );
    if (st.text.length < T.shown) T.shown = 0;
    T.target = st.text;
    T.phase = st.phase;
    T.error = st.error;
    actionAsk(cid, st.pending);
    if (st.done) {
      clearInterval(CHAT.polling);
      CHAT.polling = null;
      T.done = true;
      if (st.error) refreshProviders().catch(() => {}); // an AI out of money or signed out leaves the list at once
    }
    if (!T.raf) T.raf = requestAnimationFrame(frame);
  }, 200);
}

// «?» beside «Новый разговор» and «Новая сессия»: what each one does and why a long conversation costs more
function sessExplain() {
  const pop = document.createElement("div");
  pop.className = "modal sexp";
  const lane = (cls, title, sub, cap) =>
    `<div class="sxlane ${cls}"><div class="sxh"><b>${tr(title)}</b><small>${tr(sub)}</small></div>
      <div class="sxchat">${[1, 2, 3, 4, 5, 6].map((k) => `<i style="--k:${k}"></i>`).join("")}</div>
      <div class="sxbars">${[1, 2, 3, 4, 5, 6].map((k) => `<span style="--k:${k}"><i></i></span>`).join("")}</div>
      <div class="sxmeter"><span></span></div><div class="sxcap">${tr(cap)}</div></div>`;
  pop.innerHTML = `<div class="card sxc"><button class="lmx" data-x>×</button>
    <h2>${tr("Почему долго сидеть в одном разговоре дорого")}</h2>
    <p class="sxd">${tr("Перед каждым ответом модель заново читает всю переписку. Чем длиннее разговор, тем больше токенов уходит на каждый новый ответ: дороже, медленнее, и модель хуже держит главное.")}</p>
    <div class="sxscene">${lane("long", "Один длинный разговор", "каждый ответ тянет за собой всю историю", "токены на ответ растут")}${lane("short", "Новый разговор на новую тему", "память с тобой, лишней истории нет", "токены на ответ не копятся")}</div>
    <div class="sxgrid">
      <div class="sxpt"><span class="sxic">${ic("plus")}</span><div><b>${tr("Новый разговор")}</b><p>${tr("Новая тема в той же сессии. Модель начинает с чистого листа: знает тебя по памяти, но не тащит переписку других разговоров.")}</p></div></div>
      <div class="sxpt"><span class="sxic">${ic("session")}</span><div><b>${tr("Новая сессия")}</b><p>${tr("Новая группа разговоров в списке: новый день или новая задача. Контекст тоже начинается с чистого листа.")}</p></div></div>
    </div>
    <p class="sxtip">${ic("hint")}<span>${tr("Сменилась тема — начни новый разговор. Нужное из прошлого Mnemai уже записала в память.")}</span></p>
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-x>${tr("Понятно")}</button></div></div>`;
  document.body.appendChild(pop);
  const close = () => pop.remove();
  pop.onclick = (e) => {
    if (e.target === pop) close();
  };
  $$("[data-x]", pop).forEach((b) => (b.onclick = close));
}

// who argues: the connected models to tick, the suggestion ticked; the first ticked sums up
function debatePick(all, pre) {
  return new Promise((done) => {
    const chosen = pre.slice();
    const pop = document.createElement("div");
    pop.className = "modal obspick debpick";
    const draw = () => {
      pop.innerHTML = `<div class="card"><h2>${tr("С кем поспорить?")}</h2><p class="hint">${tr("Автор ответа будет его защищать, отмеченные ИИ — искать в нём ошибки. Итог подведёт первый отмеченный. До трёх соперников.")}</p>
        <div class="obslist">${all
          .map((a, k) => {
            const n = chosen.indexOf(a.ref);
            return `<button class="obsv ${n >= 0 ? "on" : ""}" data-k="${k}"><i>${n >= 0 ? n + 1 : ""}</i><div><b data-noi18n>${esc(a.name)}</b></div><span>${n === 0 ? tr("подведёт итог") : ""}</span></button>`;
          })
          .join("")}</div>
        <div class="row" style="justify-content:flex-end;gap:8px;margin-top:16px"><button class="btn g" data-x>${tr("Отмена")}</button><button class="btn" data-go ${chosen.length ? "" : "disabled"}>${tr("Начать спор")}</button></div></div>`;
      $$("[data-k]", pop).forEach(
        (b) =>
          (b.onclick = () => {
            const r = all[+b.dataset.k].ref,
              n = chosen.indexOf(r);
            if (n >= 0) chosen.splice(n, 1);
            else if (chosen.length < 3) chosen.push(r);
            else return toast(tr("Не больше трёх соперников"));
            draw();
          }),
      );
      $("[data-x]", pop).onclick = () => close(null);
      $("[data-go]", pop).onclick = () => chosen.length && close(chosen);
    };
    const close = (v) => {
      pop.remove();
      done(v);
    };
    pop.onclick = (e) => e.target === pop && close(null);
    draw();
    document.body.appendChild(pop);
  });
}
// «Поспорить с разными ИИ»: the answer's author defends it, one or two other connected AIs question it, then a verdict
async function debateAnswer(i) {
  const msgs = CHAT.chat.messages,
    m = msgs[i],
    by = m.model || CHAT.chat.model || CHAT.model;
  const question =
    (
      msgs
        .slice(0, i)
        .reverse()
        .find((x) => x.role === "user") || {}
    ).text || "";
  let provs = CHAT.providers;
  try {
    provs = (await api("/api/models")).providers;
  } catch (e) {}
  // other AIs first; then other models of the same one — Sonnet argues with Opus just as well
  const [mine, own] = String(by).split(":"),
    myP = (provs || []).find((p) => p.id === mine),
    myModel = own || (myP && myP.models && myP.models[0] ? myP.models[0].id : ""),
    elsewhere = (provs || [])
      .filter((p) => p.ready && p.id !== mine && p.models && p.models.length)
      .map((p) => p.id + ":" + (p.models.find((x) => x.id) || p.models[0]).id),
    siblings =
      myP && myP.ready ? (myP.models || []).filter((x) => x.id && x.id !== myModel).map((x) => mine + ":" + x.id) : [];
  // every connected model but the author can be picked; the suggestion is ticked already
  const all = (provs || [])
    .filter((p) => p.ready && p.models && p.models.length)
    .flatMap((p) =>
      p.models
        .filter((x) => (x.id || p.id !== mine) && !(p.id === mine && x.id === myModel))
        .filter((x) => x.id || p.models.length === 1)
        .map((x) => ({
          ref: p.id + ":" + x.id,
          name: x.name && x.name !== x.id ? x.name : p.name + (x.id ? " · " + x.id : ""),
          group: p.name,
        })),
    );
  if (!all.length) {
    toast(tr("Чтобы было с кем спорить, подключи ещё один ИИ: Настройки → ИИ и модели"));
    return;
  }
  const others = await debatePick(
    all,
    [...elsewhere, ...siblings].filter((r) => all.some((a) => a.ref === r)).slice(0, 2),
  );
  if (!others) return;
  try {
    await post("/api/chat/cons", {
      chat: CHAT.id,
      action: "start",
      members: [by, ...others],
      rounds: 2,
      format: "debate",
      summarizer: others[0],
      challenge: { by, answer: m.text, question },
    });
    renderChat(await api("/api/chat?id=" + CHAT.id));
    $("#msgs").insertAdjacentHTML(
      "beforeend",
      `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`,
    );
    scrollEnd();
    poll();
  } catch (e) {
    toast(e.message);
  }
}
