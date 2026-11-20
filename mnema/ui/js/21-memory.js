// ---------------------------------------------------------------- memory
async function viewMemory(tab) {
  if (!MEM.on && !MEM.peek) {
    $("#view").innerHTML =
      `<div class="page"><div class="wrap"><div class="memoff">${ic("eyeoff")}<h1>${tr("Память выключена")}</h1>
      <p>${tr("Сейчас Mnemai — обычный чат с любым ИИ: ничего о тебе не знает и ничего не запоминает. Консорциум, документы, действия с файлами, встречи и локальные модели работают.")}</p>
      <p>${tr("С памятью ИИ знают, кто ты, над чем работаешь и как тебе отвечать, а Mnemai учится по ходу разговора. Всё хранится у тебя на компьютере обычными файлами.")}</p>
      <div class="row" style="justify-content:center"><button class="btn" data-memon>${tr("Включить память")}</button><button class="btn g" id="mempeek">${tr("Посмотреть записанное")}</button></div></div></div></div>`;
    $("#mempeek").onclick = () => {
      MEM.peek = true;
      viewMemory(tab);
    };
    return;
  }
  tab = ["portrait", "history", "files"].includes(tab) ? tab : "portrait";
  $("#view").innerHTML =
    `<div class="page"><div class="wrap">${APP.demo ? demoBar() : ""}<h1>Что я о тебе знаю</h1><p class="sub">Всё лежит у тебя на компьютере обычными файлами — <a href="#" id="openf2" style="color:var(--acc)">открыть папку</a>. Нажми «выучено» — покажу, откуда я это знаю.</p>
   <div class="tabs">${[
     ["portrait", "Портрет"],
     ["history", "История"],
     ["files", "Файлы"],
   ]
     .map(
       ([k, l, n]) => `<button data-t="${k}" class="${k === tab ? "on" : ""}">${l}${n ? `<em>${n}</em>` : ""}</button>`,
     )
     .join("")}</div><div id="mt"></div></div></div>`;
  $$("[data-t]").forEach((b) => (b.onclick = () => viewMemory(b.dataset.t)));
  bindDemo();
  $("#openf2").onclick = (e) => {
    e.preventDefault();
    post("/api/memory/open");
  };
  await { portrait: memPortrait, history: memHistory, files: memFiles }[tab]();
}
function demoBar() {
  return `<div class="demo"><span>Это демо-память выдуманного Ивана. Обучение здесь выключено, твой компьютер не читается.</span>${APP.desktop ? '<button class="btn" id="mine">Завести свою память</button>' : ""}</div>`;
}
function bindDemo() {
  if ($("#mine")) $("#mine").onclick = () => api("/api/app/switch");
}
const noteGet = (rel) => api("/api/note?rel=" + encodeURIComponent(rel));
const raw = async (rel) => (await noteGet(rel)).raw || "";
// the editor sends the version it opened: a file Mnemai changed meanwhile is not overwritten (the server says 409)
async function noteSave(rel, text, base) {
  try {
    await post("/api/note", { rel, raw: text, base });
    toast(tr("Сохранено"));
    return true;
  } catch (e) {
    toast(e.message, 6000);
    return false;
  }
}
function bullets(text) {
  return text
    .split("\n")
    .filter((l) => /^\s*- /.test(l))
    .map((l) => l.replace(/^\s*- /, ""));
}
function factLi(t) {
  const learned = /· выучено/.test(t);
  const clean = t.replace(/\s*· выучено/, "");
  return `<li><span>${inline(clean)}</span>${learned ? `<span class="learned" data-why="${esc(clean)}">выучено · откуда?</span>` : ""}</li>`;
}
function sections(text) {
  const out = [];
  out.intro = [];
  let cur = null;
  text
    .replace(/^---[\s\S]*?\n---\n/, "")
    .split("\n")
    .forEach((l) => {
      const h = l.match(/^#{2,3}\s+(.*)/);
      if (h) {
        cur = { h: h[1], lines: [] };
        out.push(cur);
      } else if (l.startsWith("# ")) return;
      else if (cur && l.trim()) cur.lines.push(l.replace(/^\s*- /, ""));
      else if (!cur && l.trim()) out.intro.push(l.replace(/^\s*- /, ""));
    });
  return out;
}
const PROFILE_STUB = /^Кто я в двух-трёх фразах/;
async function editNote(rel, back) {
  const got = await noteGet(rel),
    t = got.raw || "";
  $("#mt").innerHTML =
    `<div class="card editor"><h2 data-noi18n>${esc(rel)}<button class="btn g sm" id="bk">${tr("Назад")}</button></h2><textarea id="ed">${esc(t)}</textarea><div class="row" style="margin-top:10px"><button class="btn" id="sv">${tr("Сохранить")}</button><span class="hint">${tr("Правка попадёт в историю, её можно откатить.")}</span></div></div>`;
  $("#bk").onclick = back;
  $("#sv").onclick = async () => {
    if (await noteSave(rel, $("#ed").value, got.hash)) back();
  };
}
async function tellAboutMe() {
  location.hash = "chat";
  await new Promise((r) => setTimeout(r, 350));
  if (CHAT.id) await viewChat();
  const i = $("#inp");
  if (i) {
    i.value = tr("Расскажу о себе: ");
    i.focus();
  }
}
async function memPortrait() {
  const [me, rules, evn, projects, people, cardl, ag, ms] = await Promise.all([
    raw("70 Memory/Profile.md"),
    raw("70 Memory/Rules.md"),
    api("/api/notes?scope=decisions"),
    api("/api/notes?scope=projects"),
    api("/api/notes?scope=people"),
    api("/api/notes?scope=cards"),
    api("/api/agent").catch(() => ({ profile: {} })),
    api("/api/memory/status").catch(() => ({})),
  ]);
  const dec = (
    await Promise.all(
      evn
        .map((n) => n.rel)
        .sort()
        .reverse()
        .slice(0, 2)
        .map(raw),
    )
  ).join("\n");
  const cards = await Promise.all(cardl.map(async (n) => ({ ...n, raw: await raw(n.rel) })));
  const secs = sections(me);
  const hid = (h) => /#(money|health|private)/.test(h);
  const name = ((ag.profile || {}).owner_name || "").trim(),
    intro = secs.intro.filter((l) => !PROFILE_STUB.test(l) && !l.startsWith(">"));
  // headings of the starting memory read in the owner's language; his own headings stay as written
  const youH = (h) => {
    const y = h
      .replace(/\s*#\w+/g, "")
      .replace(/со мной/gi, "с тобой")
      .replace(/^Обо мне$/i, "О тебе")
      .replace(/^Мне /, "Тебе ");
    return y === "Как с тобой говорить" ? tr("Как с тобой говорить") : tr(y);
  };
  const all = [...secs.flatMap((x) => x.lines), ...bullets(rules), ...cards.flatMap((c) => bullets(c.raw))],
    learned = all.filter((l) => /· выучено/.test(l)).length;
  // facts about him are there, the portrait is not: build it now (learning also does it after each write)
  const openFacts = secs.filter((x) => !hid(x.h) && !/говорить|стиль/i.test(x.h)).flatMap((x) => x.lines).length;
  const building = !intro.length && openFacts >= 3 && !window.__portraitTry;
  if (building) {
    window.__portraitTry = 1;
    post("/api/portrait/refresh", {})
      .then((r) => r.written && $("[data-t=portrait].on") && memPortrait())
      .catch(() => {});
  }
  const prof = (k) => /говорить/i.test(k);
  const merged = [];
  secs
    .filter((x) => x.lines.length)
    .forEach((x) => {
      const t = youH(x.h),
        m = merged.find((y) => y.t === t);
      if (m) {
        m.lines = [...m.lines, ...x.lines];
        m.hid = m.hid || hid(x.h);
      } else merged.push({ t, h: x.h, lines: [...x.lines], hid: hid(x.h) });
    });
  const profTopics = merged.map((x) => ({
    title: x.t,
    icon: prof(x.h) ? "chat" : "user",
    color: prof(x.h) ? "#0ea5e9" : "#6366f1",
    hidden: x.hid,
    items: x.lines,
    edit: "70 Memory/Profile.md",
    what: prof(x.h) ? tr("Тон, длина ответов, обращение") : tr("Из твоего портрета"),
  }));
  const topics = [
    {
      title: tr("Правила для ИИ"),
      icon: "list",
      color: "#f59e0b",
      items: bullets(rules),
      edit: "70 Memory/Rules.md",
      what: tr("Что ИИ должен и чего не должен делать с тобой. Твои поправки в разговорах становятся правилами."),
      empty: tr("Правил пока нет."),
    },
    {
      title: tr("Проекты"),
      icon: "folder",
      color: "#10b981",
      chips: projects.filter((p) => p.status !== "archive").map((p) => [p.title, p.status || ""]),
      tell: true,
      what: tr("Над чем ты работаешь. Mnemai заводит проект сама, когда ты о нём рассказываешь."),
      empty: tr("Пока нет. Упомяни в чате, над чем работаешь."),
    },
    {
      title: tr("Люди вокруг тебя"),
      icon: "users",
      color: "#ec4899",
      chips: people.map((p) => [p.title, ""]),
      tell: true,
      what: tr("Коллеги, близкие, клиенты — кто есть кто, чтобы ИИ не переспрашивал."),
      empty: tr("Пока нет. Появятся, когда расскажешь о ком-то."),
    },
    ...profTopics,
    ...cards.map((c, i) => ({
      title: c.title,
      icon: "cards",
      color: MT_COLORS[i % MT_COLORS.length],
      hidden: /\ntags:\s*\[/.test(c.raw),
      items: bullets(c.raw),
      edit: c.rel,
      what: tr("Тема, о которой Mnemai собирает факты."),
    })),
    {
      title: tr("События и решения"),
      icon: "pin",
      color: "#0284c7",
      items: bullets(dec),
      what: tr("Что ты решил и когда — чтобы ИИ не предлагал то, от чего ты уже отказался."),
      empty: tr("Пока нет. Скажи «решил…» в чате — запишу."),
    },
  ];
  const head = topics.filter((t) => [tr("Правила для ИИ"), tr("Проекты"), tr("Люди вокруг тебя")].includes(t.title));
  const rest = topics.filter((t) => !head.includes(t));
  const byCount = (a, b) => topicCount(b) - topicCount(a);
  topics.splice(
    0,
    topics.length,
    ...head,
    ...rest.filter((t) => profTopics.includes(t)),
    ...rest.filter((t) => !profTopics.includes(t) && t.title !== tr("События и решения")).sort(byCount),
    ...rest.filter((t) => t.title === tr("События и решения")),
  );
  window.__topics = topics;
  $("#mt").innerHTML =
    `<div class="card phero"><div class="pav">${esc((name || "?").slice(0, 1).toUpperCase())}</div><div class="pbody">
      <div class="pname" data-noi18n>${esc(name || tr("Ты"))}</div>
      <div class="pabout">${tr("Это твой портрет. Mnemai подставляет его каждому ИИ, с которым ты говоришь, — чтобы тот сразу знал, кто ты и как с тобой работать.")}</div>
      ${intro.length ? `<div class="who">${intro.map(inline).join("<br>")}</div>` : building ? `<div class="pnone pbuild">${tr("Собираю портрет из того, что уже знаю о тебе…")}</div>` : `<div class="pnone">${tr("Пока Mnemai почти ничего о тебе не знает. Портрет заполнится сам по ходу разговоров — или пройди «Знакомство»: пара минут, и она будет знать главное.")}</div>`}
      <div class="pstats"><span>${ic("book")}<b data-count="${all.length}">0</b> ${tr("фактов")}</span><span>${ic("check")}<b data-count="${learned}">0</b> ${tr("выучено само")}</span>${ms.updated ? `<span>${ic("redo")}${tr("обновлено")} ${ago(ms.updated)}</span>` : ""}</div>
      <div class="pacts">${[
        ["data-int", "👋", "#6366f1", "#a855f7", "Знакомство", "пара минут вопросов"],
        ["data-quiz", "🎯", "#10b981", "#14b8a6", "Насколько Mnemai меня знает", "проверь её на себе"],
        ["data-cmp", "🔍", "#0ea5e9", "#6366f1", "С памятью и без", "один вопрос, два ответа"],
        ["data-tell", "💬", "#f59e0b", "#f97316", "Рассказать о себе", "своими словами"],
        ['data-edit="70 Memory/Profile.md"', "✏️", "#ec4899", "#a855f7", "Поправить самому", "открыть портрет"],
      ]
        .map(
          ([a, em, c1, c2, t, s], n) =>
            `<button class="pact" ${a} style="--c1:${c1};--c2:${c2};--d:${n * 0.05}s"><span class="medal2"><span>${em}</span></span><span class="xftx"><b>${tr(t)}</b><small>${tr(s)}</small></span></button>`,
        )
        .join("")}</div></div></div>
   ${memMap(topics, name)}
   <div class="mtiles">${topics.map(topicTile).join("")}</div>`;
  $$("[data-tell]").forEach((b) => (b.onclick = tellAboutMe));
  $$("[data-int]").forEach((b) => (b.onclick = interviewView));
  $$("[data-quiz]").forEach((b) => (b.onclick = quizView));
  $$("[data-cmp]").forEach((b) => (b.onclick = () => compareView()));
  $$("[data-edit]").forEach((b) => (b.onclick = () => editNote(b.dataset.edit, () => viewMemory("portrait"))));
  bindWhy();
  bindRules();
  countUp($("#mt"));
  $$("[data-topic]").forEach((b) => (b.onclick = () => topicModal(window.__topics[+b.dataset.topic])));
}
// rules for the AI: a compact two-column list, one line per rule, newest first; a click opens the full text
function ruleParts(t) {
  const learned = /· выучено/.test(t);
  let text = t.replace(/\s*· выучено/, "").trim();
  const m = text.match(/\s*\((?:статус\s+)?(\d{2})\.(\d{2})\.(\d{4})\)\s*$/);
  if (m) text = text.slice(0, m.index).trim();
  return {
    text,
    learned,
    day: m ? `${m[1]}.${m[2]}` : "",
    key: m ? m[3] + m[2] + m[1] : "",
    raw: t.replace(/\s*· выучено/, ""),
  };
}
// the same compact rows for a topic card: one column, one line per fact, newest first, a click opens the full text
const rowsSorted = (list) =>
  list
    .map(ruleParts)
    .map((r, i) => ({ ...r, i }))
    .sort((a, b) => (b.key || "99999999").localeCompare(a.key || "99999999") || a.i - b.i);
const rowLi = (r) =>
  `<li data-rl title="${esc(r.text)}"><i class="rld${r.learned ? "" : " own"}"></i><span class="rlt">${inline(r.text)}</span>${r.day ? `<time>${r.day}</time>` : ""}${r.learned ? `<span class="rlwhy" data-why="${esc(r.raw)}">${tr("откуда?")}</span>` : ""}</li>`;
function factRows(list) {
  const rows = rowsSorted(list);
  return `<ol class="rlist one${rows.length > 8 ? " long" : ""}">${rows.map(rowLi).join("")}</ol>`;
}
function rulesCard(list) {
  const rows = rowsSorted(list);
  const own = rows.filter((r) => !r.learned).length;
  const body = rows.length
    ? `<div class="rlbar">${rows.length > 6 ? `<label class="rlq">${ic("search")}<input id="rlq" placeholder="${tr("Найти правило")}"></label>` : ""}<span class="rlsum"><i class="rld"></i>${rows.length - own} ${tr("выучено само")}<i class="rld own"></i>${own} ${tr("твоих")}</span></div>
      <ol class="rlist${rows.length > 14 ? " long" : ""}">${rows.map(rowLi).join("")}</ol><div class="rlnone" hidden>${tr("Ничего не нашлось")}</div>`
    : "";
  return `<div class="card pcard rcard"><div class="pch"><h2>${tr("Правила для ИИ")} <span class="hint">${rows.length}</span></h2><button class="ib" data-edit="70 Memory/Rules.md" title="${tr("Поправить")}">${ic("edit")}</button></div><p class="pwhat">${tr("Что ИИ должен и чего не должен делать с тобой. Твои поправки в разговорах становятся правилами.")}</p>${body || `<div class="pempty">${tr("Правил пока нет.")}</div>`}</div>`;
}
function bindRules() {
  $$(".rlist").forEach((ol) =>
    $$("[data-rl]", ol).forEach(
      (li) =>
        (li.onclick = (e) => {
          if (e.target.closest("[data-why]")) return;
          if (!ol.style.height) {
            ol.style.height = ol.offsetHeight + "px"; // the card keeps its height: the opened fact scrolls inside
            ol.style.overflow = "auto";
          }
          const open = li.classList.contains("open");
          $$("[data-rl].open", ol).forEach((x) => x.classList.remove("open"));
          if (!open) li.classList.add("open");
        }),
    ),
  );
  const box = $(".rcard");
  if (!box) return;
  const q = $("#rlq", box);
  if (q)
    q.oninput = () => {
      const v = q.value.trim().toLowerCase();
      let n = 0;
      $$("[data-rl]", box).forEach((li) => {
        const hit = !v || li.title.toLowerCase().includes(v);
        li.hidden = !hit;
        n += hit;
      });
      $(".rlnone", box).hidden = !!n;
    };
}
function bindWhy() {
  $$("[data-why]").forEach(
    (x) =>
      (x.onclick = async () =>
        showWhy(await api("/api/memory/why?text=" + encodeURIComponent(x.dataset.why)), x.dataset.why)),
  );
}
function showWhy(d, text) {
  const pop = document.createElement("div");
  pop.className = "modal";
  pop.innerHTML = `<div class="card"><h2>Откуда я это знаю</h2><div style="font-weight:600">${esc(d.text || text)}</div>${d.found ? `<div class="kv"><span>Откуда</span><div>${esc((d.source_names || []).join(", "))}</div><span>Встретилось</span><div>${d.count} раз · уверенность ${Math.round(d.confidence * 100)}%</div><span>Впервые</span><div>${esc((d.first_seen || "").replace("T", " ").slice(0, 16))}</div><span>Почему так решила</span><div>${esc(d.why || (d.decided_by === "owner" ? "ты подтвердил" : "—"))}</div>${(d.evidence || []).length ? `<span>Твои слова</span><div>${d.evidence.map((e) => `<div style="border-left:2px solid var(--line);padding-left:8px;margin-bottom:4px;color:var(--ink2)">${inline(e)}</div>`).join("")}</div>` : ""}</div>` : '<p class="hint">Записано вручную или до обучения.</p>'}
  <div class="row">${d.found ? `<button class="btn l" data-a="edit">Поправить</button><button class="btn l" data-a="forget">Забыть</button>` : ""}<button class="btn g" data-a="close">Закрыть</button></div></div>`;
  document.body.appendChild(pop);
  pop.onclick = (e) => {
    if (e.target === pop) pop.remove();
  };
  $$("[data-a]", pop).forEach(
    (b) =>
      (b.onclick = async () => {
        const a = b.dataset.a;
        if (a === "close") return pop.remove();
        const body = { id: d.id, action: a };
        if (a === "edit") {
          const v = await askText("Как правильно?", d.text);
          if (!v) return;
          body.text = v;
        }
        await post("/api/learn/review", body);
        pop.remove();
        toast(a === "forget" ? "Забыла" : "Поправила");
        viewMemory("portrait");
      }),
  );
}
const KIND = {
  fact: "факт",
  rule: "правило",
  decision: "решение",
  project: "проект",
  person: "человек",
  preference: "предпочтение",
};
async function memHistory() {
  const [evs, cl, sv] = await Promise.all([
    api("/api/journal?limit=150"),
    api("/api/clients"),
    api("/api/saves").catch(() => ({ saves: [] })),
  ]);
  const undone = new Set(evs.filter((e) => e.undoes).map((e) => e.undoes));
  const who = (id) =>
      id === "learner" ? "Обучение" : id === "owner" ? "Ты" : (cl.find((c) => c.id === id) || { name: id }).name,
    ACT = {
      read: "прочитал",
      write: "записал",
      undo: "откатил",
      learn: "обучение",
    };
  const saves = (sv.saves || []).length
    ? `<div class="card"><h2>Сейвы дня («95 Saves»)</h2><p class="hint">Копии заметок до первой правки дня — можно вернуть заметку к утренней версии.</p>${sv.saves
        .map(
          (s) =>
            `<div class="jr"><b data-noi18n>${esc(s.name)}</b><span class="hint" data-noi18n>${esc(s.path)}</span><button class="btn g sm" data-sv="${esc(s.path)}">восстановить</button></div>`,
        )
        .join("")}</div>`
    : "";
  $("#mt").innerHTML =
    `<div class="card">${evs.map((e) => `<div class="jr"><span>${esc(e.ts.slice(5, 16).replace("T", " "))}</span><b>${esc(who(e.client))}</b><div><span class="hint">${esc(ACT[e.action] || e.action)}</span> ${esc(e.summary)}</div>${e.action === "write" && !undone.has(e.id) ? `<button class="btn l sm" data-u="${esc(e.id)}">откатить</button>` : "<span></span>"}</div>`).join("") || "Пока пусто."}</div>` +
    saves;
  $$("[data-u]").forEach(
    (b) =>
      (b.onclick = async () => {
        try {
          await post("/api/undo", { id: b.dataset.u });
          toast("Откатила");
          memHistory();
        } catch (e) {
          toast(e.message);
        }
      }),
  );
  $$("[data-sv]").forEach(
    (b) =>
      (b.onclick = async () => {
        try {
          await post("/api/saves/restore", { path: b.dataset.sv });
          toast("Восстановила из сейва");
          memHistory();
        } catch (e) {
          toast(e.message);
        }
      }),
  );
}
async function memFiles() {
  const all = (await api("/api/notes")).sort((a, b) => a.rel.localeCompare(b.rel));
  const groups = {};
  all.forEach((n) => {
    const top = n.rel.split("/")[0];
    (groups[top] = groups[top] || []).push(n);
  });
  $("#mt").innerHTML = Object.entries(groups)
    .map(
      ([top, ns]) =>
        `<div class="card files"><h2 data-noi18n>${esc(top.replace(/\.md$/, ""))}</h2>${ns.map((n) => `<a data-r="${esc(n.rel)}"><span>${esc(n.title)}</span><span class="hint" data-noi18n>${esc(n.rel.split("/").slice(1).join("/") || n.rel)}</span></a>`).join("")}</div>`,
    )
    .join("");
  $$("[data-r]").forEach(
    (a) =>
      (a.onclick = async () => {
        const r = a.dataset.r,
          got = await noteGet(r),
          t = got.raw || "";
        $("#mt").innerHTML =
          `<div class="card editor"><h2>${esc(r)}<button class="btn g sm" id="bk">Назад</button></h2><textarea id="ed">${esc(t)}</textarea><div class="row" style="margin-top:10px"><button class="btn" id="sv">Сохранить</button><span class="hint">Правка попадёт в историю, её можно откатить.</span></div></div>`;
        $("#bk").onclick = memFiles;
        $("#sv").onclick = async () => {
          if (await noteSave(r, $("#ed").value, got.hash)) got.hash = (await noteGet(r)).hash;
        };
      }),
  );
}

// ---------------------------------------------------------------- memory page: a live map of topics, tiles, every topic opens in a window
const MT_COLORS = [
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
  "#22c55e",
  "#e11d48",
  "#3b82f6",
  "#a855f7",
  "#14b8a6",
  "#eab308",
  "#64748b",
];
const daysAgoKey = (n) => {
  const d = new Date(Date.now() - n * 864e5);
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
};
function topicCount(t) {
  return t.chips ? t.chips.length : t.items.length;
}
function topicFresh(t) {
  if (t.chips) return false;
  const since = daysAgoKey(3);
  return t.items.some((l) => (ruleParts(l).key || "") >= since);
}
// bubbles around the owner: start on an ellipse, then push apart and pull to the centre until nothing overlaps
function mapLayout(topics, W, H) {
  const max = Math.max(1, ...topics.map(topicCount));
  const cx = W / 2,
    cy = H / 2,
    core = 40,
    n = topics.length;
  const shrink = n > 30 ? 0.85 : 1;
  const bs = topics.map((t, i) => {
    const r = (19 + 34 * Math.sqrt(topicCount(t) / max)) * shrink,
      a = (i / n) * Math.PI * 2 + 0.3;
    return {
      t,
      i,
      r,
      x: cx + Math.cos(a) * W * 0.42,
      y: cy + Math.sin(a) * H * 0.36,
    };
  });
  // all the bubbles together take at most ~38% of the box: then they have room not to cover each other
  const area = bs.reduce((s, b) => s + Math.PI * b.r * b.r, 0),
    room = 0.38 * W * H;
  if (area > room) bs.forEach((b) => (b.r = Math.max(14, b.r * Math.sqrt(room / area))));
  for (let it = 0; it < 400; it++) {
    for (const b of bs) {
      b.x += (cx - b.x) * 0.0035;
      b.y += (cy - b.y) * 0.03;
    }
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const p = bs[i],
          q = bs[j],
          dx = q.x - p.x,
          dy = q.y - p.y,
          d = Math.hypot(dx, dy) || 0.01,
          need = p.r + q.r + 8;
        if (d < need) {
          const k = (need - d) / d / 2;
          p.x -= dx * k;
          p.y -= dy * k;
          q.x += dx * k;
          q.y += dy * k;
        }
      }
    for (const b of bs) {
      const dx = b.x - cx,
        dy = b.y - cy,
        d = Math.hypot(dx, dy) || 0.01,
        need = core + b.r + 12;
      if (d < need) {
        b.x = cx + (dx / d) * need;
        b.y = cy + (dy / d) * need;
      }
      b.x = Math.min(W - b.r - 6, Math.max(b.r + 6, b.x));
      b.y = Math.min(H - b.r - 6, Math.max(b.r + 6, b.y));
    }
  }
  return bs;
}
const MAP_MAX = 16; // the biggest topics on the map; all of them are in the tiles below
function memMap(topics, name) {
  const W = 860,
    H = 300;
  topics.forEach((t, i) => (t.__i = i));
  const shown =
    topics.length > MAP_MAX ? [...topics].sort((a, b) => topicCount(b) - topicCount(a)).slice(0, MAP_MAX) : topics;
  const rest = topics.length - shown.length;
  const pl = mapLayout(shown, W, H);
  const lines = pl
    .map(
      (p, k) =>
        `<line x1="${W / 2}" y1="${H / 2}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}" style="--c:${p.t.color};--k:${k}"/>`,
    )
    .join("");
  const bubbles = pl
    .map((p, k) => {
      const n = topicCount(p.t),
        big = p.r >= 33;
      return `<button class="mbub ${topicFresh(p.t) ? "fresh" : ""} ${p.t.hidden ? "hid" : ""}" data-topic="${p.t.__i}" title="${esc(p.t.title)} · ${n}" style="--x:${((p.x / W) * 100).toFixed(2)}%;--y:${((p.y / H) * 100).toFixed(2)}%;--r:${(p.r * 2).toFixed(0)}px;--c:${p.t.color};--k:${k};--f:${(k % 5) * 0.6}s"><b>${n}</b>${big ? `<span>${esc(p.t.title)}</span>` : `<span class="sm">${esc(p.t.title)}</span>`}${p.t.hidden ? `<i class="mlock">${ic("lock")}</i>` : ""}</button>`;
    })
    .join("");
  return `<div class="card mmap"><div class="mmh"><h2>${tr("Карта памяти")}</h2><span class="hint">${tr("размер — сколько фактов, пульсирует — обновлено за 3 дня, замок — видят не все ИИ")}${rest > 0 ? ` · ${tr("ещё тем ниже")}: ${rest}` : ""}</span></div>
    <div class="mmbox"><svg class="mmlines" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${lines}</svg><div class="mmcore">${esc((name || "?").slice(0, 1).toUpperCase())}</div>${bubbles}</div></div>`;
}
function topicTile(t, i) {
  const n = topicCount(t);
  const prev = t.chips
    ? `<div class="mtchips">${t.chips
        .slice(0, 5)
        .map((c) => `<em>${esc(c[0])}</em>`)
        .join("")}${n > 5 ? `<em class="more">+${n - 5}</em>` : ""}</div>`
    : `<ul class="mtprev">${rowsSorted(t.items)
        .slice(0, 2)
        .map((r) => `<li><i style="background:${t.color}"></i><span>${inline(r.text)}</span></li>`)
        .join("")}</ul>`;
  return `<button class="mtile ${topicFresh(t) ? "fresh" : ""}" data-topic="${i}" style="--c:${t.color};--d:${(i % 12) * 0.04}s">
    <div class="mth"><span class="mtic">${ic(t.icon)}</span><b>${esc(t.title)}</b>${t.hidden ? `<span class="mtlock" title="${tr("видят только те ИИ, кому разрешено")}">${ic("lock")}</span>` : ""}<em class="mtn">${n}</em></div>
    ${n ? prev : `<p class="mtempty">${esc(t.empty || tr("пусто"))}</p>`}
    <span class="mtall">${n ? `${tr("Все")} ${n} →` : tr("Открыть →")}</span></button>`;
}
function topicModal(t) {
  const pop = document.createElement("div");
  pop.className = "modal mtopic";
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
  const n = topicCount(t);
  const rows = t.chips ? [] : rowsSorted(t.items);
  const own = rows.filter((r) => !r.learned).length;
  const body = t.chips
    ? `<div class="mtcl">${t.chips.map((c) => `<span class="pill">${esc(c[0])}${c[1] ? ` <small>${esc(c[1])}</small>` : ""}</span>`).join("")}</div>`
    : `<ol class="rlist one mtlist">${rows.map(rowLi).join("")}</ol><div class="rlnone" hidden>${tr("Ничего не нашлось")}</div>`;
  pop.innerHTML = `<div class="card mtc2" style="--c:${t.color}"><div class="mtmh"><span class="mtic big">${ic(t.icon)}</span><div><h2>${esc(t.title)} <span class="hint">${n}</span></h2><small>${esc(t.what || "")}${t.hidden ? ` · ${tr("видят только те ИИ, кому разрешено")}` : ""}</small></div>${t.edit ? `<button class="ib" data-medit title="${tr("Поправить")}">${ic("edit")}</button>` : ""}${t.tell ? `<button class="btn g sm" data-mtell>${ic("chat")}${tr("Рассказать")}</button>` : ""}<button class="lmx" data-x>×</button></div>
    ${!t.chips && n > 8 ? `<div class="rlbar"><label class="rlq">${ic("search")}<input id="mtq" placeholder="${tr("Найти")}"></label>${rows.length ? `<span class="rlsum"><i class="rld"></i>${rows.length - own} ${tr("выучено само")}<i class="rld own"></i>${own} ${tr("твоих")}</span>` : ""}</div>` : ""}
    ${n ? body : `<div class="pempty">${esc(t.empty || tr("пусто"))}</div>`}</div>`;
  $$("[data-x]", pop).forEach((b) => (b.onclick = close));
  if ($("[data-medit]", pop))
    $("[data-medit]", pop).onclick = () => {
      close();
      editNote(t.edit, () => viewMemory("portrait"));
    };
  if ($("[data-mtell]", pop))
    $("[data-mtell]", pop).onclick = () => {
      close();
      tellAboutMe();
    };
  $$("[data-rl]", pop).forEach(
    (li) =>
      (li.onclick = (e) => {
        if (e.target.closest("[data-why]")) return;
        const open = li.classList.contains("open");
        $$("[data-rl].open", pop).forEach((x) => x.classList.remove("open"));
        if (!open) li.classList.add("open");
      }),
  );
  bindWhy();
  const q = $("#mtq", pop);
  if (q) {
    q.focus();
    q.oninput = () => {
      const v = q.value.trim().toLowerCase();
      let k = 0;
      $$("[data-rl]", pop).forEach((li) => {
        const hit = !v || li.title.toLowerCase().includes(v);
        li.hidden = !hit;
        k += hit;
      });
      $(".rlnone", pop).hidden = !!k;
    };
  }
}
// the numbers in the portrait run up from zero
function countUp(root) {
  $$("[data-count]", root).forEach((el) => {
    const to = +el.dataset.count,
      t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / 900);
      el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}
