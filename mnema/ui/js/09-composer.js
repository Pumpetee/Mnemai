// ---------------------------------------------------------------- the input line, as the owner likes it
const COMP_ITEMS = [
  ["clip", "clip", "Скрепка", "файлы и картинки"],
  ["plusb", "plus", "Ещё", "меню «+»"],
  ["termchip", "hint", "Подсказки", "пояснения к терминам"],
  ["privchip", "eyeoff", "Без обучения", "разговор не учит память"],
  ["conschip", "users", "Консорциум", "несколько ИИ обсуждают"],
  ["micb", "mic", "Микрофон", "команда голосом и встречи"],
];
const COMP_DEF = {
  order: COMP_ITEMS.map((x) => x[0]),
  off: ["termchip"],
  placeholder: "",
  rows: 1,
  send: "enter",
  labels: true,
};
function compCfg() {
  const c = { ...COMP_DEF, ...LS.get("composer", {}) };
  c.order = [
    ...c.order.filter((k) => COMP_ITEMS.some((x) => x[0] === k)),
    ...COMP_ITEMS.map((x) => x[0]).filter((k) => !c.order.includes(k)),
  ];
  return c;
}
function applyComposer() {
  const bar = $(".cbar");
  if (!bar) return;
  const c = compCfg(),
    st = $("#cstate", bar),
    send = $("#send", bar);
  if (!$("#termchip", bar)) {
    const b = document.createElement("button");
    b.className = "cchip";
    b.id = "termchip";
    b.title = tr("Подсказки к терминам");
    b.innerHTML = `${ic("hint")}<span>${tr("Подсказки")}</span>${hq("hints")}`;
    b.onclick = () => {
      const on = !LS.get("terms", true);
      LS.set("terms", on);
      document.body.classList.toggle("noterms", !on);
      b.classList.toggle("on", on);
      drawState();
    };
    bar.insertBefore(b, st);
  }
  $("#termchip", bar).classList.toggle("on", LS.get("terms", true));
  const left = c.order.filter((k) => k !== "micb");
  left.forEach((k) => {
    const el = $("#" + k, bar);
    if (el) bar.insertBefore(el, st);
  });
  const mic = $("#micb", bar);
  if (mic) bar.insertBefore(mic, send);
  const planb = $("#planchip", bar);
  if (planb) bar.insertBefore(planb, st); // always right after the consortium chip, before the status
  c.order.forEach((k) => {
    const el = $("#" + k, bar);
    if (el) el.hidden = c.off.includes(k);
  });
  bar.classList.toggle("nolabels", !c.labels);
  const inp = $("#inp"),
    stline = $("#cstatus");
  if (inp) {
    inp.placeholder = "";
    inp.classList.toggle("empty", !inp.value);
    inp.rows = Math.max(1, Math.min(8, c.rows));
    inp.style.minHeight = c.rows > 1 ? c.rows * 22 + "px" : "";
  }
  if (stline) {
    stline.textContent = c.placeholder || statusText();
    stline.hidden = !stline.textContent;
    stline.classList.toggle("hastext", !!(inp && inp.value));
  }
}
let COMP_LAST = null; // the switch just flipped: its button pops in the sample, or fades out of it
function compCard(id) {
  const c = compCfg(),
    last = COMP_LAST;
  COMP_LAST = null;
  return `<div class="card" data-sec="app" id="${id || "compcard"}"><h2>${tr("Строка ввода")}<span class="hint">${tr("что под полем и в каком порядке")}</span></h2>
   <div class="cpvbox"><div class="cpvh"><span>${tr("Пример")}</span><em><i></i>${tr("меняется сразу, когда включаешь и выключаешь кнопки ниже")}</em></div>
   <div class="cpvin" style="--rows:${c.rows}"><span>${esc(c.placeholder || tr("Напиши что угодно — я помню тебя и учусь по ходу"))}</span><kbd>${c.send === "enter" ? "Enter" : "Ctrl+Enter"} ↵</kbd></div>
   <div class="cpv">${c.order
     .filter((k) => !c.off.includes(k) || (last && last.k === k))
     .map((k) => {
       const it = COMP_ITEMS.find((x) => x[0] === k),
         fx = last && last.k === k ? (c.off.includes(k) ? "gone" : "cpop") : "";
       return `<span class="${k === "micb" ? "m" : ""} ${fx}">${ic(it[1])}${c.labels && ["termchip", "privchip", "conschip"].includes(k) ? `<em>${tr(it[2])}</em>` : ""}</span>`;
     })
     .join("")}<b class="sendpv">${SEND_ICON}</b></div></div>
   <div class="clist2">${c.order
     .map((k) => {
       const it = COMP_ITEMS.find((x) => x[0] === k);
       return `<div class="crow" draggable="true" data-ck="${k}"><i class="grip">⋮⋮</i>${ic(it[1])}<div><b>${tr(it[2])}</b><small>${tr(it[3])}</small></div><button class="sw ${c.off.includes(k) ? "" : "on"}" data-cs="${k}"></button></div>`;
     })
     .join("")}</div>
   <div class="hint" style="margin:6px 0 12px">${tr("Перетащи строку, чтобы поменять порядок.")}</div>
   <div class="set"><b>${tr("Подсказка в поле")}</b><div><input class="inp" data-cp="placeholder" placeholder="${esc(tr("Напиши что угодно — я помню тебя и учусь по ходу"))}" value="${esc(c.placeholder)}" style="width:100%"></div></div>
   <div class="set"><b>${tr("Высота поля")}</b><div><div class="seg" data-cseg="rows">${[
     [1, "1 строка"],
     [2, "2"],
     [3, "3"],
     [5, "5"],
   ]
     .map(([v, l]) => `<button data-v="${v}" class="${c.rows == v ? "on" : ""}">${tr(l)}</button>`)
     .join("")}</div></div></div>
   <div class="set"><b>${tr("Отправка")}</b><div><div class="seg" data-cseg="send">${[
     ["enter", "Enter"],
     ["ctrl", "Ctrl+Enter"],
   ]
     .map(([v, l]) => `<button data-v="${v}" class="${c.send === v ? "on" : ""}">${l}</button>`)
     .join(
       "",
     )}</div><div class="hint" style="margin-top:4px">${c.send === "enter" ? tr("Shift+Enter — новая строка") : tr("Enter — новая строка")}</div></div></div>
   <div class="set"><b>${tr("Подписи у кнопок")}</b><div><button class="sw ${c.labels ? "on" : ""}" data-cl></button></div></div></div>`;
}
function bindCompCard(card, redraw) {
  const save = (p) => {
    LS.set("composer", { ...compCfg(), ...p });
    applyComposer();
    redraw();
  };
  $$("[data-cs]", card).forEach(
    (b) =>
      (b.onclick = () => {
        const c = compCfg(),
          k = b.dataset.cs;
        COMP_LAST = { k };
        save({ off: c.off.includes(k) ? c.off.filter((x) => x !== k) : [...c.off, k] });
      }),
  );
  $$("[data-cseg]", card).forEach((sg) =>
    $$("button", sg).forEach(
      (b) => (b.onclick = () => save({ [sg.dataset.cseg]: sg.dataset.cseg === "rows" ? +b.dataset.v : b.dataset.v })),
    ),
  );
  $("[data-cp]", card).onchange = (e) => save({ placeholder: e.target.value.trim() });
  $("[data-cl]", card).onclick = () => save({ labels: !compCfg().labels });
  let drag = null;
  $$(".crow", card).forEach((r) => {
    r.ondragstart = () => {
      drag = r.dataset.ck;
      r.classList.add("drag");
    };
    r.ondragend = () => r.classList.remove("drag");
    r.ondragover = (e) => {
      e.preventDefault();
      r.classList.add("over");
    };
    r.ondragleave = () => r.classList.remove("over");
    r.ondrop = (e) => {
      e.preventDefault();
      r.classList.remove("over");
      const c = compCfg(),
        o = c.order.filter((k) => k !== drag),
        at = o.indexOf(r.dataset.ck);
      o.splice(at, 0, drag);
      save({ order: o });
    };
  });
}
function compModal() {
  if ($(".cmpm")) return;
  const pop = document.createElement("div");
  pop.className = "modal cmpm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  const draw = () => {
    pop.innerHTML = compCard("compm");
    const c = $("#compm", pop);
    c.insertAdjacentHTML("afterbegin", '<button class="lmx" data-x style="float:right">×</button>');
    $("[data-x]", pop).onclick = () => pop.remove();
    bindCompCard(c, draw);
  };
  draw();
}
