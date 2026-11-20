// Things to try and to show: «Поделиться карточкой», «С памятью и без», «Насколько Mnemai тебя знает», «Знакомство»,
// «Прожарка». A card is a picture with the result, Mnemai's mark and the link — no memory goes into it by itself.
const SHARE_URL = "github.com/Pumpetee/Mnemai";

function cardWrap(x, text, maxW, maxLines) {
  const words = String(text || "")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ");
  const out = [];
  let line = "";
  for (const w of words) {
    const t = line ? line + " " + w : w;
    if (x.measureText(t).width <= maxW) line = t;
    else {
      if (line) out.push(line);
      line = w;
      if (out.length === maxLines) break;
    }
  }
  if (line && out.length < maxLines) out.push(line);
  if (out.length === maxLines && words.join(" ").length > out.join(" ").length) {
    let l = out[maxLines - 1];
    while (l && x.measureText(l + "…").width > maxW) l = l.slice(0, -1);
    out[maxLines - 1] = l.replace(/[\s,.;:—-]+$/, "") + "…";
  }
  return out;
}
function cardCanvas({ kind = "", title = "", big = "", sub = "", lines = [] }) {
  const W = 1200,
    H = 630,
    c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const x = c.getContext("2d"),
    font = getComputedStyle(document.body).fontFamily || "system-ui, sans-serif";
  const bg = x.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#121027");
  bg.addColorStop(1, "#2b1d63");
  x.fillStyle = bg;
  x.fillRect(0, 0, W, H);
  const glow = x.createRadialGradient(W * 0.86, 40, 10, W * 0.86, 40, 560);
  glow.addColorStop(0, "rgba(139,92,246,.5)");
  glow.addColorStop(1, "rgba(139,92,246,0)");
  x.fillStyle = glow;
  x.fillRect(0, 0, W, H);
  // the mark
  const lg = x.createLinearGradient(64, 56, 120, 112);
  lg.addColorStop(0, "#6366f1");
  lg.addColorStop(1, "#8b5cf6");
  x.fillStyle = lg;
  x.beginPath();
  x.roundRect(64, 56, 56, 56, 15);
  x.fill();
  x.fillStyle = "#fff";
  x.font = `800 32px ${font}`;
  x.textAlign = "center";
  x.textBaseline = "middle";
  x.fillText("M", 92, 86);
  x.textAlign = "left";
  x.textBaseline = "alphabetic";
  x.font = `800 30px ${font}`;
  x.fillText("Mnemai", 136, 96);
  if (kind) {
    x.font = `700 20px ${font}`;
    x.fillStyle = "#c4b5fd";
    x.textAlign = "right";
    x.fillText(kind.toUpperCase(), W - 64, 92);
    x.textAlign = "left";
  }
  let y = 190;
  if (big) {
    x.font = `800 130px ${font}`;
    const tg = x.createLinearGradient(64, 140, 64 + x.measureText(big).width, 270);
    tg.addColorStop(0, "#ffffff");
    tg.addColorStop(1, "#c4b5fd");
    x.fillStyle = tg;
    x.fillText(big, 60, 270);
    y = 340;
  }
  x.fillStyle = "#ffffff";
  x.font = `800 ${big ? 44 : 52}px ${font}`;
  for (const l of cardWrap(x, title, W - 128, 2)) {
    x.fillText(l, 64, y);
    y += big ? 54 : 64;
  }
  if (sub) {
    x.font = `500 26px ${font}`;
    x.fillStyle = "#c9cbe0";
    for (const l of cardWrap(x, sub, W - 128, 1)) {
      x.fillText(l, 64, y + 4);
      y += 44;
    }
  }
  x.font = `500 26px ${font}`;
  y += 8;
  const per = lines.length <= 2 && !big ? 2 : 1; // two answers side by side get two lines each
  for (const raw of lines.slice(0, big ? 2 : 4)) {
    if (y > H - 110) break;
    x.fillStyle = "#a78bfa";
    x.beginPath();
    x.arc(72, y - 9, 5, 0, Math.PI * 2);
    x.fill();
    x.fillStyle = "#e6e7f2";
    for (const l of cardWrap(x, raw, W - 150, per)) {
      if (y > H - 110) break;
      x.fillText(l, 92, y);
      y += 36;
    }
    y += 8;
  }
  x.fillStyle = "rgba(255,255,255,.12)";
  x.fillRect(64, H - 92, W - 128, 1);
  x.font = `500 22px ${font}`;
  x.fillStyle = "#a5a8c0";
  x.fillText(tr("Память для любого ИИ · бесплатно, на твоём компьютере"), 64, H - 50);
  x.font = `700 22px ${font}`;
  x.fillStyle = "#e0d9ff";
  x.textAlign = "right";
  x.fillText(SHARE_URL, W - 64, H - 50);
  return c;
}
// the card before it leaves: a look, then copy the picture, save it or copy a post with the link
function shareCard(spec, postText) {
  const c = cardCanvas(spec),
    url = c.toDataURL("image/png");
  const pop = document.createElement("div");
  pop.className = "modal shpop";
  pop.innerHTML = `<div class="card"><button class="lmx" data-x>×</button><h2>${tr("Поделиться")}</h2>
    <img class="shimg" src="${url}" alt="">
    <p class="hint">${tr("Картинка уйдёт ровно такой. Личного в ней только то, что видно здесь.")}</p>
    <div class="row shacts"><button class="btn" data-a="copy">${ic("copy")}${tr("Скопировать картинку")}</button><button class="btn l" data-a="save">${ic("down")}${tr("Сохранить")}</button><button class="btn g" data-a="text">${ic("chat")}${tr("Скопировать текст поста")}</button></div></div>`;
  const close = () => pop.remove();
  pop.onclick = (e) => e.target === pop && close();
  $("[data-x]", pop).onclick = close;
  $("[data-a='copy']", pop).onclick = async () => {
    try {
      const blob = await new Promise((r) => c.toBlob(r, "image/png"));
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
      toast(tr("Картинка в буфере — вставь её в пост или чат"));
    } catch (e) {
      toast(tr("Не получилось скопировать — сохрани картинкой"));
    }
  };
  $("[data-a='save']", pop).onclick = async () => {
    try {
      const r = await post("/api/share/save", {
        png: url,
        name: "Mnemai " + (spec.kind || ""),
      });
      toast(tr("Сохранила") + ": " + r.path);
    } catch (e) {
      toast(e.message);
    }
  };
  $("[data-a='text']", pop).onclick = async () => {
    try {
      await navigator.clipboard.writeText((postText || spec.title || "") + "\n\nhttps://" + SHARE_URL);
      toast(tr("Текст поста скопирован"));
    } catch (e) {
      toast(e.message);
    }
  };
  document.body.appendChild(pop);
}

// ---------------------------------------------------------------- «С памятью и без»
async function compareView(question) {
  const pop = document.createElement("div");
  pop.className = "modal plpop cmppop";
  const q0 = question || tr("Что ты знаешь обо мне? И что мне важнее всего сделать на этой неделе?");
  pop.innerHTML = `<div class="card"><button class="lmx" data-x>×</button><div class="plhead"><span class="plic">${ic("eye")}</span><div><h2>${tr("С памятью и без")}</h2><p class="hint">${tr("Один вопрос — подключённые ИИ отвечают дважды: как обычный чат, ничего о тебе не зная, и через Mnemai, с твоей памятью.")}</p></div></div>
    <div class="cmpq"><input class="inp" id="cmpq" value="${esc(q0)}"><button class="btn" id="cmpgo">${tr("Сравнить")}</button></div>
    <div id="cmpres"></div></div>`;
  const close = () => pop.remove();
  pop.onclick = (e) => e.target === pop && close();
  $("[data-x]", pop).onclick = close;
  document.body.appendChild(pop);
  const go = async () => {
    const res = $("#cmpres", pop),
      btn = $("#cmpgo", pop);
    btn.disabled = true;
    res.innerHTML = `<div class="plwait">${TYPING}<span>${tr("ИИ отвечают дважды — обычно до минуты")}</span></div>`;
    let d;
    try {
      d = await post("/api/compare", { question: $("#cmpq", pop).value });
    } catch (e) {
      res.innerHTML = `<p class="err">${linkSettings(esc(e.message))}</p>`;
      btn.disabled = false;
      return;
    }
    btn.disabled = false;
    res.innerHTML = `<div class="cmpgrid">${d.results
      .map(
        (r) =>
          `<div class="cmpcol"><div class="cmpname"><i style="background:${spkColor(r.ref)}"></i><b data-noi18n>${esc(r.name)}</b></div>${
            r.error
              ? `<p class="err">${linkSettings(esc(r.error))}</p>`
              : `<div class="cmpa plain"><small>${tr("Без памяти")}</small><div class="md">${md(r.plain || "—")}</div></div><div class="cmpa mine"><small>${ic("check")}${tr("С Mnemai")}</small><div class="md">${md(r.mine || "—")}</div></div>`
          }</div>`,
      )
      .join("")}</div>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" id="cmpshare">${tr("Поделиться")}</button></div>`;
    const ok = d.results.find((r) => !r.error && r.plain && r.mine);
    $("#cmpshare", pop).onclick = () =>
      ok
        ? shareCard(
            {
              kind: tr("С памятью и без"),
              title: d.question,
              lines: [
                tr("Без памяти") + ": " + ok.plain.replace(/[#*_`>]/g, ""),
                tr("С Mnemai") + ": " + ok.mine.replace(/[#*_`>]/g, ""),
              ],
              sub: ok.name,
            },
            tr("Спросил ИИ одно и то же дважды: как обычный чат и через Mnemai, с моей памятью. Разница видна сразу."),
          )
        : toast(tr("Нечем делиться: ни один ИИ не ответил"));
  };
  $("#cmpgo", pop).onclick = go;
  $("#cmpq", pop).onkeydown = (e) => e.key === "Enter" && go();
}

// ---------------------------------------------------------------- «Насколько Mnemai тебя знает»
async function quizView() {
  let d;
  try {
    d = await api("/api/quiz");
  } catch (e) {
    return toast(e.message);
  }
  const pop = document.createElement("div");
  pop.className = "modal plpop quizpop";
  const close = () => pop.remove();
  pop.onclick = (e) => e.target === pop && close();
  document.body.appendChild(pop);
  const items = d.items || [];
  if (items.length < 3) {
    pop.innerHTML = `<div class="card"><button class="lmx" data-x>×</button><div class="plhead"><span class="plic">${ic("hint")}</span><div><h2>${tr("Насколько Mnemai тебя знает")}</h2><p class="hint">${tr("Пока Mnemai знает о тебе слишком мало для квиза. Пройди знакомство — пара минут, и будет что проверять.")}</p></div></div>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" id="qzint">${tr("Познакомиться")}</button></div></div>`;
    $("[data-x]", pop).onclick = close;
    $("#qzint", pop).onclick = () => (close(), interviewView());
    return;
  }
  let k = 0,
    yes = 0,
    fixed = 0;
  const draw = () => {
    if (k >= items.length) return done();
    const it = items[k];
    pop.innerHTML = `<div class="card"><button class="lmx" data-x>×</button>
      <div class="qzbar"><span style="width:${(k / items.length) * 100}%"></span></div>
      <div class="qzk">${tr("Факт")} ${k + 1} ${tr("из")} ${items.length}</div>
      <div class="qzfact" data-noi18n>${esc(it.text)}</div>
      <div class="qzwhere">${tr("из заметки")} «<span data-noi18n>${esc(it.title)}</span>»</div>
      <div class="qzacts"><button class="btn qzy" data-v="yes">${ic("check")}${tr("Верно")}</button><button class="btn l" data-v="changed">${ic("edit")}${tr("Уже не так")}</button><button class="btn g qzn" data-v="no">${ic("x")}${tr("Неправда")}</button></div>
      <div class="qzfix" hidden><input class="inp" id="qzt" placeholder="${tr("Как теперь?")}"><button class="btn" id="qzsave">${tr("Сохранить")}</button></div></div>`;
    $("[data-x]", pop).onclick = close;
    const send = async (verdict, text) => {
      try {
        await post("/api/quiz", { id: it.id, verdict, text });
      } catch (e) {
        toast(e.message);
      }
      if (verdict === "yes") yes++;
      else fixed++;
      k++;
      draw();
    };
    $$("[data-v]", pop).forEach(
      (b) =>
        (b.onclick = () => {
          if (b.dataset.v !== "changed") return send(b.dataset.v);
          $(".qzfix", pop).hidden = false;
          const t = $("#qzt", pop);
          t.value = it.text;
          t.focus();
          t.select();
          $("#qzsave", pop).onclick = () => t.value.trim() && send("changed", t.value.trim());
          t.onkeydown = (e) => e.key === "Enter" && t.value.trim() && send("changed", t.value.trim());
        }),
    );
  };
  const done = () => {
    const n = items.length,
      pct = Math.round((yes / n) * 100);
    pop.innerHTML = `<div class="card qzdone"><button class="lmx" data-x>×</button>
      <div class="qzscore">${yes}<small>/${n}</small></div>
      <h2>${tr("Насколько Mnemai тебя знает")}: ${pct}%</h2>
      <p class="hint">${fixed ? tr("Поправлено фактов") + ": " + fixed + ". " + tr("Память теперь точнее — каждый ИИ получит уже исправленное.") : tr("Всё верно — память в порядке.")}</p>
      <div class="row" style="justify-content:center;gap:8px;margin-top:16px"><button class="btn" id="qzsh">${tr("Поделиться")}</button><button class="btn l" id="qzagain">${tr("Ещё раз")}</button><button class="btn g" data-x2>${tr("Закрыть")}</button></div></div>`;
    $("[data-x]", pop).onclick = close;
    $("[data-x2]", pop).onclick = close;
    $("#qzagain", pop).onclick = () => (close(), quizView());
    $("#qzsh", pop).onclick = () =>
      shareCard(
        {
          kind: tr("Квиз"),
          big: `${yes}/${n}`,
          title: `${tr("Насколько Mnemai меня знает")}: ${pct}%`,
          lines: [
            tr("Проверил") + " " + n + " " + tr("фактов из своей памяти"),
            fixed ? tr("Поправил") + " " + fixed + " — " + tr("память стала точнее") : tr("Ни одного промаха"),
          ],
        },
        `${tr("Проверил, насколько Mnemai меня знает")}: ${yes} ${tr("из")} ${n}. ${tr("Одна память для Claude, ChatGPT, Gemini и локальных моделей — и всё на моём компьютере.")}`,
      );
  };
  draw();
}

// ---------------------------------------------------------------- «Знакомство»
async function interviewView() {
  if (!MEM.on) {
    await memSet(true);
    if (!MEM.on) return;
  }
  let d;
  try {
    d = await api("/api/interview");
  } catch (e) {
    return toast(e.message);
  }
  const qs = d.questions,
    ans = {};
  let k = 0;
  const started = Date.now();
  const pop = document.createElement("div");
  pop.className = "modal plpop intpop";
  const close = () => pop.remove();
  document.body.appendChild(pop);
  const draw = () => {
    const q = qs[k],
      lastQ = k === qs.length - 1;
    pop.innerHTML = `<div class="card"><button class="lmx" data-x>×</button>
      <div class="intdots">${qs.map((_, i) => `<i class="${i < k ? "done" : i === k ? "on" : ""}"></i>`).join("")}</div>
      <div class="qzk">${tr("Знакомство")} · ${k + 1} ${tr("из")} ${qs.length}</div>
      <h2 class="intq">${tr(q.q)}</h2>
      <textarea class="inp intta" id="inta" rows="3" placeholder="${tr("например")}: ${esc(tr(q.eg))}"></textarea>
      <div class="row intacts"><button class="btn g" id="intback" ${k ? "" : "disabled"}>${tr("Назад")}</button><span style="flex:1"></span><button class="btn l" id="intskip">${tr("Пропустить")}</button><button class="btn" id="intnext">${lastQ ? tr("Готово") : tr("Дальше")}</button></div></div>`;
    const ta = $("#inta", pop);
    ta.value = ans[q.key] || "";
    ta.focus();
    $("[data-x]", pop).onclick = close;
    const next = (keep) => {
      ans[q.key] = keep ? ta.value.trim() : "";
      if (lastQ) return finish();
      k++;
      draw();
    };
    $("#intnext", pop).onclick = () => next(true);
    $("#intskip", pop).onclick = () => next(false);
    $("#intback", pop).onclick = () => {
      ans[q.key] = ta.value.trim();
      k--;
      draw();
    };
    ta.onkeydown = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        next(true);
      }
    };
  };
  const finish = async () => {
    let r;
    try {
      r = await post("/api/interview", { answers: ans });
    } catch (e) {
      return toast(e.message);
    }
    const mins = Math.max(1, Math.round((Date.now() - started) / 60000));
    pop.innerHTML = `<div class="card qzdone"><button class="lmx" data-x>×</button>
      <div class="qzscore">${r.facts}</div>
      <h2>${tr("фактов о тебе в памяти")}</h2>
      <p class="hint">${tr("Теперь любой ИИ, с которым ты говоришь через Mnemai, знает, кто ты, что сейчас главное и как с тобой говорить. Дальше память пополняется сама.")}</p>
      <div class="row" style="justify-content:center;gap:8px;margin-top:16px;flex-wrap:wrap"><button class="btn" id="intport">${tr("Мой портрет")}</button><button class="btn l" id="intcmp">${tr("С памятью и без")}</button><button class="btn g" id="intsh">${tr("Поделиться")}</button></div></div>`;
    $("[data-x]", pop).onclick = close;
    $("#intport", pop).onclick = () => (close(), go("memory", "portrait"));
    $("#intcmp", pop).onclick = () => (close(), compareView());
    $("#intsh", pop).onclick = () =>
      shareCard(
        {
          kind: tr("Знакомство"),
          big: String(r.facts),
          title: tr("фактов обо мне Mnemai узнала за") + " " + mins + " " + tr("мин"),
          lines: [tr("Теперь Claude, ChatGPT и Gemini знают, кто я и как со мной говорить")],
        },
        tr(
          "Познакомился с Mnemai за пару минут — теперь все мои ИИ знают меня одинаково, а память лежит у меня на компьютере.",
        ),
      );
    if (typeof refreshStatus === "function") refreshStatus();
  };
  draw();
}

// ---------------------------------------------------------------- «Прожарка»: the summary of a consortium as a card
function shareSummary(i) {
  const m = ((CHAT.chat || {}).messages || [])[i];
  if (!m) return;
  const cons = (CHAT.chat || {}).consortium || {},
    fmt = cons.format || "council";
  const plain = (m.text || "").replace(/[#*_`>]/g, "");
  const lines = plain
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  const bullet = /^([-•*]|\d+[.)])\s+/; // «- …», «• …», «1. …»; a «4/10» line is not one
  const bullets = lines.filter((l) => bullet.test(l)).map((l) => l.replace(bullet, ""));
  const names = (cons.members || []).map(consName).join(", ");
  if (fmt === "roast") {
    const score = /^\W*(\d{1,2})\s*\/\s*10\b/; // the first line of a roast's summary: «4/10», in any language
    const sc = ((lines.find((l) => score.test(l)) || "").match(score) || [])[1];
    const verdict = lines.find((l) => !score.test(l) && !bullet.test(l)) || "";
    return shareCard(
      {
        kind: tr("Прожарка"),
        big: sc ? sc + "/10" : "🔥",
        title: verdict,
        lines: bullets,
      },
      `${tr("Отдал на прожарку совету из нескольких ИИ")} (${names}). ${sc ? tr("Оценка") + ": " + sc + "/10." : ""}`,
    );
  }
  const head = (lines[0] || "").replace(/^Итог:\s*/i, "");
  shareCard(
    {
      kind: tr((CONS_FORMATS[fmt] || CONS_FORMATS.council).n),
      title: head,
      sub: names,
      lines: bullets,
    },
    `${tr("Задал вопрос совету из нескольких ИИ")} (${names}) — ${tr("вот к чему они пришли.")}`,
  );
}
