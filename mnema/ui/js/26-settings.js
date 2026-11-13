// ---------------------------------------------------------------- settings
const AUTO_HINT = {
  observe: "Только показывает, что заметила. Ничего не пишет.",
  approve: "Всё новое ждёт тебя.",
  mixed: "Уверенное записывает сама, личное и спорное спрашивает.",
  quiet: "Пишет всё сама, ты откатываешь лишнее.",
};
// A subscription may still require a provider-issued access key.  Billing type
// is deliberately separate from the way credentials are supplied.
const isSubscription = (p) => !!p.subscription || ["claude_code", "codex", "opencode_go"].includes(p.id);
// «Настройки по умолчанию»: Движок, Записи встреч and Программа; memory, keys, proxy and folders stay
async function settingsReset() {
  if (
    !(await ask(
      "Вернуть настройки по умолчанию?",
      "Движок, Записи встреч и Программа станут как после установки. Память, ключи, прокси, VPN и папки останутся как есть.",
      "Вернуть",
      false,
    ))
  )
    return;
  try {
    await post("/api/settings/reset");
    if (APP.desktop) APP = await post("/api/app/close_pref", { value: "ask" }).catch(() => APP);
    LS.set("theme", {});
    applyTheme();
    toast(tr("Настройки по умолчанию"));
    viewSettings(SETCUR);
  } catch (e) {
    toast(e.message);
  }
}
// several memories on one computer: the open one, the others to switch to, a new one, delete
async function drawVaults() {
  const box = $("#vaultsw");
  if (!box || !APP.desktop) return;
  let d;
  try {
    d = await api("/api/app/vaults");
  } catch (e) {
    return;
  }
  if (!d || !d.list) return;
  box.innerHTML = `<div class="vswh">${tr("Память")}</div>${d.list
    .map(
      (v, k) =>
        `<div class="mvrow ${v.path === d.current ? "cur" : ""} ${v.exists ? "" : "gone"}" title="${esc(v.path)}"><button class="vname" data-vo="${k}">${ic(v.path === d.current ? "check" : "mem")}<span data-noi18n>${esc(v.name)}</span></button><button class="vmore kebab" data-vm="${k}" title="${tr("Ещё")}">${ic("dots")}</button></div>`,
    )
    .join("")}<button class="vnew" id="vnew">${ic("plus")}<span>${tr("Новая память")}</span></button>`;
  $$("[data-vo]", box).forEach(
    (b) =>
      (b.onclick = async () => {
        const v = d.list[+b.dataset.vo];
        if (v.path === d.current) return;
        if (!v.exists) return toast(tr("Этой папки сейчас нет. Проверь, подключён ли диск."));
        const r = await post("/api/app/vault_open", { path: v.path }).catch((e) => ({ error: e.message }));
        if (r.error) toast(r.error);
        else toast(tr("Открываю") + " " + v.name);
      }),
  );
  $$("[data-vm]", box).forEach(
    (b) =>
      (b.onclick = () => {
        const v = d.list[+b.dataset.vm];
        const rename = async () => {
          const name = await askText("Как назвать эту память?", v.name, "Папка на диске сохранит своё имя.");
          if (name === null) return;
          const r = await post("/api/app/vault_rename", { path: v.path, name }).catch((e) => ({ error: e.message }));
          if (r.error) return toast(r.error);
          drawVaults();
        };
        const remove = async () => {
          const open = v.path === d.current;
          if (
            !(await ask(
              open ? "Удалить открытую память?" : "Удалить эту память?",
              open
                ? "Mnemai закроет её и уберёт папку в корзину, вернуть можно оттуда."
                : "Папка уйдёт в корзину, вернуть можно оттуда.",
            ))
          )
            return;
          // the second check: the name once more, and the button wakes up after 10 seconds
          if (
            !(await dlg({
              title: tr("Точно удалить") + " «" + v.name + "»?",
              text: "Всё, что Mnemai о тебе узнала в этой памяти, — портрет, факты, разговоры и история — уйдёт в корзину вместе с папкой.",
              ok: "Удалить",
              danger: true,
              wait: 10,
            }))
          )
            return;
          const r = await post("/api/app/vault_forget", { path: v.path, delete: true }).catch((e) => ({
            error: e.message,
          }));
          if (r.error) return toast(r.error);
          if (r.closing) return toast(tr("Закрываю память и убираю папку в корзину"));
          toast(tr("Папка памяти в корзине"));
          drawVaults();
        };
        menu(b, [
          { label: tr("Переименовать"), icon: "edit", run: rename },
          { label: tr("Удалить"), icon: "trash", danger: true, run: remove },
        ]);
      }),
  );
  $("#vnew", box).onclick = async () => {
    if (
      await ask("Создать новую память?", "Откроется первый экран, текущая память останется в списке.", "Создать", false)
    )
      api("/api/app/switch");
  };
}
// Telegram: Mnemai learns from the conversations in the chats the owner picked; read only — the client itself refuses anything but reading
const TG_LOGO = `<svg viewBox="0 0 24 24" class="tglogo"><circle cx="12" cy="12" r="12" fill="#229ED9"/><path d="M5.4 11.7l11.6-4.5c.5-.2 1 .1.8.9l-2 9.3c-.1.6-.5.8-1 .5l-2.9-2.2-1.4 1.4c-.2.2-.3.3-.6.3l.2-3 5.4-4.9c.2-.2 0-.3-.3-.1l-6.7 4.2-2.9-.9c-.6-.2-.6-.6.1-.9z" fill="#fff"/></svg>`;
async function drawTg() {
  const box = $("#c-tg");
  if (!box) return;
  let r;
  try {
    r = await api("/api/telegram");
  } catch (e) {
    box.innerHTML = `<h2>Telegram</h2><p class="err">${esc(e.message)}</p>`;
    return;
  }
  const step = r.set ? 4 : r.step === "password" ? 3 : r.step === "code" ? 2 : 1;
  const st = (n, title, body) =>
    `<li class="${n < step ? "done" : n === step ? "on" : ""}"><i>${n < step ? ic("check") : n}</i><div><b>${tr(title)}</b>${n === step ? body : ""}</div></li>`;
  const body = r.set
    ? `<div class="tgok"><span class="tgava">${esc((r.who || "?").slice(0, 1).toUpperCase())}</span><div><b>${esc(r.who || "")}</b><small>${tr("Подключено · новые сообщения читаются в каждом цикле обучения")}</small></div><button class="btn g sm" id="tgrforget">${tr("Отключить")}</button></div>`
    : `<ol class="tgsteps">
        ${st(
          1,
          "Ключи приложения",
          `<p class="hint">${tr("Открой my.telegram.org, войди по своему номеру, выбери «API development tools», создай приложение с любым названием и скопируй api_id и api_hash. Это бесплатно и занимает минуту.")}</p>
           <div class="row"><a class="btn l sm" href="https://my.telegram.org/apps" target="_blank">${tr("Открыть my.telegram.org")}</a></div>
           <div class="tgfields"><input class="inp" id="tgaid" placeholder="api_id" value="${esc(r.api_id || "")}"><input class="inp" id="tgahash" type="password" placeholder="api_hash"><input class="inp" id="tgphone" placeholder="${tr("+7 номер телефона")}" value="${esc(r.phone || "")}"><button class="btn" id="tgrgo">${tr("Получить код")}</button></div>`,
        )}
        ${st(
          2,
          "Код из Telegram",
          `<p class="hint">${tr("Telegram прислал код в чат «Telegram» на твоём телефоне.")}</p><div class="tgfields"><input class="inp" id="tgcode" placeholder="${tr("код")}" inputmode="numeric"><button class="btn" id="tgcodego">${tr("Войти")}</button></div>`,
        )}
        ${st(
          3,
          "Облачный пароль",
          `<p class="hint">${tr("У тебя включена двухэтапная проверка: введи облачный пароль Telegram.")}</p><div class="tgfields"><input class="inp" id="tgpw" type="password" placeholder="${tr("облачный пароль")}"><button class="btn" id="tgpwgo">${tr("Войти")}</button></div>`,
        )}
      </ol>`;
  const chats = r.chats || [];
  const chatList = `<div class="tgchats"><div class="tgch"><b>${tr("Чаты для чтения")}</b>${r.set ? `<button class="btn l sm" id="tgadd">${ic("plus")}${tr("Добавить чаты")}</button>` : ""}</div>
    ${
      chats.length
        ? `<div class="tgcl">${chats
            .map(
              (c, k) =>
                `<div class="tgci"><span class="tgava sm">${c.kind === "group" ? ic("users") : c.kind === "self" ? ic("pin") : esc((c.name || "?").slice(0, 1).toUpperCase())}</span><span data-noi18n>${esc(c.name)}</span><button class="kebab" data-tgdel="${k}" title="${tr("Убрать")}">${ic("x")}</button></div>`,
            )
            .join("")}</div>`
        : `<p class="hint">${r.set ? tr("Пока ни одного чата — Mnemai ничего не читает. Добавь чаты, по которым она будет тебя узнавать.") : tr("Чаты появятся здесь после входа: ты сам выберешь, какие Mnemai читает.")}</p>`
    }</div>`;
  box.innerHTML = `<div class="tghead">${TG_LOGO}<div><h2>Telegram</h2><p>${tr("Mnemai узнаёт тебя и людей вокруг по твоим перепискам в Telegram")}</p></div><span class="tgro">${ic("lock")}${tr("Только чтение")}</span></div>
    <div class="tgsafe"><span>${ic("check")}${tr("Читает переписку целиком — твои сообщения и собеседников, только в чатах, которые ты выбрал")}</span><span>${ic("check")}${tr("Ничего не отправляет, не удаляет и не отмечает прочитанным")}</span><span>${ic("check")}${tr("Каналы и ботов пропускает")}</span></div>
    <p class="tgnote">${tr("Запрет заложен в саму программу: клиент Telegram внутри Mnemai умеет только читать, любая другая команда отклоняется до отправки.")}</p>
    <div class="tglocal">${ic("shield")}<div><b>${tr("Всё хранится только на этом компьютере")}</b><p>${tr("Вход в Telegram зашифрован в защищённом хранилище системы, список чатов и то, что Mnemai из них поняла, лежат в папке памяти. Своих серверов у Mnemai нет, переписка никуда не копируется. ИИ получает только нужные места, когда ты задаёшь вопрос.")}</p></div></div>
    ${body}${chatList}`;
  const rdp = (b) =>
    post("/api/telegram", b)
      .then(drawTg)
      .catch((e) => toast(e.message));
  const on = (id, f) => $("#" + id, box) && ($("#" + id, box).onclick = f);
  const filled = (...ids) => {
    const gap = ids.map((id) => $("#" + id, box)).find((x) => x && !x.value.trim());
    if (gap) gap.focus();
    return !gap;
  };
  on(
    "tgrgo",
    () =>
      filled("tgaid", "tgahash", "tgphone") &&
      rdp({ api_id: $("#tgaid").value, api_hash: $("#tgahash").value, phone: $("#tgphone").value }),
  );
  on("tgcodego", () => filled("tgcode") && rdp({ code: $("#tgcode").value }));
  on("tgpwgo", () => filled("tgpw") && rdp({ password: $("#tgpw").value }));
  on("tgadd", () => tgPick(chats));
  $$("[data-tgdel]", box).forEach(
    (b) => (b.onclick = () => rdp({ chats: chats.filter((_, k) => k !== +b.dataset.tgdel) })),
  );
  on(
    "tgrforget",
    async () =>
      (await ask("Отключить Telegram?", "Mnemai забудет вход и перестанет читать переписку.", "Отключить")) &&
      rdp({ forget: true }),
  );
}
// the owner's chats to pick from: Mnemai reads only the picked ones
async function tgPick(cur) {
  const head = `<div class="obshead">${TG_LOGO}<div><h2>${tr("Чаты для чтения")}</h2><p class="hint">${tr("Mnemai будет читать переписку целиком — твои сообщения и собеседников — только в отмеченных чатах. Каналы и боты в список не попадают.")}</p></div></div>`;
  const pop = document.createElement("div");
  pop.className = "modal obspick tgpick";
  pop.innerHTML = `<div class="card">${head}<p class="hint">${tr("загружаю…")}</p></div>`;
  pop.onclick = (e) => e.target === pop && pop.remove();
  document.body.appendChild(pop);
  let list;
  try {
    list = (await api("/api/telegram/chats")).chats;
  } catch (e) {
    pop.remove();
    return toast(e.message);
  }
  const chosen = new Map(cur.map((c) => [c.id, c]));
  let q = "";
  const draw = () => {
    const shown = list.filter((c) => !q || c.name.toLowerCase().includes(q));
    pop.querySelector(".card").innerHTML = `${head}
      <input class="inp tgq" placeholder="${tr("Найти чат")}" value="${esc(q)}">
      <div class="obslist tglist">${shown
        .map(
          (c) =>
            `<button class="obsv ${chosen.has(c.id) ? "on" : ""}" data-id="${esc(c.id)}"><i>${chosen.has(c.id) ? ic("check") : ""}</i><div><b data-noi18n>${esc(c.name)}</b></div><span>${c.kind === "group" ? tr("группа") : c.kind === "self" ? tr("твои заметки") : tr("личный чат")}</span></button>`,
        )
        .join("")}${shown.length ? "" : `<p class="hint">${tr("Ничего не нашлось")}</p>`}</div>
      <div class="row" style="justify-content:space-between;margin-top:14px"><span class="hint">${tr("Выбрано")}: ${chosen.size}</span><div class="row" style="gap:8px"><button class="btn g" data-x>${tr("Отмена")}</button><button class="btn" id="tgok">${tr("Сохранить")}</button></div></div>`;
    const inp = $(".tgq", pop);
    inp.oninput = () => {
      q = inp.value.trim().toLowerCase();
      draw();
      const i = $(".tgq", pop);
      i.focus();
      i.setSelectionRange(i.value.length, i.value.length);
    };
    $$("[data-id]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          const c = list.find((x) => x.id === b.dataset.id);
          chosen.has(c.id) ? chosen.delete(c.id) : chosen.set(c.id, c);
          draw();
        }),
    );
    $("[data-x]", pop).onclick = () => pop.remove();
    $("#tgok", pop).onclick = async () => {
      try {
        await post("/api/telegram", { chats: [...chosen.values()].map(({ id, name, kind }) => ({ id, name, kind })) });
      } catch (e) {
        return toast(e.message);
      }
      pop.remove();
      toast(
        chosen.size
          ? tr("Чаты сохранены: Mnemai прочитает их в ближайшем цикле обучения")
          : tr("Чаты убраны: Mnemai ничего не читает"),
      );
      drawTg();
    };
  };
  draw();
}
// «Подключить Obsidian»: the vaults Obsidian knows on this computer, ticked ones become extra memory folders
const OBS_LOGO = `<svg viewBox="0 0 24 24" class="obslogo"><path d="M16.2 2.4c-.6-.5-1.5-.5-2.1 0L7.3 7.8c-.4.3-.6.8-.6 1.3l.4 5.6c0 .3.2.7.4.9l4.2 5.6c.5.6 1.4.8 2 .3l3.8-2.6c.5-.3.7-.9.6-1.5l-.4-2.4c-.1-.4 0-.9.3-1.2l1.7-2.1c.4-.5.4-1.2.1-1.7L16.2 2.4z" fill="#7c3aed"/><path d="M11.6 9.2l2.9-4.6 2.4 5.6-2 2.6c-.6-.9-1.7-2.3-3.3-3.6z" fill="#a78bfa"/></svg>`;
async function obsidianPick(prof) {
  let d;
  try {
    d = await api("/api/obsidian");
  } catch (e) {
    return toast(e.message);
  }
  const pop = document.createElement("div");
  pop.className = "modal obspick";
  const chosen = new Set(d.vaults.filter((v) => v.added).map((v) => v.path));
  const draw = () => {
    pop.innerHTML = `<div class="card"><div class="obshead">${OBS_LOGO}<div><h2>${tr("Подключить Obsidian")}</h2><p class="hint">${tr("Mnemai будет видеть заметки хранилища вместе со своей памятью: при каждом вопросе найдёт нужные места и отдаст их ИИ. Заметки только читаются, в них ничего не пишется.")}</p></div></div>
      ${
        d.vaults.length
          ? `<div class="obslist">${d.vaults
              .map(
                (v, k) =>
                  `<button class="obsv ${chosen.has(v.path) ? "on" : ""}" data-k="${k}"><i>${chosen.has(v.path) ? ic("check") : ""}</i><div><b data-noi18n>${esc(v.name)}</b><small data-noi18n>${esc(v.path)}</small></div><span>${v.notes} ${tr("заметок")}${v.open ? " · " + tr("открыто сейчас") : ""}</span></button>`,
              )
              .join("")}</div>`
          : `<p class="hint">${tr("Obsidian на этом компьютере не нашёлся. Укажи папку хранилища вручную.")}</p>`
      }
      <div class="row" style="justify-content:space-between;margin-top:14px">${window.pywebview ? `<button class="btn g" id="obsother">${tr("Другая папка…")}</button>` : "<span></span>"}<div class="row" style="gap:8px"><button class="btn g" data-x>${tr("Отмена")}</button><button class="btn" id="obsok">${tr("Подключить")}</button></div></div></div>`;
    $$("[data-k]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          const p = d.vaults[+b.dataset.k].path;
          chosen.has(p) ? chosen.delete(p) : chosen.add(p);
          draw();
        }),
    );
    $("[data-x]", pop).onclick = () => pop.remove();
    if ($("#obsother", pop))
      $("#obsother", pop).onclick = async () => {
        const p = await window.pywebview.api.pick("folder");
        if (p) {
          d.vaults.push({ path: p, name: p.split(/[\\/]/).pop(), notes: "", open: false });
          chosen.add(p);
          draw();
        }
      };
    $("#obsok", pop).onclick = async () => {
      const known = new Set(d.vaults.map((v) => v.path));
      const keep = extraFolders(prof).filter((x) => !known.has(x));
      await post("/api/agent", { extra_folders: [...keep, ...chosen], team_vault: "" }).catch((e) => toast(e.message));
      pop.remove();
      toast(chosen.size ? tr("Obsidian подключён: заметки читаются в фоне") : tr("Obsidian отключён"));
      viewSettings(SETCUR);
    };
  };
  pop.onclick = (e) => e.target === pop && pop.remove();
  draw();
  document.body.appendChild(pop);
}
// extra memory folders: the list, with a team folder set before 1.4 as the first one
function extraFolders(prof) {
  const out = (prof.extra_folders || []).filter(Boolean);
  if (prof.team_vault && !out.includes(prof.team_vault)) out.unshift(prof.team_vault);
  return out;
}
// what each mode does with three facts heard in a conversation: into memory, waits for the owner, only noticed
function autoScene(mode) {
  const facts = [
    ["Пилот — 3 ноября", "92%"],
    ["Любит зелёный чай", "55%"],
    ["💊 Здоровье", "личное"],
  ];
  const fate = {
    observe: ["fade", "fade", "fade"],
    approve: ["stop", "stop", "stop"],
    mixed: ["go", "stop", "stop"],
    quiet: ["go", "go", "go"],
  }[mode] || ["go", "stop", "stop"];
  const saved = fate.filter((f) => f === "go").length;
  const mid =
    mode === "observe"
      ? `<b class="asmid">${ic("eye")}</b>`
      : fate.includes("stop")
        ? `<b class="asmid q" title="${tr("ждёт тебя")}">?</b>`
        : "";
  return `<div class="autosc m-${mode}"><div class="asn">${ic("chat")}<span>${tr("Разговор")}</span></div>
    <div class="aslane">${mid}${facts.map(([t, p], i) => `<em class="asf ${fate[i]}" style="--i:${i}"><span>${esc(tr(t))}</span><small>${esc(tr(p))}</small></em>`).join("")}</div>
    <div class="asn mem">${ic("mem")}<span>${tr("Память")}</span>${saved ? `<i class="ascnt">+${saved}</i>` : ""}</div></div>`;
}
const BRAIN_HINT = {
  auto: "Сама выбирает лучшее из того, что есть: Claude по подписке, если он стоит на компьютере, иначе встроенную модель.",
  none: "Понимает только явное: «запомни», поправки, решения.",
  local: "Встроенная модель на компьютере понимает обычную речь. Ничего не уходит наружу.",
  claude_code: "Понимает обычную речь. Тексты уходят в Claude по твоей подписке.",
  api: "Ключ и модель задаются в продвинутых настройках.",
  ollama: "Нужна запущенная Ollama, модель выбирается в продвинутых настройках. Ничего не уходит с компьютера.",
};
const BRAINS = {
  auto: "сама",
  none: "только явное",
  local: "встроенная",
  claude_code: "Claude по подписке",
  api: "свой ключ",
  ollama: "Ollama",
};
let SETTINGS_FOCUS = "",
  PRM_ST = { prompts: [], mode: "second", auto: true };
function parseProxy(u) {
  u = String(u || "").trim();
  if (!u) return { mode: "system" };
  if (/^(off|нет|none|direct)$/i.test(u)) return { mode: "off" };
  if (!/:\/\//.test(u)) u = "http://" + u;
  try {
    const x = new URL(u.replace(/^socks5?h?:/i, "http:"));
    return {
      mode: /^socks/i.test(u) ? "socks5" : "http",
      host: x.hostname,
      port: x.port,
      user: decodeURIComponent(x.username || ""),
    };
  } catch (e) {
    return { mode: "http", host: u };
  }
}
function proxyForm(cur, pwSet, sys) {
  const p = parseProxy(cur),
    m = p.mode;
  return `<div class="pxf">${vpnButtons()}<div class="pxmanual" ${m === "http" || m === "socks5" ? "" : "hidden"}><div class="seg pxmode">${[
    ["system", "Как в Windows"],
    ["off", "Напрямую"],
    ["http", "HTTP"],
    ["socks5", "SOCKS5"],
  ]
    .map(([k, l]) => `<button data-pm="${k}" class="${m === k ? "on" : ""}">${l}</button>`)
    .join("")}</div>
   <div class="hint pxsys" ${m === "system" ? "" : "hidden"}>${sys ? `Windows сейчас использует <b>${esc(sys)}</b> — его и возьму.` : "В Windows прокси не задан — пойду напрямую."}</div>
   <div class="pxfields" ${m === "http" || m === "socks5" ? "" : "hidden"}><div class="pxrow"><div class="fld"><span>Адрес</span><input data-px="host" value="${esc(p.host || "")}" placeholder="127.0.0.1"></div><div class="fld"><span>Порт</span><input data-px="port" value="${esc(p.port || "")}" placeholder="${m === "socks5" ? "1080" : "8080"}"></div></div>
   <div class="pxrow"><div class="fld"><span>Логин, если нужен</span><input data-px="user" value="${esc(p.user || "")}" autocomplete="off"></div><div class="fld"><span>Пароль</span><input data-px="pw" type="password" placeholder="${pwSet ? "сохранён" : ""}" autocomplete="new-password"></div></div></div>
   <div class="row" style="margin-top:10px"><button class="btn l" data-pxa="check">Проверить</button><button class="btn" data-pxa="save">Сохранить</button><span class="hint pxres"></span></div></div></div>`;
}
function bindProxyForm(box, onSave) {
  let mode = $(".pxmode .on", box).dataset.pm;
  const url = () => {
    if (mode === "system") return "";
    if (mode === "off") return "off";
    const v = (k) => $(`[data-px="${k}"]`, box).value.trim();
    if (!v("host")) return null;
    return `${mode}://${v("user") ? encodeURIComponent(v("user")) + "@" : ""}${v("host")}${v("port") ? ":" + v("port") : ""}`;
  };
  const pw = () => {
    const v = $('[data-px="pw"]', box).value;
    return v ? v : null;
  };
  $$("[data-pm]", box).forEach(
    (b) =>
      (b.onclick = () => {
        mode = b.dataset.pm;
        $$("[data-pm]", box).forEach((x) => x.classList.toggle("on", x === b));
        $(".pxsys", box).hidden = mode !== "system";
        $(".pxfields", box).hidden = !(mode === "http" || mode === "socks5");
        $(".pxres", box).textContent = "";
      }),
  );
  $('[data-pxa="check"]', box).onclick = async () => {
    const u = url();
    if (u === null) {
      toast("Укажи адрес прокси");
      return;
    }
    const r = $(".pxres", box);
    r.textContent = "проверяю…";
    r.style.color = "";
    try {
      const x = await post("/api/net/check", { proxy: u, ...(pw() !== null ? { password: pw() } : {}) });
      r.textContent = x.ok ? `работает · ${x.via} · ${x.ms} мс` : `не работает: ${x.error}`;
      r.style.color = x.ok ? "var(--ok)" : "var(--bad)";
    } catch (e) {
      r.textContent = e.message;
    }
  };
  $('[data-pxa="save"]', box).onclick = async () => {
    const u = url();
    if (u === null) {
      toast("Укажи адрес прокси");
      return;
    }
    await onSave(u, pw());
  };
  bindVpnButtons(
    box,
    async (u, name) => {
      await onSave(u, null, true);
      toast(u ? tr("VPN подключён") + ": " + name : name + " " + tr("работает на всю систему"));
    },
    () => {
      const mm = $(".pxmanual", box);
      mm.hidden = !mm.hidden;
    },
  );
  if (0)
    $('[data-pxa="find"]', box).onclick = async (e) => {
      const b = e.currentTarget,
        r = $(".vpnr", box);
      b.disabled = true;
      r.innerHTML = `<div class="hint" style="margin:8px 0">${tr("Ищу VPN на этом компьютере…")}</div>`;
      let d;
      try {
        d = await api("/api/net/detect");
      } catch (err) {
        d = { proxies: [], tunnels: [] };
      }
      b.disabled = false;
      r.innerHTML =
        [
          ...(d.tunnels || []).map(
            (t) =>
              `<div class="vrow sys"><i></i><div><b>${esc(t)}</b> <span class="hint">${tr("запущен. Если он подключён, Mnemai пойдёт через него сама — поля можно не заполнять")}</span></div></div>`,
          ),
          ...(d.proxies || []).map(
            (p) =>
              `<div class="vrow ok"><i></i><div><b>${esc(p.name)}</b> <span class="hint">${esc(p.url.replace("://", " · "))} · ${p.ms} ${tr("мс")}</span></div><button class="btn sm" data-vu="${esc(p.url)}">${tr("Использовать")}</button></div>`,
          ),
        ].join("") ||
        `<div class="vrow"><div class="hint">${tr("Ничего не нашла. Включи VPN-программу и нажми ещё раз. Если он в Windows на всю систему (OpenVPN, WireGuard), поля можно оставить пустыми.")}</div></div>`;
      $$("[data-vu]", r).forEach(
        (x) =>
          (x.onclick = async () => {
            await onSave(x.dataset.vu, null);
            toast(tr("VPN подключён: все запросы к ИИ идут через него"));
          }),
      );
    };
}
async function viewSettings(arg) {
  arg = String(arg || "");
  arg = { adv: "style", simple: "ai", net: "app/netcard" }[arg] || arg;
  let [sec, card] = arg.split("/");
  if (!SETSECS.some((x) => x[0] === sec)) sec = "ai"; // settings always open at the first section
  const page = $(".page"),
    keep = !card && page && $("#st") && sec === SETCUR ? page.scrollTop : 0;
  const adv = true;
  const [ag, ms, ls, br, pst, eng, scr, efs, cry] = await Promise.all([
    api("/api/agent"),
    api("/api/models"),
    api("/api/learn/status"),
    api("/api/learn/brain"),
    api("/api/prompts").catch(() => ({ prompts: [], mode: "second", auto: true })),
    api("/api/engine").catch(() => null),
    api("/api/scribe/settings").catch(() => null),
    api("/api/efs").catch(() => null),
    api("/api/crypto").catch(() => null),
  ]);
  PRM_ST = pst;
  const prof = ag.profile,
    simple = prof.simple,
    s = ls.settings;
  // many or long choices: an even grid instead of a row that breaks with one lone choice on the second line
  const segGrid = (choices) => {
    const ls = Object.values(choices).map((l) => tr(String(l)));
    if (ls.length > 4) return "many";
    return ls.length === 4 && ls.join("").length > 60 ? "many two" : "";
  };
  const seg = (key, choices, val) =>
    `<div class="seg ${segGrid(choices)}" data-seg="${key}">${Object.entries(choices)
      .map(([k, l]) => `<button data-v="${k}" class="${k === val ? "on" : ""}">${esc(l)}</button>`)
      .join("")}</div>`;
  const allModels = ms.providers
    .filter((p) => p.ready)
    .flatMap((p) =>
      p.models.map((m) => ({ v: p.id + ":" + m.id, l: (p.id === "claude_code" ? "" : p.name + " · ") + m.name })),
    );
  const groups = {};
  Object.entries(ls.sources).forEach(([k, m]) => {
    (groups[m.group] = groups[m.group] || []).push([k, m]);
  });
  if (!$("#st"))
    $("#view").innerHTML = `<div class="page"><div class="wrap setwrap">${APP.demo ? demoBar() : ""}<h1>Настройки</h1>
  <div class="setlay"><nav class="setnav">${SETSECS.map(([k, i, l]) => `<button data-sec="${k}">${ic(i)}<span>${tr(l)}</span></button>`).join("")}<div class="setfoot"><div id="vaultsw"></div><button class="setreset" id="setreset">${ic("redo")}<span>${tr("Настройки по умолчанию")}</span></button></div></nav><div id="st"></div></div></div></div>`;
  $$(".setnav [data-sec]").forEach((b) => (b.onclick = () => showSec(b.dataset.sec)));
  $("#setreset").onclick = settingsReset;
  drawVaults();
  bindDemo();
  const save = async (patch, msg) => {
    try {
      await post("/api/agent", patch);
      if (msg) toast(msg);
    } catch (e) {
      toast(e.message);
    }
  };
  const saveL = async (patch, msg) => {
    try {
      await post("/api/learn/settings", patch);
      if (msg) toast(msg);
    } catch (e) {
      toast(e.message);
    }
  };
  const again = () => viewSettings(SETCUR);
  {
    $("#st").innerHTML = `
    ${modelHero(ms, allModels, prof.default_model || ms.default_model)}
    <div class="card" data-sec="ai" id="c-prov"><h2>${tr("Модели")}<span class="hint">${tr("с какими ИИ говорить в Mnemai")}</span></h2><div class="aigrp aipaid">${tr("Платные")}<span class="hint">${tr("работают через интернет: платишь компании, чей это ИИ")}</span></div><div class="aisub">${tr("По подписке")}<span class="hint">${tr("та, что уже оплачена у компании")}</span></div><div class="aigrid">${ms.providers
      .filter((x) => isSubscription(x))
      .map((x, n) => provTile(x, n))
      .join(
        "",
      )}</div><div class="aisub">${tr("По ключу API")}<span class="hint">${tr("оплата по расходу, отдельно от подписки")}</span></div><div class="aigrid">${ms.providers
      .filter((x) => !["local", "ollama", "strata"].includes(x.id) && !isSubscription(x))
      .sort((a, b) => tr(a.name).localeCompare(tr(b.name)))
      .map((x, n) => provTile(x, n + 1))
      .join(
        "",
      )}</div><div class="aigrp">${tr("Бесплатные")}<span class="hint">${tr("на этом компьютере, без интернета, ничего не уходит наружу")}</span></div><div class="aigrid">${ms.providers
      .filter((x) => ["local", "ollama", "strata"].includes(x.id))
      .map((x, n) => provTile(x, n))
      .join("")}</div></div>
    ${engineCard(eng)}
    ${((SCR_X = { ...SCR_X, models: allModels, summary: prof.scribe_summary_model || "", keep: !!prof.scribe_keep_audio }), (bindScribeCard.last = scr), scribeCard(scr))}
    <div class="card" data-sec="security" id="seccard"><h2>${tr("Защита данных")}</h2>
     <div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${prof.redact !== false ? "on" : ""}" id="secred"></button><div><b>${tr("Скрывать секреты от облачных ИИ")}</b><p>${tr("Номера карт, пароли, ключи, телефоны, паспорта и СНИЛС заменяются метками до отправки, в ответ настоящие значения подставляются на компьютере.")}</p></div></div>
     ${efs ? `<div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${efs.on ? "on" : ""}" id="secefs" ${efs.supported ? "" : "disabled"}></button><div><b>${tr("Шифровать папку памяти")}</b><p>${efs.supported ? tr("Средствами Windows: файлы на диске зашифрованы ключом твоей учётной записи, без входа в неё их не прочитать, даже вынув диск. Для тебя и Mnemai всё работает как раньше.") : esc(tr(efs.reason))}</p>${efs.on ? `<button class="btn g sm" id="secbk" style="margin-top:6px">${tr("Сохранить ключ восстановления")}</button>` : ""}</div></div>` : ""}
     ${cry ? `<div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${cry.on ? "on" : ""}" id="seccry"></button><div><b>${tr("Шифровать память паролем")}</b><p>${tr("Mnemai сама шифрует заметки, разговоры и журнал, на любой системе. Без пароля их не прочитать, даже скопировав папку. Obsidian и другие редакторы эти файлы не откроют. Забудешь пароль — память не вернуть.")}</p>${cry.on ? `<p class="hint">${tr("Зашифровано файлов")}: ${cry.files}</p><div class="tg" style="padding:6px 0 0;border:0"><button class="sw sm ${cry.remembered ? "on" : ""}" id="seccrem"></button><div><b>${tr("Помнить пароль на этом компьютере")}</b><p>${tr("Mnemai открывается без вопроса, ключ хранится в защищённом хранилище системы. Выключи, чтобы пароль спрашивался при каждом запуске.")}</p></div></div><button class="btn g sm" id="seccpw" style="margin-top:6px">${tr("Сменить пароль")}</button>` : ""}</div></div>` : ""}
     <div class="row"><button class="btn l" id="secout">${ic("eye")}${tr("Что ушло наружу")}</button><button class="btn g" id="secacc">${ic("lock")}${tr("Кто из ИИ что видит")}</button></div></div>
    ${themeCard()}
    ${compCard()}
    ${youCard(prof, ag)}
    <div class="card" data-sec="learn" id="c-mem"><div class="tg" style="padding:0;border:0"><button class="sw ${MEM.on ? "on" : ""}" id="memsw2"></button><div><b>${tr("Память")}</b><p>${tr(MEM.on ? "Включена: ИИ знают, кто ты и над чем работаешь, Mnemai учится по ходу разговора. Claude Code, Claude Desktop и Cursor получают ту же память." : "Выключена: обычный чат. ИИ ничего о тебе не знают, Mnemai ничего не запоминает, Claude Code, Claude Desktop и Cursor память не получают. Всё остальное работает.")}</p></div></div></div>
    <div class="card ${MEM.on ? "" : "dimmed"}" data-sec="learn" id="c-learn">${MEM.on ? "" : memOffNote("обучение не идёт")}<div class="set"><b>Насколько сама учится${hq("learn")}</b><div>${seg("autonomy", ag.simple.autonomy.choices, simple.autonomy)}${autoScene(simple.autonomy)}<div class="hint" style="margin-top:6px">${esc(AUTO_HINT[simple.autonomy])}</div></div></div>
    <div class="set"><b>${tr("Вопросы от себя")}</b><div class="tg" style="padding:0;border:0"><button class="sw ${prof.self_ask !== false ? "on" : ""}" id="selfasksw"></button><div><b>${tr("Иногда спрашивать о проекте")}</b><p>${tr("Когда разговор про проект — один вопрос карточкой: устаревший статус или нет цели. Не чаще раза в 40–120 минут.")}</p></div></div></div>
    <div class="set"><b>${tr("Что Mnemai можно смотреть")}${hq("outside")}</b><div class="tg" style="padding:0;border:0"><button class="sw ${s.outside !== false ? "on" : ""}" id="outsw"></button><div><b>${tr("Другие программы и браузер")}</b><p>${s.outside === false ? tr("Выключено: учусь только на разговорах в Mnemai. Чаты Claude Code, заметки, документы, Telegram и историю браузера не читаю.") : tr("Можно: читаю только то, что включено ниже. Всё читается на компьютере.")}</p></div></div></div>
    <div class="set srcset"><b>Где учиться<span class="hint">${tr("Нажми на карточку, чтобы включить или выключить")}</span></b><div class="srcgrid ${s.outside === false ? "outoff" : ""}">${Object.entries(
      groups,
    )
      .flatMap(([g, list]) => list.map((x) => [g, ...x]))
      .map(([g, k, m], n) => {
        const on = s.sources[k].enabled,
          v = SRC_LOOK[k] || ["📘", "#6d5ff5", "#4fb6ff", "Читает новое"];
        const o = s.sources[k].options || {},
          where = o.path ? String(o.path) : "",
          needs = !on && ["mail", "calendar"].includes(k);
        const lock = s.outside === false && !["mnema_chat", "corrections"].includes(k);
        return `<div class="srct ${on && !lock ? "on" : ""} ${lock ? "locked" : ""}" data-tile="${k}" style="--c1:${v[1]};--c2:${v[2]};--d:${n * 0.06}s">
        <span class="srctag">${esc(g)}</span><button class="sw ${on ? "on" : ""}" data-src="${k}" title="${on ? "Выключить" : "Включить"}"></button>
        <div class="medal2"><span>${v[0]}</span><i class="spark"></i><i class="spark"></i><i class="spark"></i></div>
        <b>${esc(m.name)}</b>${m.note ? `<p>${esc(m.note)}</p>` : ""}
        <div class="srcst">${lock ? `${ic("lock")}${tr("Закрыто: другие программы не смотрю")}` : on ? `<i></i>${tr(v[3])}` : needs ? tr(k === "mail" ? "нужны почта и пароль" : "нужна ссылка или файл") : tr("Не читает")}</div>
        ${on && where ? `<div class="srcwhere" title="${esc(where)}" data-noi18n>${esc(where)}</div>` : ""}
        ${srcOpts(k, o) && !lock ? `<button class="srcset2" data-sopt="${k}">${ic("set")}${tr(on ? "Настроить" : "Указать и включить")}</button>` : ""}</div>`;
      })
      .join("")}</div></div></div>
    <div class="card" data-sec="ai" id="c-other"><h2>${tr("Память в других ИИ")}<span class="hint">${tr("там будет та же память, по их правам доступа")}</span></h2><div class="aigrid" id="conngrid">${OUT_AI.map(([k, n, note]) => outTile(k, n, note, null)).join("")}</div></div>
    </div>${
      APP.desktop
        ? `<div class="card" data-sec="app" id="c-app"><div class="set"><b>Запуск</b><div class="tg" style="padding:0;border:0"><button class="sw ${APP.autostart ? "on" : ""}" id="autos"></button><div><b>Вместе с Windows</b><p>Учится в фоне, окно не открывает.</p></div></div></div>
    <div class="set"><b>Крестик окна</b><div>${seg("onclose", { ask: "спрашивать", tray: "сворачивать в трей", quit: "закрывать" }, APP.on_close || "ask")}</div></div></div>`
        : ""
    }`;
    $$("#st [data-seg]").forEach((sg) =>
      $$("button", sg).forEach(
        (b) =>
          (b.onclick = async () => {
            const k = sg.dataset.seg,
              v = b.dataset.v;
            if (k === "brain") await saveL({ brain: { kind: v } }, "Сохранено");
            else if (k === "onclose") {
              APP = await post("/api/app/close_pref", { value: v });
              toast("Сохранено");
            } else if (k === "gender") await save({ gender: v }, "Сохранено");
            else await save({ simple: { [k]: v } }, "Сохранено");
            again();
          }),
      ),
    );
    if ($("#oname")) {
      $("#oname").onchange = async (e) => {
        await save({ owner_name: e.target.value.trim() }, "Сохранено");
      };
      $("#oname").oninput = (e) => {
        const pv = $("#ypv");
        if (pv) pv.innerHTML = youPreview({ ...prof, owner_name: e.target.value }, ag);
        const av = $(".yav");
        if (av) av.textContent = (e.target.value.trim() || "?").slice(0, 1).toUpperCase();
      };
    }
    bindEngine();
    bindScribeCard();
    $("#secred").onclick = async (e) => {
      const b = e.currentTarget,
        on = !b.classList.contains("on");
      await save({ redact: on }, on ? "Секреты скрываются" : "Секреты уходят как есть");
      b.classList.toggle("on", on);
      refreshStatus();
    };
    $("#secout").onclick = () => outgoingModal(7);
    if ($("#secefs"))
      $("#secefs").onclick = async (e) => {
        const b = e.currentTarget,
          on = !b.classList.contains("on");
        if (
          on &&
          !(await ask(
            "Включить шифрование?",
            "Ключ шифрования живёт в твоей учётной записи Windows. Если переустановить Windows без сохранённого ключа восстановления, файлы памяти не открыть. После включения сохрани ключ восстановления.",
            "Включить",
            false,
          ))
        )
          return;
        b.disabled = true;
        try {
          const d = await post("/api/efs", { action: on ? "on" : "off" });
          toast(d.on ? tr("Папка памяти зашифрована") : tr("Шифрование выключено"));
          again();
        } catch (err) {
          toast(err.message);
          b.disabled = false;
        }
      };
    if ($("#seccry")) $("#seccry").onclick = () => cryptoModal(cry.on ? "off" : "on", again);
    if ($("#seccpw")) $("#seccpw").onclick = () => cryptoModal("password", again);
    if ($("#seccrem"))
      $("#seccrem").onclick = async (e) => {
        const b = e.currentTarget,
          on = !b.classList.contains("on");
        try {
          await post("/api/crypto", { action: "remember", on });
          b.classList.toggle("on", on);
          toast(on ? tr("Пароль запомнен на этом компьютере") : tr("Пароль будет спрашиваться при запуске"));
        } catch (err) {
          toast(err.message);
        }
      };
    if ($("#secbk"))
      $("#secbk").onclick = async () => {
        const d = await post("/api/efs", { action: "backup" });
        toast(tr("Windows спросит пароль в отдельном окне. Ключ сохранится в") + " " + d.file);
      };
    $("#secacc").onclick = () => goSet("security/c-access");
    const rcomp = () => {
      const c = $("#compcard");
      if (c) {
        c.outerHTML = compCard();
        bindCompCard($("#compcard"), rcomp);
      }
    };
    bindCompCard($("#compcard"), rcomp);
    const rtheme = () => {
      const c = $("#themecard");
      if (c) {
        c.outerHTML = themeCard();
        bindThemeCard(rtheme);
      }
      drawThemeBtn();
    };
    bindThemeCard(rtheme);
    RTHEME = rtheme;
    $$("[data-pr]").forEach(
      (b) =>
        (b.onclick = async () => {
          await save({ preset: b.dataset.pr }, "Характер: " + $("b", b).textContent);
          again();
        }),
    );
    const onDefm = (e) => {
      CHAT.model = e.target.value;
      save({ default_model: e.target.value }, "Модель по умолчанию");
      const h = $("#c-model");
      if (h) {
        h.outerHTML = modelHero(ms, allModels, e.target.value);
        $("#defm").onchange = onDefm;
      }
    };
    if ($("#defm")) $("#defm").onchange = onDefm;
    $$("[data-src]").forEach(
      (b) =>
        (b.onclick = async () => {
          if (b.closest(".locked")) {
            toast(tr("Сначала разреши смотреть другие программы — переключатель выше"));
            return;
          }
          await saveL({ sources: { [b.dataset.src]: { enabled: !s.sources[b.dataset.src].enabled } } });
          again();
        }),
    );
    if ($("#outsw"))
      $("#outsw").onclick = async () => {
        await saveL(
          { outside: s.outside === false, found_asked: true },
          s.outside === false ? tr("Можно смотреть то, что включено") : tr("Только разговоры в Mnemai"),
        );
        again();
      };
    $$("[data-tile]").forEach(
      (t) =>
        (t.onclick = (e) => {
          if (e.target.closest("input,select,textarea,button,label,a,.srcopts,.fld,.row")) return;
          const b = $("[data-src]", t);
          if (b) b.click();
        }),
    );
    $$("[data-sopt]").forEach(
      (b) =>
        (b.onclick = (e) => {
          e.stopPropagation();
          const k = b.dataset.sopt,
            src = s.sources[k],
            meta = (ls.sources || {})[k] || { name: k };
          const pop = document.createElement("div");
          pop.className = "modal srcm";
          document.body.appendChild(pop);
          pop.onclick = (ev) => {
            if (ev.target === pop) pop.remove();
          };
          pop.innerHTML = `<div class="card"><div class="cmhead"><div class="medal2 on" style="--c1:${(SRC_LOOK[k] || [])[1] || "#6d5ff5"};--c2:${(SRC_LOOK[k] || [])[2] || "#4fb6ff"};margin:0;width:44px;height:44px;font-size:22px;filter:none;opacity:1;background:linear-gradient(135deg,var(--c1),var(--c2))"><span>${(SRC_LOOK[k] || ["📘"])[0]}</span></div><div><h2>${esc(meta.name)}</h2><p>${esc(meta.note || "")}</p></div><button class="lmx" data-x>×</button></div>
        <div class="srcopts">${srcOpts(k, src.options)}</div><div class="row" style="justify-content:flex-end;margin-top:14px;gap:8px"><button class="btn g" data-x>${tr("Отмена")}</button><button class="btn" data-ok>${tr(src.enabled ? "Сохранить" : "Сохранить и включить")}</button></div></div>`;
          $$("[data-x]", pop).forEach((x) => (x.onclick = () => pop.remove()));
          $$("[data-pick]", pop).forEach(
            (x) =>
              (x.onclick = async () => {
                const pth = await window.pywebview.api.pick(x.dataset.kind || "folder");
                if (pth) x.parentElement.querySelector("input").value = pth;
              }),
          );
          $("[data-ok]", pop).onclick = async () => {
            const opts = {};
            $$("[data-opt]", pop).forEach((i) => (opts[i.dataset.opt] = i.type === "checkbox" ? i.checked : i.value));
            pop.remove();
            await saveL({ sources: { [k]: { enabled: true, options: opts } } }, tr("Сохранено"));
            again();
          };
        }),
    );
    $$("[data-opt]").forEach(
      (i) =>
        (i.onchange = () =>
          saveL(
            {
              sources: { [i.dataset.s]: { options: { [i.dataset.opt]: i.type === "checkbox" ? i.checked : i.value } } },
            },
            "Сохранено",
          )),
    );
    $$("[data-pick]").forEach(
      (b) =>
        (b.onclick = async () => {
          const p = await window.pywebview.api.pick(b.dataset.kind || "folder");
          if (p) {
            const i = b.parentElement.querySelector("input");
            i.value = p;
            i.onchange();
          }
        }),
    );
    if ($("#autos"))
      $("#autos").onclick = async () => {
        APP = await post("/api/app/autostart", { on: !APP.autostart });
        again();
      };
    bindTiles();
    bindProv();
  }
  {
    const clients = await api("/api/clients");
    $("#st").insertAdjacentHTML(
      "beforeend",
      `
    <div class="card" data-sec="style" id="c-packs"><h2>Наборы <span class="hint">поделиться настройками без личных данных</span></h2><div class="row"><button class="btn l" id="exp">Скачать мой набор</button><label class="btn l" style="cursor:pointer">Загрузить набор<input type="file" id="imp" accept=".json" hidden></label></div></div>
    ${ag.catalog.map((sec, si) => `<div class="card adv-sec" data-sec="style" ${si ? "" : 'id="c-rules"'}><details><summary><h2>${esc(sec.title)} <span class="cnt">${sec.items.filter((i) => i.on).length} из ${sec.items.length}</span></h2></summary>${sec.items.map((i) => `<div class="tg"><button class="sw ${i.on ? "on" : ""}" data-tog="${i.id}" data-on="${i.on ? 1 : 0}"></button><div><b>${esc(i.title)}</b><p>${esc(i.rule)}</p></div></div>`).join("")}</details></div>`).join("")}
    <div class="card" data-sec="learn" id="c-sources"><h2>Обучение по источникам${hq("learn")}</h2>${
      Object.entries(ls.sources)
        .filter(([k]) => s.sources[k].enabled)
        .map(
          ([k, m]) =>
            `<div class="set"><b>${esc(m.name)}</b><div>${seg("mode:" + k, ag.simple.autonomy.choices, s.sources[k].mode)}</div></div>`,
        )
        .join("") || '<p class="hint">Источники выключены.</p>'
    }
      <div class="numgrid">
        <label class="numt" style="--c1:#6366f1;--c2:#a855f7"><span class="medal2 lit"><span>🎯</span></span><span class="xftx"><b>${tr("Записывать без вопроса")}</b><small>${tr("когда уверена не меньше чем на")}</small></span><span class="numin"><input id="auto" type="number" min="50" max="100" value="${Math.round(s.auto_confidence * 100)}"><em>%</em></span></label>
        <label class="numt" style="--c1:#f59e0b;--c2:#f97316"><span class="medal2 lit"><span>🧹</span></span><span class="xftx"><b>${tr("Предлагать забыть")}</b><small>${tr("то, что не пригодилось, через")}</small></span><span class="numin"><input id="fdays" type="number" min="7" value="${s.forget_after_days}"><em>${tr("дн.")}</em></span></label>
        <div class="numt wide" style="--c1:#ef4444;--c2:#f97316"><span class="medal2 ${s.never.length ? "lit" : ""}"><span>🚫</span></span><span class="xftx"><b>${tr("Не учиться на темах и словах")}</b><span class="lchips">${s.never.map((p, i) => `<label class="on">${esc(p)} <b data-nv="${i}">×</b></label>`).join("") || `<small>${tr("пусто — учится на всём")}</small>`}</span><span class="row xfadd"><input id="nva" class="inp" placeholder="${tr("тема или слово")}"><button class="btn g" id="nvb">${tr("Добавить")}</button></span></span></div>
      </div>
      <div class="set"><b>Чем понимает тексты${hq("brain")}</b><div>${seg("brain", BRAINS, s.brain.kind)}<div class="hint" style="margin-top:6px">${esc(BRAIN_HINT[s.brain.kind])}${s.brain.kind === "auto" && br.using ? ` <b>${tr("Сейчас")}: ${esc(tr({ claude_code: "Claude по подписке", local: "встроенная модель", none: "только явное" }[br.using] || br.using))}</b>` : ""}</div>${br.level === "bad" ? `<div class="brain bad" style="margin-top:8px">${esc(br.message)}</div>` : ""}
        ${s.brain.kind === "api" ? `<div class="fld"><span>Провайдер</span><select id="bprov"><option value="anthropic" ${s.brain.provider === "anthropic" ? "selected" : ""}>Anthropic</option><option value="openai" ${s.brain.provider !== "anthropic" ? "selected" : ""}>Совместимый с OpenAI</option></select></div><div class="fld"><span>Ключ</span><input id="bkey" type="password" value="${esc(s.brain.api_key)}"></div>` : ""}
        ${!["none", "auto"].includes(s.brain.kind) ? `<div class="fld"><span>Модель</span><input id="bmodel" value="${esc(s.brain.model)}" placeholder="${s.brain.kind === "claude_code" ? "по умолчанию" : s.brain.kind === "ollama" ? "например, qwen2.5:14b" : "название модели"}"></div>` : ""}${s.brain.kind === "ollama" || s.brain.kind === "api" ? `<div class="fld"><span>Адрес, если не стандартный</span><input id="bend" value="${esc(s.brain.endpoint)}"></div>` : ""}
        <div class="row" style="margin-top:8px"><button class="btn l" id="btest">Проверить</button><span class="hint" id="bres"></span></div></div></div>
      <div class="row" style="margin-top:10px"><button class="btn" id="lsave">Сохранить</button><button class="btn l" id="lnow">Учиться сейчас</button><button class="btn g" id="lpause">${s.paused ? "Продолжить обучение" : "Пауза обучения"}</button></div></div>
    <div class="card ${MEM.on ? "" : "dimmed"}" data-sec="security" id="c-access">${MEM.on ? "" : memOffNote("ИИ сейчас ничего не получают")}<h2>Кто из ИИ что видит${hq("access")}<span class="accsaved" id="accsaved">${ic("check")}${tr("Сохранено")}</span></h2>
      <p class="hint" style="margin:-4px 0 12px">${tr("Галочка — эта часть памяти уходит этому ИИ вместе с вопросом. Замок — тема вырезается даже из разрешённых частей. Меняется сразу.")}</p>
      <div class="accwrap" id="accm">${accMatrix(clients)}</div></div>
    <div class="card" data-sec="style" id="promptcard"><h2>${tr("Повторяющиеся задачи")}${hq("prompts")}</h2><p class="hint" style="margin:-4px 0 10px">${tr("Делаешь что-то не в первый раз — отчёт по встрече, пост по заметкам, письмо клиенту? Mnemai запишет рецепт: как именно ты это делаешь. Дальше просишь коротко — и она делает так же, без уточнений.")}</p>
      <div class="set"><b>${tr("Предлагать записать рецепт")}</b><div>${seg("pmode", { off: "никогда", second: "когда задача повторилась", every: "на каждую задачу" }, PRM_ST.mode)}</div></div>
      <div class="tg" style="padding:12px 0"><button class="sw ${PRM_ST.auto ? "on" : ""}" id="pauto"></button><div><b>${tr("Узнавать задачу и готовить по рецепту")}</b><p>${tr("Попросил знакомое — Mnemai сама берёт рецепт, в ответе пометка «по рецепту». Выключено — рецепты лежат, но сама их не берёт.")}</p></div></div>
      <div class="set"><b>${tr("Мои рецепты")}</b><div>${PRM_ST.prompts.length ? `<div class="plist">${PRM_ST.prompts.map((x) => `<div class="pi"><div><b>${esc(x.name)}</b><span>${esc(x.when || "")} · использован ${x.uses} раз</span></div><button class="btn g sm" data-popen="${esc(x.file)}">Открыть</button><button class="btn g sm" data-pdel="${esc(x.file)}">Удалить</button></div>`).join("")}</div>` : '<span class="hint">пока нет — Mnemai предложит первый, когда задача повторится</span>'}</div></div></div>
    <div class="card" data-sec="app" id="netcard"><h2>${tr("VPN и прокси")}</h2>
      <p class="hint" style="margin:-4px 0 12px">${tr("Когда ИИ недоступны напрямую. По ключу Mnemai подключается сама, держать приложение VPN открытым не нужно. Через VPN идут только запросы Mnemai, остальной компьютер работает как раньше.")}</p>
      <div class="vksvcs">${VK_SVCS.map((x, n) => {
        const [mk, c1, c2] = VK_LOOK[x] || ["•", "#64748b", "#94a3b8"];
        return `<button class="vksv ${x === (prof.vpn_service || "Hiddify") ? "on" : ""}" data-vks="${esc(x)}" style="--c1:${c1};--c2:${c2};--d:${n * 0.04}s"><span class="medal2"><span>${mk}</span></span><b ${x === "Другой сервис" ? "" : "data-noi18n"}>${esc(tr(x))}</b></button>`;
      }).join("")}</div>
      <div class="vkrow"><select class="inp" id="vksvc" hidden>${VK_SVCS.map((x) => `<option value="${esc(x)}" ${x === (prof.vpn_service || "Hiddify") ? "selected" : ""}>${esc(tr(x))}</option>`).join("")}</select>
        <button class="btn" id="vkimp">${ic("copy")}${tr("Импортировать ключ")}</button><button class="btn g" id="vkman">${ic("edit")}${tr("Ввести ключ вручную")}</button></div>
      <div class="hint vkhint" id="vkhint"></div>
      <div class="vkbox" id="vkbox" hidden><textarea class="inp" id="vkkey" rows="3" placeholder="vless://…  vmess://…  trojan://…  ss://…  ${tr("или ссылка подписки")} https://…"></textarea><div class="row" style="margin-top:8px;gap:8px"><button class="btn" id="vkgo">${tr("Подключиться")}</button><span class="hint" id="vkmsg"></span></div></div>
      <div class="vkstat" id="vkstat"></div>
      <details class="vkold"><summary>${tr("Или через уже запущенный VPN (Hiddify, Happ…) или свой прокси")}</summary>${proxyForm(prof.vpn_key_on ? "" : prof.proxy || "", ag.proxy_password_set, ag.proxy_system)}</details>
      <div class="hint" style="margin-top:10px">${tr("Сейчас запросы идут")}: <b>${esc(ag.proxy_used || tr("напрямую"))}</b></div></div>
    <div class="card" data-sec="app" id="c-acts"><h2>${tr("Действия на компьютере")}</h2>
      <div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${prof.tools !== false ? "on" : ""}" id="actsw"></button><div><b>${tr("Модель может читать и создавать файлы")}</b><p>${tr("Читать, искать, создавать и править файлы, делать PDF, Word и Excel, записывать в память. В интернет ничего не уходит. Любую запись можно откатить: «Память» → «История».")}</p></div></div>
      <div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${prof.pc_access !== false ? "on" : ""}" id="pcsw"></button><div><b>${tr("Терминал и управление компьютером")}</b><p>${tr("Модель может выполнять команды в терминале этого компьютера: смотреть процессы, железо и сеть, запускать программы, работать с git и файлами вне рабочих папок. Каждая команда — с таймаутом, в журнале «Память» → «История». Выключи, если доступ к системе не нужен.")}</p></div></div>
      <div class="tg" style="padding:0 0 10px;border:0"><button class="sw ${prof.tools_ask ? "on" : ""}" id="actask-sw"></button><div><b>${tr("Спрашивать разрешение на каждое действие")}</b><p>${tr("Выключено: Mnemai делает сразу. Каждая запись всё равно в журнале и откатывается в «Память» → «История».")}</p></div></div>
      <div class="set"><b>${tr("Где можно")}</b><div><div class="actfolders"><div class="actf"><span>${tr("Папка памяти")}</span><code data-noi18n>${esc(ACH.folder || "")}</code></div>${(prof.tool_folders || []).map((f, k) => `<div class="actf"><span>${tr("Рабочая папка")}</span><code data-noi18n>${esc(f)}</code><button class="btn g sm" data-actdel="${k}">${tr("Убрать")}</button></div>`).join("")}</div>
      <div class="row" style="margin-top:8px"><input id="actnew" class="inp" style="min-width:320px" placeholder="${tr("папка, где можно работать")}">${window.pywebview ? `<button class="btn l" id="actpick">${tr("Выбрать…")}</button>` : ""}<button class="btn g" id="actadd">${tr("Добавить")}</button></div></div></div></div>
    <div class="card" data-sec="app" id="c-team"><h2>${tr("Дополнительные папки памяти")}${hq("team")}</h2>
      <div class="xfgrid"><button class="xft" id="obsconnect" style="--c1:#7c3aed;--c2:#a855f7"><span class="medal2 lit">${OBS_LOGO}</span><span class="xftx"><b>Obsidian</b><small>${tr("Хранилища Obsidian на этом компьютере")}</small><span class="srcst">${ic("plus")}${tr("Подключить Obsidian")}</span></span></button>
      <div class="xft" style="--c1:#0ea5e9;--c2:#22d3ee"><span class="medal2 lit"><span>📁</span></span><span class="xftx"><b>${tr("Своя папка")}</b><small>${tr("Любая папка с заметками или документами")}</small>
      <span class="row xfadd"><input id="team" class="inp" placeholder="${tr("папка с заметками или другой памятью")}">${window.pywebview ? `<button class="btn g" id="tpick">${tr("Выбрать…")}</button>` : ""}<button class="btn g" id="tsave">${tr("Добавить")}</button></span></span></div></div>
      <div class="actfolders" id="xfolders">${extraFolders(prof)
        .map(
          (f, k) =>
            `<div class="actf"><span>${tr("Папка")}</span><code data-noi18n>${esc(f)}</code><button class="btn g sm" data-xdel="${k}">${tr("Убрать")}</button></div>`,
        )
        .join("")}</div></div>
    <div class="card tgc" data-sec="learn" id="c-tg"><h2>Telegram</h2><p class="hint">${tr("загружаю…")}</p></div>
`,
    );
    $("#exp").onclick = async () => {
      const p = await api("/api/agent/pack");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(p, null, 2)], { type: "application/json" }));
      a.download = "mnema-набор.json";
      a.click();
    };
    $("#imp").onchange = async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      try {
        await post("/api/agent/pack", JSON.parse(await f.text()));
        toast("Набор загружен");
        again();
      } catch (err) {
        toast(err.message);
      }
    };
    $$("[data-tog]").forEach(
      (b) =>
        (b.onclick = async () => {
          const on = b.dataset.on !== "1";
          await save({ toggles: { [b.dataset.tog]: on } });
          b.dataset.on = on ? 1 : 0;
          b.classList.toggle("on", on);
          const sec = b.closest(".adv-sec");
          $(".cnt", sec).textContent = `${$$(".sw.on", sec).length} из ${$$(".sw", sec).length}`;
        }),
    );
    $$("#st .adv-only [data-seg],#c-sources [data-seg],#promptcard [data-seg]").forEach((sg) =>
      $$("button", sg).forEach(
        (b) =>
          (b.onclick = async () => {
            const k = sg.dataset.seg,
              v = b.dataset.v;
            if (k === "pmode") await save({ prompts_mode: v });
            else if (k === "brain") await saveL({ brain: { kind: v } });
            else if (k.startsWith("mode:")) await saveL({ sources: { [k.slice(5)]: { mode: v } } });
            again();
          }),
      ),
    );
    const collect = () => {
      const p = { auto_confidence: +$("#auto").value / 100, forget_after_days: +$("#fdays").value, brain: {} };
      for (const [id, k] of [
        ["bprov", "provider"],
        ["bkey", "api_key"],
        ["bmodel", "model"],
        ["bend", "endpoint"],
      ])
        if ($("#" + id)) p.brain[k] = $("#" + id).value;
      return p;
    };
    $("#lsave").onclick = async () => {
      await saveL(collect(), "Сохранено");
      again();
    };
    $("#lnow").onclick = async () => {
      await saveL(collect());
      try {
        await post("/api/learn/run", { initial: !s.initial.done });
        toast("Учусь. Что поняла — в ленте справа вверху");
      } catch (e) {
        toast(e.message);
      }
    };
    $("#lpause").onclick = async () => {
      await saveL({ paused: !s.paused }, s.paused ? "Обучение продолжается" : "Обучение на паузе");
      again();
    };
    $("#btest").onclick = async () => {
      $("#bres").textContent = "проверяю…";
      const r = await post("/api/learn/test_brain", collect());
      $("#bres").textContent = r.ok
        ? "Работает: " + r.found.join("; ")
        : "Не работает: " + (r.error || "ничего не нашла");
    };
    $$("[data-nv]").forEach(
      (x) => (x.onclick = () => saveL({ never: s.never.filter((_, i) => i != x.dataset.nv) }).then(again)),
    );
    $("#nvb").onclick = () => {
      const v = $("#nva").value.trim();
      if (v) saveL({ never: [...s.never, v] }, "Добавлено").then(again);
    };
    bindAcc(clients);
    drawTg();
    if ($("#tpick"))
      $("#tpick").onclick = async () => {
        const p = await window.pywebview.api.pick("folder");
        if (p) $("#team").value = p;
      };
    $("#tsave").onclick = async () => {
      const v = $("#team").value.trim();
      if (!v) return toast(tr("Укажи папку"));
      await save(
        { extra_folders: [...extraFolders(prof).filter((x) => x !== v), v], team_vault: "" },
        "Папка добавлена",
      );
      viewSettings(SETCUR);
    };
    $("#obsconnect").onclick = () => obsidianPick(prof);
    api("/api/obsidian") // an Obsidian vault in the list wears its logo
      .then((d) =>
        $$("#xfolders .actf").forEach((row, k) => {
          const f = d.folders[k];
          if (f && f.obsidian) row.querySelector("span").innerHTML = OBS_LOGO + "Obsidian";
        }),
      )
      .catch(() => {});
    $$("[data-xdel]").forEach(
      (b) =>
        (b.onclick = async () => {
          await save(
            { extra_folders: extraFolders(prof).filter((_, k) => k !== +b.dataset.xdel), team_vault: "" },
            "Папка убрана",
          );
          viewSettings(SETCUR);
        }),
    );
    const actFolders = prof.tool_folders || [];
    if ($("#actsw"))
      $("#actsw").onclick = async (e) => {
        const on = !e.currentTarget.classList.contains("on");
        e.currentTarget.classList.toggle("on", on);
        await save({ tools: on }, on ? "Действия с файлами включены" : "Действия с файлами выключены");
      };
    if ($("#memsw2")) $("#memsw2").onclick = () => memSet(!MEM.on);
    if ($("#selfasksw"))
      $("#selfasksw").onclick = async (e) => {
        const on = !e.currentTarget.classList.contains("on");
        e.currentTarget.classList.toggle("on", on);
        await save({ self_ask: on }, on ? "Буду иногда спрашивать о проектах" : "Сама больше не спрашиваю");
      };
    if ($("#actask-sw"))
      $("#actask-sw").onclick = async (e) => {
        const on = !e.currentTarget.classList.contains("on");
        e.currentTarget.classList.toggle("on", on);
        await save({ tools_ask: on }, on ? "Буду спрашивать перед действием" : "Действия — сразу, без вопросов");
      };
    if ($("#pcsw"))
      $("#pcsw").onclick = async (e) => {
        const on = !e.currentTarget.classList.contains("on");
        e.currentTarget.classList.toggle("on", on);
        await save({ pc_access: on }, on ? "Терминал включён" : "Терминал выключен: только файлы");
      };
    if ($("#actpick"))
      $("#actpick").onclick = async () => {
        const p = await window.pywebview.api.pick("folder");
        if (p) $("#actnew").value = p;
      };
    if ($("#actadd"))
      $("#actadd").onclick = async () => {
        const v = $("#actnew").value.trim();
        if (!v) return toast(tr("Укажи папку"));
        await save({ tool_folders: [...actFolders, v] }, "Папка добавлена");
        viewSettings(SETCUR);
      };
    $$("[data-actdel]").forEach(
      (b) =>
        (b.onclick = async () => {
          await save({ tool_folders: actFolders.filter((_, k) => k !== +b.dataset.actdel) }, "Папка убрана");
          viewSettings(SETCUR);
        }),
    );
    if ($("#pauto"))
      $("#pauto").onclick = async (e) => {
        const on = !e.currentTarget.classList.contains("on");
        e.currentTarget.classList.toggle("on", on);
        await save({ prompts_auto: on });
      };
    $$("[data-popen]").forEach((b) => (b.onclick = () => post("/api/prompts/open", { file: b.dataset.popen })));
    $$("[data-pdel]").forEach(
      (b) =>
        (b.onclick = async () => {
          if (
            !(await ask("Удалить повторяющуюся задачу?", "Mnemai забудет рецепт и перестанет делать задачу по нему."))
          )
            return;
          await post("/api/prompts/delete", { file: b.dataset.pdel });
          again();
        }),
    );
    bindVpnKey(prof);
    bindProxyForm($("#netcard"), async (url, pw, quiet) => {
      await save({ proxy: url, ...(pw !== null ? { proxy_password: pw } : {}) }, quiet ? "" : "Прокси сохранён");
      if (!quiet) again();
      else {
        const cur = $("#netcard .hint b:last-of-type");
      }
    });
  }
  decorateToggles($("#st"));
  showSec(sec, card);
  const pg = $(".page");
  if (pg && !card) pg.scrollTop = keep;
}
function srcOpts(k, o) {
  const f = (key, label, ph, kind) =>
    `<div class="fld"><span>${label}</span><div class="row"><input data-s="${k}" data-opt="${key}" value="${esc(o[key] ?? "")}" placeholder="${esc(ph)}" style="flex:1">${kind && window.pywebview ? `<button class="btn g sm" data-pick data-kind="${kind}">Выбрать…</button>` : ""}</div></div>`;
  const M = {
    claude_code: () => f("path", "Папка разговоров", "~/.claude/projects", "folder"),
    notes: () => f("path", "Папка заметок", "например, папка Obsidian", "folder"),
    chatgpt_export: () => f("path", "Файл conversations.json", "выгрузка ChatGPT", "file"),
    telegram: () => f("path", "Папка выгрузки", "Telegram Desktop → Экспорт → JSON", "folder"),
    mail: () =>
      f("host", "Сервер IMAP", "imap.gmail.com") +
      f("user", "Почта", "you@gmail.com") +
      `<div class="fld"><span>Пароль приложения</span><input type="password" data-s="mail" data-opt="password" value="${esc(o.password || "")}"></div>`,
    calendar: () => f("path", "Файл .ics или ссылка iCal", "секретная ссылка iCal из Google Календаря", "file"),
    documents: () => f("path", "Папка документов", "например, Документы", "folder"),
    browser_history: () =>
      `<div class="fld"><span>Браузер</span><select data-s="browser_history" data-opt="browser"><option value="">все найденные</option>${["Chrome", "Edge", "Яндекс Браузер"].map((b) => `<option ${o.browser === b ? "selected" : ""}>${b}</option>`).join("")}</select></div>`,
  };
  return M[k] ? M[k]() : "";
}
// brand look of every AI: glyph and two colours of the medal (the same tile for all, no one is first among equals)
const AI_LOOK = {
  local: ["💻", "#0ea5e9", "#22c55e"],
  claude_code: ["C", "#d97757", "#f4a582"],
  codex: ["C", "#111827", "#64748b"],
  opencode_go: ["G", "#16a34a", "#86efac"],
  anthropic: ["A", "#b45309", "#e0915f"],
  openai: ["◎", "#10a37f", "#4fd1a5"],
  gemini: ["✦", "#4285f4", "#9b8cf5"],
  openrouter: ["R", "#475569", "#94a3b8"],
  deepseek: ["🐋", "#4d6bfe", "#7c93ff"],
  yandex: ["Я", "#fc3f1d", "#ff9a3c"],
  ollama: ["🦙", "#374151", "#9ca3af"],
  strata: ["S", "#0ea5e9", "#6366f1"],
  "claude-code": [">_", "#d97757", "#f4a582"],
  "claude-desktop": ["C", "#c2410c", "#fb923c"],
  cursor: ["⌘", "#1f2937", "#6b7280"],
};
const aiLook = (k, name) => AI_LOOK[k] || [(name || "?").slice(0, 1), "#64748b", "#94a3b8"];
const aiMedal = (k, name, cls = "") => {
  const [g] = aiLook(k, name);
  return `<span class="medal2 aimed ${cls}"><span data-noi18n>${esc(g)}</span><i class="spark"></i><i class="spark"></i><i class="spark"></i></span>`;
};
const OUT_AI = [
  ["claude-code", "Claude Code", "память в каждой сессии через MCP"],
  ["claude-desktop", "Claude Desktop", "память в приложении Claude через MCP"],
  ["cursor", "Cursor", "правила и проекты в редакторе через MCP"],
];
// the AI that answers by default: a hero with its medal, the choice right there
function modelHero(ms, allModels, cur) {
  const pid = String(cur || "").split(":")[0],
    p = ms.providers.find((x) => x.id === pid) || {},
    opt = allModels.find((o) => o.v === cur) || allModels[0] || { l: "" },
    ready = ms.providers.filter((x) => x.ready).length,
    [, c1, c2] = aiLook(pid, p.name);
  return `<div class="card aihero" data-sec="ai" id="c-model" style="--c1:${c1};--c2:${c2}">
    <div class="aihl">${aiMedal(pid, p.name, "on")}<div><small>${tr("Сейчас отвечает")}</small><b>${esc(opt.l.split(" · ").pop() || p.name || "")}</b><span>${esc(p.name || "")}${p.note ? ` · ${esc(p.note)}` : ""}</span></div></div>
    <div class="aihr"><label for="defm">${tr("Модель по умолчанию")}${hq("models")}</label><select class="inp" id="defm">${allModels.map((o) => `<option value="${esc(o.v)}" ${o.v === cur ? "selected" : ""}>${esc(o.l)}</option>`).join("")}</select><small>${tr("Подключено")}: ${ready} ${tr("из")} ${ms.providers.length}. ${tr("В разговоре модель меняется сверху слева.")}</small></div></div>`;
}
const aiStatus = (on, txt, cls = "") => `<span class="aist ${cls}">${on ? "<i></i>" : ""}${txt}</span>`;
// one word for the state of an AI: works, switched off by the owner, set up but not working (and why), not set up
const provState = (p) =>
  p.disabled ? "выключено" : p.problem ? "не работает" : p.ready ? "подключено" : "не подключено";
function provTile(p, n = 0) {
  const on = p.connected && !p.disabled;
  const act = p.disabled
    ? ""
    : p.id === "local"
      ? `<button class="btn g sm" data-lm>${tr(p.ready ? "Другая модель" : "Выбрать и скачать")}</button>`
      : p.id === "claude_code"
        ? p.problem
          ? ""
          : p.ready
            ? `<span class="aiok">${tr("работает без ключа")}</span>`
            : p.found
              ? `<button class="btn sm" data-cclogin>${tr("Войти")}</button><button class="btn g sm" data-chk>${tr("Проверить снова")}</button>`
              : `<button class="btn g sm" data-ccinstall>${tr("Как установить")}</button><button class="btn g sm" data-chk>${tr("Проверить снова")}</button>`
        : p.id === "codex"
          ? p.ready
            ? `<span class="aiok">${tr("подписка ChatGPT")}</span>`
            : p.found
              ? `<button class="btn sm" data-codexlogin>${tr(p.problem ? "Переподключить ChatGPT" : "Продолжить с ChatGPT")}</button><button class="btn g sm" data-chk>${tr("Проверить снова")}</button>`
              : `<button class="btn g sm" data-codexinstall>${tr("Как установить Codex")}</button><button class="btn g sm" data-chk>${tr("Проверить снова")}</button>`
          : `<button class="btn g sm" data-more>${tr(p.needs_key ? (p.connected ? "Сменить ключ" : "Указать ключ") : "Указать адрес")}</button>`;
  const check = p.problem && !p.disabled ? `<button class="btn sm" data-chk>${tr("Проверить снова")}</button>` : "";
  const off = p.connected
    ? `<button class="btn g sm aioff" data-off="${p.disabled ? 0 : 1}" title="${tr(p.disabled ? "Вернуть этот ИИ в списки моделей" : "Убрать этот ИИ из списков моделей — ключ и настройки останутся")}">${tr(p.disabled ? "Включить" : "Выключить")}</button>`
    : "";
  const local =
    p.id === "local" && p.ready
      ? p.models.map((m) => m.name).join(", ")
      : p.id === "claude_code" && !p.ready && !p.problem && !p.disabled
        ? tr(p.found ? "Claude Code найден — войди в свой аккаунт Claude" : "Claude Code не найден на этом компьютере")
        : p.id === "codex" && !p.ready && !p.problem && !p.disabled
          ? tr(p.found ? "Подключи подписку ChatGPT" : "Codex App Server не найден на этом компьютере")
          : "";
  const [, c1, c2] = aiLook(p.id, p.name);
  const cls = p.disabled ? "off" : p.problem ? "bad" : "";
  return `<div class="aitile ${p.ready ? "on" : ""} ${cls}" data-p="${p.id}" ${p.id === "local" ? 'id="c-local"' : ""} style="--c1:${c1};--c2:${c2};--d:${n * 0.05}s">${aiStatus(p.ready, tr(provState(p)), cls)}
    ${aiMedal(p.id, p.name)}<b>${esc(p.name)}</b><small class="${p.problem && on ? "aiprob" : ""}" ${p.problem && on ? `title="${esc(p.problem)}"` : ""}>${esc(p.problem && on ? p.problem.split(/(?<=[.!])\s/)[0] : local || p.note)}</small>
    <div class="aift">${check}${act}${off}</div>
    ${p.id === "local" || p.id === "claude_code" || p.id === "codex" ? "" : `<div class="more" hidden>${p.needs_key ? `<input class="inp" type="password" placeholder="${tr("ключ")}" value="${esc(p.key)}" data-k>` : `<input class="inp" placeholder="http://127.0.0.1:11434" value="${esc(p.endpoint)}" data-e>`}<button class="btn sm" data-pk>${tr("Сохранить и найти модели")}</button><button class="btn g sm" data-less>${tr("Отмена")}</button></div>`}</div>`;
}
function outTile(k, name, note, on, n = 0) {
  const act = `<button class="btn g sm" data-con="${k}">${tr(on ? "Обновить" : "Подключить")}</button>`;
  const [, c1, c2] = aiLook(k, name);
  return `<div class="aitile out ${on ? "on" : ""}" data-out="${k}" style="--c1:${c1};--c2:${c2};--d:${n * 0.05}s">${aiStatus(on, on === null ? "…" : tr(on ? "подключено" : "не подключено"))}
    <span class="aipipe"><span class="aim">M</span><i></i>${aiMedal(k, name)}</span><b>${esc(name)}</b><small>${esc(tr(note))}</small>
    <div class="aift">${act}</div></div>`;
}
function bindTiles(fetch = true) {
  $$(".aitile [data-more]").forEach(
    (b) =>
      (b.onclick = () => {
        const t = b.closest(".aitile"),
          m = $(".more", t);
        m.hidden = !m.hidden;
        t.classList.toggle("editing", !m.hidden);
        if (!m.hidden) $("input", m).focus();
      }),
  );
  $$(".aitile [data-less]").forEach(
    (b) =>
      (b.onclick = () => {
        const t = b.closest(".aitile");
        $(".more", t).hidden = true;
        t.classList.remove("editing");
      }),
  );
  $$(".aitile [data-lm]").forEach((b) => (b.onclick = () => localModal()));
  $$(".aitile [data-off]").forEach(
    (b) =>
      (b.onclick = async () => {
        const id = b.closest(".aitile").dataset.p;
        b.disabled = true;
        await post("/api/providers", { id, disabled: b.dataset.off === "1" });
        await refreshProviders();
        viewSettings(SETCUR);
      }),
  );
  $$(".aitile [data-cclogin]").forEach(
    (b) =>
      (b.onclick = async () => {
        const r = await post("/api/providers/claude_login", {});
        toast(r.ok ? tr("Открылось окно Claude Code: войди в аккаунт, потом нажми «Проверить снова»") : r.error, 9000);
      }),
  );
  $$(".aitile [data-ccinstall]").forEach(
    (b) => (b.onclick = () => post("/api/open_url", { url: "https://code.claude.com/docs/en/setup" }).catch(() => {})),
  );
  $$(".aitile [data-codexlogin]").forEach(
    (b) =>
      (b.onclick = async () => {
        const r = await post("/api/providers/codex_login", {});
        if (r.ok && r.url) await post("/api/open_url", { url: r.url });
        toast(
          r.ok ? tr("Открылся браузер: подтверди вход и разрешение использовать подписку ChatGPT") : r.error,
          10000,
        );
      }),
  );
  $$(".aitile [data-codexinstall]").forEach(
    (b) =>
      (b.onclick = () => post("/api/open_url", { url: "https://developers.openai.com/codex/cli" }).catch(() => {})),
  );
  $$(".aitile [data-chk]").forEach(
    (b) =>
      (b.onclick = async () => {
        const id = b.closest(".aitile").dataset.p;
        b.disabled = true;
        b.textContent = tr("проверяю…");
        const r = await post("/api/providers/check", { id });
        toast(r.ok ? tr("Работает") : r.error);
        await refreshProviders();
        viewSettings(SETCUR);
      }),
  );
  if (fetch)
    api("/api/connect")
      .then((st) => {
        const g = $("#conngrid");
        if (!g) return;
        g.innerHTML = OUT_AI.map(([k, n, note], i) => outTile(k, n, note, !!st[k], i)).join("");
        bindTiles(false);
      })
      .catch(() => {});
  bindCon();
  bindProv();
}
function bindCon() {
  $$("[data-con]").forEach(
    (b) =>
      (b.onclick = async () => {
        b.disabled = true;
        const r = await post("/api/connect", { target: b.dataset.con });
        b.disabled = false;
        toast(r.ok ? tr("Подключено. В новых сессиях там будет твоя память.") : tr("Не вышло") + ": " + r.message);
        if (r.ok) bindTiles();
      }),
  );
}
function provHtml(ps) {
  return ps
    .map(
      (
        p,
      ) => `<div class="prov" data-p="${p.id}"><div><b>${esc(p.name)}</b> <span class="hint">${esc(p.note)}</span></div><span class="${p.ready ? "ok" : "no"}">${p.ready ? "подключено" : "не подключено"}</span>
  <div class="more">${p.needs_key ? `<input class="inp" type="password" placeholder="ключ" value="${esc(p.key)}" data-k>` : `<input class="inp" placeholder="адрес, по умолчанию http://127.0.0.1:11434" value="${esc(p.endpoint)}" data-e>`}<button class="btn l sm" data-pk>Сохранить и найти модели</button>${p.models.length ? `<span class="hint">${p.models.length} моделей</span>` : ""}</div></div>`,
    )
    .join("");
}
function bindProv() {
  $$("[data-pk]").forEach(
    (b) =>
      (b.onclick = async () => {
        const row = b.closest("[data-p]"),
          id = row.dataset.p,
          k = $("[data-k]", row),
          e = $("[data-e]", row);
        b.disabled = true;
        b.textContent = "ищу модели…";
        await post("/api/providers", { id, key: k ? k.value : undefined, endpoint: e ? e.value : undefined });
        const r = await post("/api/providers/models", { id });
        b.disabled = false;
        b.textContent = "Сохранить и найти модели";
        toast(r.ok ? `Нашла моделей: ${r.models.length}` : "Не вышло: " + r.error);
        await refreshProviders();
        viewSettings(SETCUR);
      }),
  );
}

// ---------------- model picker: every provider, connected or not
function modelLabel(v) {
  const [pid, mid] = String(v || "").split(/:(.*)/);
  const p = (CHAT.providers || []).find((x) => x.id === pid);
  if (!p || (CHAT.providers && !p.ready)) return tr("Нет модели — подключить");
  const m = p.models.find((x) => x.id === mid) || { name: mid || p.name };
  return pid === "claude_code"
    ? mid
      ? m.name
      : "Claude"
    : pid === "anthropic"
      ? m.name + " · ключ API"
      : pid === "local"
        ? m.name + " · на компьютере"
        : p.name + " · " + m.name;
}
const SPK_COLORS = ["#5b5bd6", "#0f8b8d", "#c76a12", "#b8327a"];
// a speaker looks the same as its AI everywhere (the tiles in Настройки, the menu): the AI's own colour and sign;
// models of one AI arguing with each other (Sonnet against Opus) differ by the palette and the model's letter
function consDistinct() {
  const m = (CHAT.cons && CHAT.cons.members) || [];
  return new Set(m.map((r) => String(r).split(":")[0])).size === m.length;
}
function spkColor(ref) {
  const m = (CHAT.cons && CHAT.cons.members) || [];
  const i = m.indexOf(ref);
  if (i >= 0 && consDistinct()) return aiLook(String(ref).split(":")[0])[1];
  return SPK_COLORS[(i < 0 ? 0 : i) % SPK_COLORS.length];
}
function spkGlyph(ref, name) {
  const pid = String(ref || "").split(":")[0];
  if (consDistinct() && AI_LOOK[pid]) return AI_LOOK[pid][0];
  const last =
    String(name || "")
      .trim()
      .split(/[\s·]+/)
      .pop() || "?";
  return last.slice(0, 1).toUpperCase();
}
function consName(ref) {
  const [pid, mid] = String(ref).split(/:(.*)/);
  if (pid === "claude_code")
    return (
      { "": "Claude", sonnet: "Claude Sonnet", opus: "Claude Opus", haiku: "Claude Haiku" }[mid || ""] ||
      "Claude " + mid
    );
  const p = (CHAT.providers || []).find((x) => x.id === pid);
  const m = p && p.models.find((x) => x.id === mid);
  if (pid === "local") return m ? m.name : mid;
  if (pid === "anthropic") {
    // "claude-sonnet-4-5" → "Claude Sonnet 4.5", as the server names it
    const out = [];
    for (const part of (mid || "claude").split("-")) {
      const prev = out[out.length - 1];
      if (/^\d{1,2}$/.test(part) && prev && /^[\d.]+$/.test(prev)) out[out.length - 1] = prev + "." + part;
      else out.push(/^\d+$/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1));
    }
    return out.join(" ");
  }
  const base = { openai: "ChatGPT", gemini: "Gemini" }[pid];
  return base && mid ? base + " · " + mid : mid || pid;
}
const CONS_FORMATS = {
  council: {
    n: "Совет",
    d: "каждый отвечает, проверяют друг друга, в конце общий ответ",
    first: "own",
    middle: ["check", "better", "dispute"],
    last: "final",
    art: "🏛️",
  },
  debate: {
    n: "Дебаты",
    d: "одни за, другие против, в конце вердикт",
    first: "pos",
    middle: ["rebut"],
    last: "verdict",
    art: "⚖️",
  },
  brainstorm: {
    n: "Мозговой штурм",
    d: "идеи без критики, потом три лучшие",
    first: "ideas",
    middle: ["grow"],
    last: "best",
    art: "💡",
  },
  redteam: {
    n: "Красная команда",
    d: "ищут дыры в твоём плане и как их закрыть",
    first: "attack",
    middle: ["fix", "attack"],
    last: "risks",
    art: "🎯",
  },
  roast: {
    n: "Прожарка",
    d: "жёстко и по делу разбирают идею, резюме или текст, в конце оценка из 10",
    first: "roast",
    middle: ["roast2"],
    last: "score",
    art: "🔥",
  },
};
const CONS_ROLES = {
  "": "Без роли",
  skeptic: "Скептик",
  practitioner: "Практик",
  finance: "Финансист",
  lawyer: "Юрист",
  creative: "Креативщик",
  analyst: "Аналитик",
  client: "Клиент",
};
const CONS_LEN = {
  short: ["Коротко", "до 80 слов"],
  normal: ["Обычно", "до 150 слов"],
  long: ["Развёрнуто", "до 300 слов"],
};
const CONS_STAGE = {
  pos: ["Позиции", "каждый защищает свою сторону 2–3 доводами"],
  rebut: ["Возражения", "отвечают на сильный довод другой стороны"],
  verdict: ["Вердикт", "честно взвешивают обе стороны"],
  ideas: ["Идеи", "по 3–5 идей, без критики"],
  grow: ["Развитие", "усиливают чужие идеи"],
  best: ["Лучшие идеи", "три лучшие: почему, первый шаг, риск"],
  attack: ["Атака", "ищут, что сломается в твоём плане"],
  fix: ["Как закрыть", "как закрыть самые опасные дыры"],
  risks: ["Риски и что делать", "список: риск, опасность, действие"],
  roast: ["Прожарка", "три самых слабых места, жёстко и по делу"],
  roast2: ["Добивка", "что пропустили, кого зря задели"],
  score: ["Оценка", "оценка из 10 и три правки"],
  own: ["Свой ответ", "каждый отвечает на вопрос сам, прямо и по делу"],
  check: ["Проверка", "ищут слабые места в ответах друг друга"],
  better: ["Улучшение", "собирают лучший ответ из сильного у всех"],
  dispute: ["Спорное", "что не решено и как это решить"],
  final: ["Общий ответ", "ответ, с которым согласен весь совет"],
};
function consPlan(n, fmt) {
  fmt = CONS_FORMATS[fmt] ? fmt : "council";
  let keys;
  if (fmt === "council") {
    const P = { 1: ["own"], 2: ["own", "final"], 3: ["own", "check", "final"], 4: ["own", "check", "better", "final"] };
    keys =
      P[n] ||
      Array.from({ length: n }, (_, r) =>
        r === 0 ? "own" : r === n - 1 ? "final" : ["check", "better", "dispute"][(r - 1) % 3],
      );
  } else {
    const f = CONS_FORMATS[fmt];
    keys =
      n === 1
        ? [f.last]
        : Array.from({ length: n }, (_, r) =>
            r === 0 ? f.first : r === n - 1 ? f.last : f.middle[(r - 1) % f.middle.length],
          );
  }
  return keys.map((k) => CONS_STAGE[k]);
}
function consScheme(sel, fmt, summ) {
  const n = sel.length;
  if (n < 2) return `<div class="cschem empty">${tr("Выбери участников — здесь появится стол")}</div>`;
  const R = 62,
    C = 86,
    pts = sel.map((r, k) => {
      const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
      return [C + R * Math.cos(a), C + R * Math.sin(a)];
    });
  const sumr = summ && sel.includes(summ) ? summ : sel[n - 1];
  const arcs = pts
    .map((p, k) => {
      const q = pts[(k + 1) % n];
      return `<path d="M${p[0].toFixed(1)} ${p[1].toFixed(1)} A${R} ${R} 0 0 1 ${q[0].toFixed(1)} ${q[1].toFixed(1)}" style="--k:${k}"/>`;
    })
    .join("");
  const seats = sel
    .map((r, k) => {
      const [x, y] = pts[k],
        col = SPK_COLORS[k % SPK_COLORS.length],
        side = fmt === "debate" ? (k % 2 === 0 ? "за" : "против") : "";
      return `<div class="cseat" style="left:${x}px;top:${y}px;--sc:${col}"><b>${k + 1}</b>${r === sumr ? `<i class="ccrown">${ic("trophy")}</i>` : ""}${side ? `<em class="${k % 2 === 0 ? "cside-pro" : "cside-con"}">${tr(side)}</em>` : ""}</div>`;
    })
    .join("");
  return `<div class="cschem f-${fmt}"><svg viewBox="0 0 172 172">${arcs}</svg><div class="cschem-table"><span>${CONS_FORMATS[fmt].art}</span></div>${seats}</div>`;
}
// «Подключить ещё ИИ» from the consortium: the AIs not connected yet as tiles; one opens its connect window, and
// when that closes the consortium comes back with whoever got connected
async function connectPick(back) {
  await refreshProviders();
  const P = (CHAT.providers || []).filter((p) => !p.ready && p.id !== "claude_code");
  const pop = document.createElement("div");
  pop.className = "modal cpick";
  pop.innerHTML = `<div class="card"><h2>${tr("Подключить ещё ИИ")}</h2><p class="hint">${tr("Выбери, кого добавить в обсуждение. После подключения вернёшься к консорциуму.")}</p>
    <div class="cpgrid">${
      P.map((p, n) => {
        const [g, c1, c2] = aiLook(p.id, p.name);
        return `<button class="cpt" data-pid="${esc(p.id)}" style="--c1:${c1};--c2:${c2};--d:${n * 0.05}s"><span class="medal2"><span>${esc(g)}</span></span><b data-noi18n>${esc(p.name)}</b><small>${tr(isSubscription(p) ? "по подписке" : p.needs_key ? "по ключу API" : "на компьютере")}</small></button>`;
      }).join("") || `<p class="hint">${tr("Все ИИ уже подключены.")}</p>`
    }</div>
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn g" data-x>${tr("Назад")}</button></div></div>`;
  document.body.appendChild(pop);
  const close = () => {
    pop.remove();
    back && back();
  };
  pop.onclick = (e) => e.target === pop && close();
  $("[data-x]", pop).onclick = close;
  $$("[data-pid]", pop).forEach(
    (b) =>
      (b.onclick = async () => {
        pop.remove();
        await connectModal(b.dataset.pid);
        const watch = setInterval(async () => {
          if ($(".modal.pm")) return;
          clearInterval(watch);
          await refreshProviders();
          back && back();
        }, 300);
      }),
  );
}
async function consortModal(full = false, preset = "") {
  await refreshProviders();
  const cur = CHAT.cons,
    edit = !!(CHAT.id && cur);
  const join = !!(
    CHAT.id &&
    !cur &&
    ((CHAT.chat || {}).messages || []).some((m) => m.role === "assistant" && !m.hidden)
  );
  const ready = (CHAT.providers || []).filter((p) => p.ready && p.models.length);
  if (ready.reduce((n, p) => n + p.models.filter((m) => m.id || p.id !== "claude_code").length, 0) < 2) {
    toast("Для консорциума нужны хотя бы два ИИ — подключи ещё один");
    modelMenu($("#model"));
    return;
  }
  let sel = cur ? [...cur.members] : join && CHAT.model && CHAT.model !== "consortium" ? [CHAT.model] : [],
    rounds = cur ? cur.rounds : 2;
  const def = LS.get("cons_def", {});
  let fmt = preset || (cur && cur.format) || def.format || "council",
    roles = { ...(def.roles || {}), ...((cur && cur.roles) || {}) },
    summ = (cur && cur.summarizer) || "",
    len = (cur && cur.length) || def.length || "normal",
    look = cur ? cur.search !== false : def.search !== false,
    adv = !!full;
  const pop = document.createElement("div");
  pop.className = "modal cm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  const draw = () => {
    const stg = consPlan(rounds, fmt),
      n = sel.length;
    if (summ && !sel.includes(summ)) summ = "";
    pop.innerHTML = adv
      ? `<div class="card cm2 ${adv ? "adv" : "simple"}"><div class="cmhead"><div class="cmic">${ic("users")}</div><div><h2>${join ? tr("Подключить консорциум к этому разговору") : tr("Консорциум — совет из нескольких ИИ")}${hq("consortium")}</h2>
      <p>${join ? tr("ИИ прочитают разговор выше и разберут твой последний вопрос, где прошлый ответ не помог.") : tr("Задаёшь вопрос — несколько ИИ разбирают его по кругам: каждый отвечает, проверяет других, и вместе они приходят к одному ответу. Помогает, когда вопрос спорный или от ответа много зависит.")}</p></div><button class="lmx" id="cmx2">×</button></div>
     <div class="cmsec"><b>1. ${tr("Кто в совете")}</b>${hq("cons_members")}<span class="hint">${tr("от 2 до 4 · по порядку выступлений")}</span></div>
     <div class="cmgrid">${ready
       .map((p) =>
         p.models
           .filter((m) => m.id || p.id !== "claude_code")
           .slice(0, 8)
           .map((m) => {
             const r = p.id + ":" + m.id,
               k = sel.indexOf(r),
               on = k >= 0,
               col = on ? SPK_COLORS[k % SPK_COLORS.length] : "";
             return `<button class="cmm ${on ? "on" : ""}" data-r="${esc(r)}" style="${on ? "--sc:" + col : ""}"><span class="cmav">${on ? k + 1 : esc(consName(r).slice(0, 1))}</span><span class="cmt"><b data-noi18n>${esc(consName(r))}</b><small>${esc(provOf(r))}</small></span>${on ? ic("check") : ""}</button>`;
           })
           .join(""),
       )
       .join("")}
       <button class="cmm add" id="cmconnect"><span class="cmav">+</span><span class="cmt"><b>${tr("Подключить ещё ИИ")}</b><small>${tr("ChatGPT, Gemini, свои модели")}</small></span></button></div>
     <div class="cmsec"><b>2. ${tr("Сколько кругов")}</b>${hq("cons_rounds")}<span class="hint">${tr("больше кругов — глубже разбор и больше запросов")}</span></div>
     <div class="cmrounds">${[1, 2, 3, 4, 5].map((k) => `<button data-rk="${k}" class="${rounds === k ? "on" : ""}">${k}</button>`).join("")}<div class="stepper sm"><button data-st="-1" ${rounds <= 1 ? "disabled" : ""}>−</button><b>${rounds}</b><button data-st="1" ${rounds >= 20 ? "disabled" : ""}>+</button></div></div>
     <div class="cmsec"><b>3. ${tr("Как обсуждают")}</b>${hq("cons_format")}<span class="hint">${tr("формат задаёт, что делает каждый круг")}</span></div>
     <div class="cmfmt">${Object.entries(CONS_FORMATS)
       .map(
         ([k, f]) =>
           `<button data-fmt="${k}" class="${fmt === k ? "on" : ""}"><span class="fart f-${k}">${f.art}</span><b>${tr(f.n)}</b><small>${tr(f.d)}</small></button>`,
       )
       .join("")}</div>
     ${
       n
         ? `<div class="cmsec"><b>4. ${tr("Роли")}</b>${hq("cons_roles")}<span class="hint">${tr("с какой стороны каждый смотрит на вопрос")}</span></div>
     <div class="cmroles">${sel
       .map(
         (r, k) =>
           `<div class="cmrole" style="--sc:${SPK_COLORS[k % SPK_COLORS.length]}"><span class="cmav">${k + 1}</span><b data-noi18n>${esc(consName(r))}</b>${fmt === "debate" ? `<em class="${k % 2 === 0 ? "cside-pro" : "cside-con"}">${tr(k % 2 === 0 ? "за" : "против")}</em>` : ""}<select class="inp sm" data-role="${esc(r)}">${Object.entries(
             CONS_ROLES,
           )
             .map(([v, l]) => `<option value="${v}" ${(roles[r] || "") === v ? "selected" : ""}>${tr(l)}</option>`)
             .join("")}</select></div>`,
       )
       .join("")}</div>`
         : ""
     }
     <div class="cmsec"><b>${n ? 5 : 4}. ${tr("Итог и длина реплик")}</b>${hq("cons_sum")}<span class="hint">${tr("кто подводит итог и насколько подробно говорят")}</span></div>
     <div class="cmsum2"><div class="cmbox"><div class="cmbh">${ic("trophy")}<b>${tr("Итог подводит")}</b></div><div class="cmpick">${[
       ["", tr("последний по очереди"), ""],
       ...sel.map((r, k) => [r, consName(r), SPK_COLORS[k % SPK_COLORS.length], k + 1]),
     ]
       .map(
         ([v, l, col, num]) =>
           `<button data-summ="${esc(v)}" class="${summ === v ? "on" : ""}" style="${col ? "--sc:" + col : ""}"><span class="cmav ${v ? "" : "auto"}">${v ? num : ic("redo")}</span><span class="cmpl" data-noi18n>${esc(l)}</span>${summ === v ? ic("check") : ""}</button>`,
       )
       .join("")}</div></div>
       <div class="cmbox"><div class="cmbh">${ic("list")}<b>${tr("Реплики")}</b></div><div class="cmlen">${Object.entries(
         CONS_LEN,
       )
         .map(
           ([v, [l, h]], k) =>
             `<button data-len="${v}" class="${len === v ? "on" : ""}"><span class="lbars">${[0, 1, 2, 3]
               .slice(0, k + 2)
               .map((x) => `<i style="--w:${[100, 82, 92, 60][x]}%"></i>`)
               .join("")}</span><b>${tr(l)}</b><small>${tr(h)}</small></button>`,
         )
         .join("")}</div></div></div>
     <div class="cmsec"><b>${n ? 6 : 5}. ${tr("Проверка фактов")}</b>${hq("cons_search")}<span class="hint">${tr("участники сами ищут в интернете, чтобы подтвердить слова")}</span></div>
     <button class="cmsearch ${look ? "on" : ""}" id="cmlook"><span class="cmsico">${ic("globe")}</span><span class="cmst"><b>${tr("Искать в интернете")}</b><small>${look ? tr("до двух запросов за ход, источники под репликой") : tr("отвечают только из своих знаний")}</small></span><i class="sw ${look ? "on" : ""}"></i></button>
     <div class="cmsec"><b>${tr("Как пойдёт обсуждение")}</b></div>
     <div class="cmviz">${consScheme(sel, fmt, summ)}<div class="cmplan">${stg.map(([t, d], k) => `<div class="cmstep" style="--d:${k * 0.05}s"><span class="cmn">${k + 1}</span><div><b>${tr(t)}</b><small>${tr(d)}</small></div></div>`).join("")}
       <div class="cmstep fin"><span class="cmn">${ic("trophy")}</span><div><b>${tr("Итог")}</b><small>${summ && sel.includes(summ) ? esc(consName(summ)) + " — " + tr("отвечает на твой вопрос прямо: в чём сошлись и что советуют") : tr("последний выступающий отвечает на твой вопрос прямо: в чём сошлись и что советуют")}</small></div></div></div></div>
     <div class="cmfoot"><button class="btn g cmadvb" id="cmsimple">← ${tr("Проще")}</button><span class="hint">${n >= 2 ? `${tr("Выступлений")}: ${n} × ${rounds} = <b>${n * rounds}</b> · ${tr("вмешаться и поставить на паузу можно в любой момент")}` : tr("Выбери хотя бы двух участников")}</span>
       <div class="row" style="gap:8px">${edit ? `<button class="btn g" id="cmoff">${tr("Выйти из консорциума")}</button>` : ""}<button class="btn g" id="cmx">${tr("Отмена")}</button><button class="btn" id="cmgo" ${n < 2 ? "disabled" : ""}>${edit ? tr("Сохранить") : join ? tr("Обсудить этот разговор") : tr("Собрать совет")}</button></div></div></div>`
      : `<div class="card cm2 ${adv ? "adv" : "simple"}"><div class="cmhead"><div class="cmic">${ic("users")}</div><div><h2>${join ? tr("Подключить консорциум к этому разговору") : tr("Консорциум — совет из нескольких ИИ")}${hq("consortium")}</h2>
      <p>${join ? tr("ИИ прочитают разговор выше и разберут твой последний вопрос, где прошлый ответ не помог.") : tr("Задаёшь вопрос — несколько ИИ разбирают его по кругам: каждый отвечает, проверяет других, и вместе они приходят к одному ответу. Помогает, когда вопрос спорный или от ответа много зависит.")}</p></div><button class="lmx" id="cmx2">×</button></div>
     <div class="cmsec"><b>1. ${tr("Кто в совете")}</b>${hq("cons_members")}<span class="hint">${tr("от 2 до 4 · по порядку выступлений")}</span></div>
     <div class="cmgrid">${ready
       .map((p) =>
         p.models
           .filter((m) => m.id || p.id !== "claude_code")
           .slice(0, 8)
           .map((m) => {
             const r = p.id + ":" + m.id,
               k = sel.indexOf(r),
               on = k >= 0,
               col = on ? SPK_COLORS[k % SPK_COLORS.length] : "";
             return `<button class="cmm ${on ? "on" : ""}" data-r="${esc(r)}" style="${on ? "--sc:" + col : ""}"><span class="cmav">${on ? k + 1 : esc(consName(r).slice(0, 1))}</span><span class="cmt"><b data-noi18n>${esc(consName(r))}</b><small>${esc(provOf(r))}</small></span>${on ? ic("check") : ""}</button>`;
           })
           .join(""),
       )
       .join("")}
       <button class="cmm add" id="cmconnect"><span class="cmav">+</span><span class="cmt"><b>${tr("Подключить ещё ИИ")}</b><small>${tr("ChatGPT, Gemini, свои модели")}</small></span></button></div>
     <div class="cmsec"><b>2. ${tr("Как обсуждают")}</b>${hq("cons_format")}<span class="hint">${tr("формат задаёт, что делает каждый круг")}</span></div>
     <div class="cmfmt">${Object.entries(CONS_FORMATS)
       .map(
         ([k, f]) =>
           `<button data-fmt="${k}" class="${fmt === k ? "on" : ""}"><span class="fart f-${k}">${f.art}</span><b>${tr(f.n)}</b><small>${tr(f.d)}</small></button>`,
       )
       .join("")}</div>
     <div class="cmprev">${consScheme(sel, fmt, summ)}<div class="cmprevt">${
       n >= 2
         ? `<b>${tr("Совет собран")}</b><div class="cmorder">${sel.map((r, k) => `<span style="--sc:${SPK_COLORS[k % SPK_COLORS.length]};--d:${k * 0.08}s"><i>${k + 1}</i><em data-noi18n>${esc(consName(r))}</em></span>`).join("")}</div><small>${tr(CONS_FORMATS[fmt].n)} · ${tr("кругов")}: ${rounds} · ${look ? tr("проверяют факты в интернете") : tr("без интернета")}</small>`
         : `<b>${tr("Выбери 2–4 ИИ")}</b><small>${tr("они сядут за стол и обсудят твой вопрос по очереди")}</small>`
     }</div></div>
     <div class="cmfoot"><button class="btn g cmadvb" id="cmadv">${ic("set")}${tr("Продвинутая настройка")}</button>
       <div class="row" style="gap:8px">${edit ? `<button class="btn g" id="cmoff">${tr("Выйти из консорциума")}</button>` : ""}<button class="btn g" id="cmx">${tr("Отмена")}</button><button class="btn" id="cmgo" ${n < 2 ? "disabled" : ""}>${edit ? tr("Сохранить") : join ? tr("Обсудить этот разговор") : tr("Собрать совет")}</button></div></div></div>`;
    if ($("#cmadv", pop))
      $("#cmadv", pop).onclick = () => {
        adv = true;
        draw();
        $(".cm2", pop).scrollTop = 0;
      };
    if ($("#cmsimple", pop))
      $("#cmsimple", pop).onclick = () => {
        adv = false;
        draw();
      };
    if ($("#cmlook", pop))
      $("#cmlook", pop).onclick = () => {
        look = !look;
        draw();
      };
    $$("[data-rk]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          rounds = +b.dataset.rk;
          draw();
        }),
    );
    $$("[data-fmt]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          fmt = b.dataset.fmt;
          draw();
        }),
    );
    $$("[data-summ]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          summ = b.dataset.summ;
          draw();
        }),
    );
    $$("[data-len]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          len = b.dataset.len;
          draw();
        }),
    );
    $$("[data-role]", pop).forEach(
      (x) =>
        (x.onchange = () => {
          roles[x.dataset.role] = x.value;
          draw();
        }),
    );
    if ($("#cmx2", pop)) $("#cmx2", pop).onclick = () => pop.remove();
    $$("[data-r]", pop).forEach(
      (c) =>
        (c.onclick = () => {
          const r = c.dataset.r;
          if (!sel.includes(r)) {
            if (sel.length >= 4) {
              toast(tr("Не больше четырёх"));
              return;
            }
            sel.push(r);
          } else sel = sel.filter((x) => x !== r);
          draw();
        }),
    );
    $$("[data-st]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          rounds = Math.max(1, Math.min(20, rounds + +b.dataset.st));
          draw();
        }),
    );
    $("#cmx", pop).onclick = () => pop.remove();
    $("#cmconnect", pop).onclick = (e) => {
      // a window of its own over the consortium, and back to the consortium when done (the model menu used to open
      // here and close at once on the same click, so the window just vanished)
      e.preventDefault();
      e.stopPropagation();
      pop.remove();
      connectPick(() => consortModal(full, preset));
    };
    if ($("#cmoff", pop))
      $("#cmoff", pop).onclick = () => {
        pop.remove();
        consAct("off");
      };
    $("#cmgo", pop).onclick = async () => {
      const rl = {};
      sel.forEach((r) => {
        if (roles[r]) rl[r] = roles[r];
      });
      const opts = { format: fmt, roles: rl, summarizer: summ, length: len, search: look },
        cfg = { members: sel, rounds, ...opts };
      pop.remove();
      LS.set("cons_def", {
        format: fmt,
        length: len,
        search: look,
        roles: { ...(LS.get("cons_def", {}).roles || {}), ...rl },
      });
      if (join) {
        try {
          await post("/api/chat/cons", { chat: CHAT.id, action: "start", members: sel, rounds, ...opts });
          const c = await api("/api/chat?id=" + CHAT.id);
          renderChat(c);
          $("#msgs").insertAdjacentHTML(
            "beforeend",
            `<div class="msg ai" id="live"><div class="av"></div><div><div class="md">${TYPING}</div></div></div>`,
          );
          scrollEnd();
          poll();
        } catch (e) {
          toast(e.message);
        }
      } else if (edit) {
        await consAct("set", { members: sel, rounds, ...opts });
      } else {
        CHAT.pendingCons = cfg;
        await viewChat();
        $("#inp").focus();
      }
    };
  };
  draw();
}
function drawModelLabel() {
  setTimeout(() => {
    drawChips();
    heatShow();
    drawTable();
  }, 0);
  drawState();
  const f = $("#mfree");
  const ready = (CHAT.providers || []).find((x) => x.id === String(CHAT.model || "").split(":")[0] && x.ready);
  if (f) f.textContent = CHAT.cons ? tr("несколько ИИ") : ready ? provOf(CHAT.model) : tr("скачай или укажи ключ");
  const l = $("#mlabel");
  if (l) l.textContent = CHAT.cons ? `Консорциум · ${CHAT.cons.members.length} ИИ` : modelLabel(CHAT.model);
  if ($("#model")) $("#model").classList.toggle("none", !CHAT.cons && !ready);
  const b = $("#conbtn");
  if (b) b.classList.toggle("on", !!CHAT.cons);
}
function provOf(v) {
  const pid = String(v || "").split(":")[0];
  return tr(
    {
      claude_code: "Claude по подписке",
      anthropic: "Claude · ключ API",
      openai: "ChatGPT · ключ API",
      gemini: "Google Gemini",
      openrouter: "OpenRouter",
      deepseek: "DeepSeek · ключ API",
      yandex: "YandexGPT · Yandex Cloud",
      ollama: "Ollama · на компьютере",
      strata: "Strata · на компьютере",
      local: "на этом компьютере",
    }[pid] || (pid ? pid : ""),
  );
}
function warmLocal(v) {
  if (!/^local:/.test(String(v || ""))) return;
  post("/api/local/warm", { model: v }).catch(() => {});
}
const SESSION_WARNED = {};
function setModel(v) {
  CHAT.model = v;
  drawModelLabel();
  warmLocal(v);
  if (v && v !== "consortium") post("/api/agent", { last_model: v }).catch(() => {});
  if (!CHAT.id && $(".startline")) renderEmpty();
}
async function refreshProviders() {
  CHAT.providers = (await api("/api/models")).providers;
  drawModelLabel();
}
function mHead(letter, name, status, on) {
  return `<div class="mh"><span class="mav ${on ? "on" : ""}">${esc(letter)}</span><b>${esc(name)}</b><span class="mst ${on ? "on" : ""}">${esc(tr(status))}</span></div>`;
}
function mRow(ref, name, meta, cur) {
  return `<button data-m="${esc(ref)}" class="mrow ${cur ? "cur" : ""}"><i class="rd"></i><span class="mn">${esc(name)}</span>${meta ? `<span class="mm">${esc(tr(meta))}</span>` : ""}</button>`;
}
function mAdd(pid, label) {
  return `<button class="mrow madd" data-p="${esc(pid)}"><i class="pl">${ic("plus")}</i><span class="mn">${esc(tr(label))}</span></button>`;
}
function modelMenu(anchor) {
  if ($(".mmenu")) {
    $(".mmenu").remove();
    return;
  }
  closeMenus();
  MENU_ANCHOR = anchor;
  const m = document.createElement("div");
  m.className = "mmenu menu mm2";
  // connected providers side by side as cards; not connected — one row of «+ connect» chips under them
  const P = CHAT.providers || [],
    cc = P.find((p) => p.id === "claude_code"),
    an = P.find((p) => p.id === "anthropic");
  const COL = {
    local: "#10b981",
    claude_code: "#d97757",
    anthropic: "#d97757",
    openai: "#10a37f",
    gemini: "#4f7cf7",
    openrouter: "#7c5cf0",
    deepseek: "#4d6bfe",
    yandex: "#fc3f1d",
    ollama: "#334155",
    strata: "#0ea5e9",
  };
  const NM = {
    local: "Встроенная модель",
    claude_code: "Claude по подписке",
    openai: "ChatGPT",
    gemini: "Gemini",
    openrouter: "OpenRouter",
    deepseek: "DeepSeek",
    yandex: "YandexGPT",
    ollama: "Ollama",
    strata: "Strata",
    anthropic: "Claude · ключ API",
  };
  const ready = P.filter((p) => p.ready),
    LOCAL = ["local", "ollama", "strata"],
    label = (p) => tr(NM[p.id] || p.name),
    // cloud first, then this computer; inside each — by name: no model goes first because of who made it
    byName = (a, b) => LOCAL.includes(a.id) - LOCAL.includes(b.id) || label(a).localeCompare(label(b));
  // one rule for every AI: its three best models, the chosen one if it is further down, and «Все модели» under them
  const TOP = 3;
  const shown = (p) => {
    const ms = (p.id === "claude_code" ? p.models.filter((x) => x.id) : p.models).filter((x) => !x.old);
    const top = ms.slice(0, TOP);
    const cur = p.models.find((x) => p.id + ":" + x.id === CHAT.model && x.id);
    if (cur && !top.includes(cur)) top.push(cur);
    return top;
  };
  const mrow = (p, x) => {
    const ref = p.id + ":" + x.id;
    const on = ref === CHAT.model || (ref === "claude_code:sonnet" && CHAT.model === "claude_code:");
    return `<button data-m="${esc(ref)}" class="m3row ${on ? "cur" : ""}" style="--pc:${COL[p.id] || "#64748b"}"><i></i><span data-noi18n>${esc(x.name)}</span></button>`;
  };
  const group = (p) =>
    `<div class="m3grp m3prov"><span>${esc(label(p))}</span><button class="m3all" data-p="${p.id}">${tr("Все модели")} · ${p.models.filter((x) => x.id || p.id !== "claude_code").length}</button></div>` +
    shown(p)
      .map((x) => mrow(p, x))
      .join("");
  const sorted = ready.sort(byName);
  // paid first — by subscription, then by an API key; then the free ones on this computer
  const subs = sorted.filter((p) => isSubscription(p)),
    keys = sorted.filter((p) => !LOCAL.includes(p.id) && !isSubscription(p)),
    here = sorted.filter((p) => LOCAL.includes(p.id));
  const sec = (title, list) => (list.length ? `<div class="m3sec">${title}</div>` + list.map(group).join("") : "");
  const cards =
    sec(`${tr("Платные")} · ${tr("по подписке")}`, subs) +
    sec(`${tr("Платные")} · ${tr("по ключу API")}`, keys) +
    sec(tr("Бесплатные"), here);
  const add = P.filter((p) => !p.ready)
    .sort(byName)
    .map(
      (p) =>
        // a row like the connected AIs above: the name, how it connects, and «Подключить» on the right
        `<button class="m3grp m3prov m2conn" data-p="${p.id}" style="--pc:${COL[p.id] || "#64748b"}"><span>${tr(p.id === "local" ? "Встроенная модель" : p.id === "anthropic" ? "Claude · ключ API" : p.id === "claude_code" ? "Подписка Claude" : NM[p.id] || p.name)}<small>${tr(p.id === "local" ? "бесплатно на компьютере" : ["ollama", "strata"].includes(p.id) ? "на компьютере" : p.id === "claude_code" ? "по подписке" : "по ключу API")}</small></span><em>${tr(p.id === "local" ? "Скачать" : "Подключить")}</em></button>`,
    )
    .join("");
  m.innerHTML = `<div class="m3list">${cards || `<div class="hint" style="padding:10px">${tr("Пока ни одного ИИ не подключено")}</div>`}</div>${add ? `<div class="m2foot"><span>${tr("Подключить ещё")}</span><div class="m2conns">${add}</div></div>` : ""}`;
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.max(8, Math.min(window.innerWidth - m.offsetWidth - 8, r.left)) + "px";
  m.style.top = r.bottom + 6 + "px";
  $$("[data-m]", m).forEach(
    (b) =>
      (b.onclick = () => {
        m.remove();
        setModel(b.dataset.m);
      }),
  );
  $$("[data-p]", m).forEach(
    (b) =>
      (b.onclick = () => {
        m.remove();
        b.dataset.p === "local" ? localModal() : connectModal(b.dataset.p);
      }),
  );
}
const PROV_HOW = {
  claude_code: {
    t: "Нужны подписка Claude и Claude Code от Anthropic — отдельная программа или та, что идёт внутри приложения Claude Desktop. Mnemai находит её сама. Если Claude Code найден, но не подключён, — нажми «Войти» на плитке и войди своей подпиской.",
    u: "https://code.claude.com/docs/en/setup",
  },
  opencode_go: {
    t: "Открой консоль OpenCode Go, создай API-ключ подписки и вставь его ниже. Mnemai сохранит ключ в защищённом хранилище системы. OpenCode Go предназначен прежде всего для запросов в стиле кодинг-агента; условия и поддерживаемые модели смотри в документации OpenCode.",
    u: "https://opencode.ai/console/go",
  },
  codex: {
    t: "Войди через официальный Sign in with ChatGPT и отдельно разреши Mnemai использовать лимит подписки. OAuth-токены Mnemai хранит в защищённом хранилище системы. Для ответов нужен установленный Codex CLI App Server; вход Codex CLI Mnemai не читает.",
    u: "https://developers.openai.com/siwc/token-sharing-open-source/sign-in",
  },
  anthropic: {
    t: "Ключ берётся на console.anthropic.com, раздел API Keys. Подписка Claude Pro ключа не даёт: для неё есть «Claude по подписке».",
    u: "https://console.anthropic.com/settings/keys",
  },
  openai: {
    t: "Ключ берётся на platform.openai.com/api-keys — «Create new secret key». Подписка ChatGPT Plus ключа не даёт: API оплачивается отдельно, по расходу.",
    u: "https://platform.openai.com/api-keys",
  },
  gemini: {
    t: "Ключ берётся в Google AI Studio: aistudio.google.com → Get API key.",
    u: "https://aistudio.google.com",
  },
  openrouter: { t: "Один ключ на сотни моделей разных компаний: openrouter.ai/keys.", u: "https://openrouter.ai/keys" },
  deepseek: {
    t: "Ключ берётся на platform.deepseek.com, раздел API keys. Оплата по расходу, отдельно от чата DeepSeek.",
    u: "https://platform.deepseek.com/api_keys",
  },
  yandex: {
    t: "В Yandex Cloud AI Studio создай API-ключ сервисного аккаунта с ролью ai.languageModels.user и скопируй ID каталога, в котором он создан. Оплата по расходу в Yandex Cloud.",
    u: "https://aistudio.yandex.ru",
  },
  strata: {
    t: "Strata запускает большие модели (Qwen, DeepSeek) на этом компьютере, бесплатно и без интернета. Поставь Strata, запусти модель (strata launch) и нажми «Проверить». Адрес по умолчанию — 127.0.0.1:8080.",
    u: "https://github.com/Niko1221/Strata",
  },
  ollama: {
    t: "Нужна установленная и запущенная Ollama (ollama.com). Адрес по умолчанию — http://127.0.0.1:11434.",
    u: "https://ollama.com",
  },
};
async function connectModal(pid) {
  await refreshProviders();
  const p = CHAT.providers.find((x) => x.id === pid);
  if (!p) return;
  const pop = document.createElement("div");
  pop.className = "modal pm";
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  const how = PROV_HOW[pid] || { t: "" };
  const draw = (models, msg) => {
    const list = (models || p.models).map((x) => (typeof x === "string" ? { id: x, name: x } : x));
    const good = list.filter((x) => !x.old),
      aged = list.filter((x) => x.old);
    const btn = (x) =>
      `<button data-pm="${esc(x.id)}" class="${p.id + ":" + x.id === CHAT.model ? "cur" : ""}">${esc(x.name)}</button>`;
    // connected: the models come first, the key and the check fold below; not yet: how to connect first
    const models_ = list.length
      ? `<div class="fld" style="margin-top:12px"><span>${tr("Выбери модель")} (${list.length})</span><input id="pq" placeholder="${tr("поиск")}"></div><div class="mlist" id="pml">${good.map(btn).join("")}${aged.length ? `<div class="mlold">${tr("Старые и служебные")}</div>${aged.map(btn).join("")}` : ""}</div>`
      : "";
    const setup = `<div class="how">${esc(how.t)}${how.u ? ` <a href="#" id="openu" style="color:var(--acc)">Открыть сайт</a>` : ""}</div>
    ${pid === "claude_code" || pid === "codex" ? "" : p.needs_key ? `<div class="fld"><span>Ключ API хранится в защищённом хранилище системы, не в папке памяти</span><input id="pkey" type="password" placeholder="${p.key ? "сохранён " + esc(p.key) : "вставь ключ"}"></div>` : `<div class="fld"><span>Адрес</span><input id="pend" value="${esc(p.endpoint)}" placeholder="${pid === "strata" ? "http://127.0.0.1:8080/v1" : "http://127.0.0.1:11434"}"></div>`}
    ${pid === "yandex" ? `<div class="fld"><span>${tr("ID каталога Yandex Cloud")}</span><input id="pfolder" value="${esc(p.folder || "")}" placeholder="b1g…"></div>` : ""}
    ${pid === "codex" ? `<div class="row"><button class="btn" id="pcodexlogin">${tr("Продолжить с ChatGPT")}</button></div>` : ""}
    <div class="row" style="margin-top:10px"><button class="btn" id="pgo">${pid === "claude_code" || pid === "codex" ? "Проверить снова" : "Проверить и найти модели"}</button><span class="hint" id="pmsg">${esc(msg || "")}</span></div>`;
    const on = p.connected && !p.disabled && list.length;
    pop.innerHTML = `<div class="card"><h2>${esc(p.name)} <span class="hint">${provState(p)}</span></h2>
    ${p.problem && !p.disabled ? `<div class="aiprob">${esc(p.problem)}</div>` : ""}
    ${p.disabled ? `<div class="how">${tr("Этот ИИ выключен: его нет в списках моделей. Ключ и настройки сохранены.")} <button class="btn sm" id="pon">${tr("Включить")}</button></div>` : ""}
    ${on ? `${models_}<details class="pmset" ${msg ? "open" : ""}><summary>${tr(p.needs_key ? "Ключ и проверка" : "Подключение и проверка")}</summary>${setup}</details>` : setup + models_}
    <div class="row" style="margin-top:12px;justify-content:flex-end"><button class="btn g sm" id="pclose">Закрыть</button></div></div>`;
    $("#pclose", pop).onclick = () => pop.remove();
    if ($("#pon", pop))
      $("#pon", pop).onclick = async () => {
        await post("/api/providers", { id: pid, disabled: false });
        await refreshProviders();
        Object.assign(
          p,
          CHAT.providers.find((x) => x.id === pid),
        );
        draw(null, "Включено");
      };
    if ($("#openu", pop))
      $("#openu", pop).onclick = (e) => {
        e.preventDefault();
        post("/api/open_url", { url: how.u }).catch(() => toast(how.u));
      };
    if ($("#pcodexlogin", pop))
      $("#pcodexlogin", pop).onclick = async () => {
        const r = await post("/api/providers/codex_login", {});
        if (r.ok && r.url) await post("/api/open_url", { url: r.url });
        $("#pmsg", pop).textContent = r.ok
          ? "В браузере подтверди вход и разрешение использовать подписку ChatGPT, затем нажми «Проверить снова»."
          : r.error;
      };
    if ($("#pq", pop))
      $("#pq", pop).oninput = (e) => {
        const q = e.target.value.toLowerCase();
        $$("[data-pm]", pop).forEach((b) => (b.hidden = !b.textContent.toLowerCase().includes(q)));
      };
    $$("[data-pm]", pop).forEach(
      (b) =>
        (b.onclick = async () => {
          await refreshProviders();
          pop.remove();
          setModel(pid + ":" + b.dataset.pm);
        }),
    );
    $("#pgo", pop).onclick = async () => {
      const k = $("#pkey", pop),
        e = $("#pend", pop),
        fo = $("#pfolder", pop);
      $("#pmsg", pop).textContent = "проверяю…";
      try {
        if (pid !== "claude_code")
          await post("/api/providers", {
            id: pid,
            key: k && k.value ? k.value : undefined,
            endpoint: e ? e.value : undefined,
            folder: fo ? fo.value : undefined,
          });
        if (pid === "claude_code" || pid === "codex") {
          const r = await post("/api/providers/check", { id: pid });
          await refreshProviders();
          const q = CHAT.providers.find((x) => x.id === pid);
          Object.assign(p, q);
          draw(
            null,
            r.ok
              ? pid === "codex"
                ? "ChatGPT отвечает — выбери модель"
                : "Claude отвечает — выбери модель"
              : "Не вышло: " + r.error,
          );
        } else {
          const r = await post("/api/providers/models", { id: pid });
          await refreshProviders();
          Object.assign(
            p,
            CHAT.providers.find((x) => x.id === pid),
          );
          draw(null, r.ok ? `Подключено: ${r.models.length} моделей` : "Не вышло: " + r.error);
        }
      } catch (err) {
        $("#pmsg", pop).textContent = "Не вышло: " + err.message;
      }
    };
  };
  draw();
}

// ---------------------------------------------------------------- «Как отвечает»: tiles on the left, a live sample answer on the right
const YOU_LOOK = {
  soft: ["☕", "#f472b6", "#fb923c", 1],
  business: ["💼", "#6366f1", "#22d3ee", 2],
  strict: ["🛡️", "#10b981", "#0ea5e9", 3],
};
function youPreview(prof, ag) {
  const simple = prof.simple || {},
    vy = simple.address === "vy",
    len = simple.length || "normal",
    g = prof.gender || "",
    pr = prof.preset || "business",
    name = (prof.owner_name || "").trim();
  const hi = vy
    ? name
      ? `${esc(name)}, ${tr("добрый день")}.`
      : tr("Добрый день.")
    : name
      ? `${esc(name)}, ${tr("привет")}.`
      : tr("Привет.");
  const right = tr(
    vy ? "вы были правы" : g === "f" ? "ты была права" : g === "m" ? "ты был прав" : "оценка сроков точная",
  );
  const agree = tr(vy ? "согласуете" : "согласуешь");
  const body = {
    short: [`${tr("Да, успеваем")} — ${right}. ${tr("Осталось согласовать отдел.")}`],
    normal: [
      `${tr("Да, успеваем")} — ${right}. ${tr("Осталось два шага")}: ${tr("согласовать отдел и подготовить доступы")}. ${tr("Первое лучше закрыть на этой неделе.")}`,
    ],
    long: [
      `${tr("Да, успеваем, если до пятницы")} ${agree} ${tr("отдел")} — ${right}.`,
      `<ul><li>${tr("согласовать отдел — до пятницы")}</li><li>${tr("подготовить доступы — два дня")}</li><li>${tr("короткий инструктаж — в день старта")}</li></ul>`,
      `${tr("Риск один: отпуск руководителя в конце месяца.")}`,
    ],
  }[len];
  const extra =
    pr === "soft"
      ? `<p class="ypsoft">${tr("Всё получится, план реальный")} 🙂</p>`
      : pr === "strict"
        ? `<p class="ypchk">${ic("check")}${tr("Сверила с памятью: дата старта — из решения от 12 октября")}</p>`
        : "";
  return `<div class="yphead"><span>${tr("Пример ответа")}</span><small>${tr("меняется вместе с настройками")}</small></div>
    <div class="ypq">${tr("Успеваем запустить пилот к ноябрю?")}</div>
    <div class="ypa"><span class="ypav">M</span><div class="ypt"><p>${hi} ${body[0]}</p>${body
      .slice(1)
      .map((x) => (x.startsWith("<ul") ? x : `<p>${x}</p>`))
      .join("")}${extra}</div></div>
    <div class="yptags"><span>${vy ? tr("на вы") : tr("на ты")}</span><span>${esc((ag.simple.length.choices || {})[len] || "")}</span><span>${esc(((ag.presets || {})[pr] || {}).name || "")}</span></div>`;
}
function youCard(prof, ag) {
  const simple = prof.simple || {},
    name = (prof.owner_name || "").trim();
  const addr = [
    ["ty", tr("на ты"), name ? `${tr("Привет")}, ${name}!` : `${tr("Привет")}!`],
    ["vy", tr("на вы"), name ? `${tr("Здравствуйте")}, ${name}!` : `${tr("Здравствуйте")}!`],
  ];
  const lens = [
    ["short", tr("коротко"), tr("одна-две фразы"), 1],
    ["normal", tr("по делу"), tr("суть и шаги"), 3],
    ["long", tr("подробно"), tr("с разбором и рисками"), 5],
  ];
  const lines = (n) =>
    `<i class="ylines">${Array.from({ length: n }, (_, k) => `<em style="--w:${[92, 78, 86, 64, 72][k]}%;--k:${k}"></em>`).join("")}</i>`;
  const pr = prof.preset || "business";
  return `<div class="card ycard" data-sec="style" id="c-you">
    <div class="ytop">
      <div class="yform">
        <div class="yrow"><div class="ylab">${tr("Как тебя зовут")}</div><label class="yname"><span class="yav">${esc((name || "?").slice(0, 1).toUpperCase())}</span><input id="oname" value="${esc(name)}" placeholder="${tr("имя")}"></label></div>
        <div class="yrow"><div class="ylab">${tr("Обращение")}</div><div class="yopts y2" data-seg="address">${addr
          .map(
            ([k, l, ex]) =>
              `<button data-v="${k}" class="yt ${(simple.address || "ty") === k ? "on" : ""}" style="--c1:${k === "ty" ? "#f59e0b" : "#6366f1"};--c2:${k === "ty" ? "#f97316" : "#334155"}"><span class="medal2 ytm"><span>${k === "ty" ? "👋" : "🎩"}</span></span><b>${l}</b><span class="ybub">${esc(ex)}</span></button>`,
          )
          .join("")}</div></div>
        <div class="yrow"><div class="ylab">${tr("Длина ответа")}</div><div class="yopts y3" data-seg="length">${lens
          .map(
            ([k, l, h, n]) =>
              `<button data-v="${k}" class="yt ${(simple.length || "normal") === k ? "on" : ""}" style="--c1:${{ short: "#10b981", normal: "#6366f1", long: "#0ea5e9" }[k]};--c2:${{ short: "#14b8a6", normal: "#a855f7", long: "#22d3ee" }[k]}"><span class="ytop2"><span class="medal2 ytm"><span>${{ short: "⚡", normal: "🎯", long: "📚" }[k]}</span></span>${lines(n)}</span><b>${l}</b><small>${h}</small></button>`,
          )
          .join("")}</div></div>
        <div class="yrow"><div class="ylab">${tr("Пол")}<small>${tr("для окончаний: прав или права")}</small></div><div class="seg yseg" data-seg="gender">${[
          ["m", tr("мужской")],
          ["f", tr("женский")],
          ["", tr("не указывать")],
        ]
          .map(([k, l]) => `<button data-v="${k}" class="${(prof.gender || "") === k ? "on" : ""}">${l}</button>`)
          .join("")}</div></div>
      </div>
    </div>
    <div class="ychar"><div class="ylab">${tr("Характер")}${hq("presets")}</div><div class="yprs">${Object.entries(
      ag.presets,
    )
      .map(([k, p], n) => {
        const [em, c1, c2, lvl] = YOU_LOOK[k] || ["✨", "#6366f1", "#22d3ee", 2];
        return `<button data-pr="${k}" class="ypr ${pr === k ? "on" : ""}" style="--c1:${c1};--c2:${c2};--d:${n * 0.06}s"><span class="medal2"><span>${em}</span><i class="spark"></i><i class="spark"></i><i class="spark"></i></span><span class="yprt"><b>${esc(p.name)}</b><span>${esc(p.note)}</span><span class="ylvl">${tr("Проверки")}<i>${[1, 2, 3].map((x) => `<em class="${x <= lvl ? "f" : ""}"></em>`).join("")}</i></span></span>${pr === k ? `<span class="yok">${ic("check")}</span>` : ""}</button>`;
      })
      .join("")}</div></div>
    <div class="ypv" id="ypv">${youPreview(prof, ag)}</div>
  </div>`;
}

// Mnemai's own encryption: turn on (a new password twice), turn off (the password), change the password
function cryptoModal(mode, done) {
  const pop = document.createElement("div");
  pop.className = "modal cryptm";
  const T = {
    on: [
      "Зашифровать память",
      "Придумай пароль не короче 8 знаков. Его нельзя восстановить: забудешь — память не вернуть. Obsidian и другие редакторы эти файлы открыть не смогут.",
      "Зашифровать",
    ],
    off: ["Снять шифрование", "Файлы памяти снова станут обычными. Введи пароль.", "Снять"],
    password: ["Сменить пароль", "Файлы не переписываются — меняется только ключ к ним.", "Сменить"],
  }[mode];
  const f = (id, ph, ac) => `<input type="password" id="${id}" placeholder="${tr(ph)}" autocomplete="${ac}">`;
  pop.innerHTML = `<div class="card"><h2>${tr(T[0])}</h2><p class="hint">${tr(T[1])}</p>
    ${mode === "on" ? f("cp1", "Пароль", "new-password") + f("cp2", "Ещё раз", "new-password") + `<label class="ulrem"><input type="checkbox" id="cprem" checked> ${tr("Помнить на этом компьютере")}</label>` : ""}
    ${mode === "off" ? f("cp1", "Пароль", "current-password") : ""}
    ${mode === "password" ? f("cp0", "Старый пароль", "current-password") + f("cp1", "Новый пароль", "new-password") + f("cp2", "Ещё раз", "new-password") : ""}
    <div class="ulerr" id="cperr"></div>
    <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn l" data-x>${tr("Отмена")}</button><button class="btn" data-ok>${tr(T[2])}</button></div></div>`;
  document.body.appendChild(pop);
  const err = (t) => ($("#cperr", pop).textContent = tr(t));
  $("[data-x]", pop).onclick = () => pop.remove();
  $("[data-ok]", pop).onclick = async () => {
    const v = (id) => ($("#" + id, pop) || {}).value || "";
    if (mode !== "off" && v("cp1").length < 8) return err("Пароль — не короче 8 знаков");
    if (mode !== "off" && v("cp1") !== v("cp2")) return err("Пароли не совпадают");
    const ok = $("[data-ok]", pop);
    ok.disabled = true;
    ok.textContent = tr(mode === "password" ? "Меняю…" : mode === "on" ? "Шифрую…" : "Расшифровываю…");
    try {
      const body =
        mode === "on"
          ? { action: "on", password: v("cp1"), remember: $("#cprem", pop).checked }
          : mode === "off"
            ? { action: "off", password: v("cp1") }
            : { action: "password", old: v("cp0"), new: v("cp1") };
      const d = await post("/api/crypto", body);
      pop.remove();
      toast(
        mode === "on"
          ? tr("Память зашифрована") + ` (${d.files})`
          : mode === "off"
            ? tr("Шифрование снято")
            : tr("Пароль сменён"),
      );
      done && done();
    } catch (e) {
      err(e.message);
      ok.disabled = false;
      ok.textContent = tr(T[2]);
    }
  };
  setTimeout(() => ($("#cp0", pop) || $("#cp1", pop)).focus(), 50);
}
