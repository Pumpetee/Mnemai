// ---------------------------------------------------------------- the first minutes: one idea per screen, gently
async function welcomeFlow() {
  if ($(".wlc") || window.__wlc) return;
  window.__wlc = 1;
  const [ag, ms, lc, cry] = await Promise.all([
    api("/api/agent").catch(() => ({ profile: {} })),
    api("/api/models").catch(() => ({ providers: [] })),
    api("/api/local").catch(() => null),
    api("/api/crypto").catch(() => null),
  ]);
  const name = (ag.profile || {}).owner_name || "",
    ready = ms.providers.filter((p) => p.ready && p.id !== "local"),
    claude = ready[0]; // any connected cloud AI — none goes first by name
  let pick = lc
    ? lc.catalog.find((m) => m.recommended && m.fit !== "no") ||
      lc.catalog.filter((m) => m.fit === "ok").sort((a, b) => b.size - a.size)[0]
    : null;
  const pop = document.createElement("div");
  pop.className = "modal wlc";
  document.body.appendChild(pop);
  document.body.classList.add("wlc-on");
  let i = 0,
    memChoice = MEM.on, // a new memory folder starts off; the owner turns it on here
    dl = false,
    lock = {
      on: false,
      pw: "",
      pw2: "",
      remember: true,
      show: false,
      busy: false,
      err: "",
    }, // «Защитить паролем»
    choice = claude ? "claude" : "local"; // what the owner talks to first; either card can be picked
  const finish = async () => {
    await post("/api/local/offer", { state: "done" }).catch(() => {});
    if (!MEM.asked || memChoice !== MEM.on) await memSet(memChoice, true).catch(() => {});
    if (choice === "local" && pick && (pick.installed || dl)) {
      const ref = "local:" + pick.id;
      await post("/api/agent", { default_model: ref, last_model: ref }).catch(() => {});
      CHAT.model = ref;
    }
    pop.classList.add("bye");
    document.body.classList.remove("wlc-on");
    setTimeout(() => pop.remove(), 300);
    if (!$("#chatgrid")) {
      location.hash = "chat";
    } else {
      await refreshProviders();
      if (!CHAT.id) renderEmpty();
    }
  };
  const vs = (a, b) =>
    `<div class="wvs"><div class="wcol bad"><span class="wlab">${tr("Обычный ИИ")}</span>${a}</div><div class="wcol good"><span class="wlab">Mnemai</span>${b}</div></div>`;
  const S = [
    {
      case: 1,
      art: vs(
        `<div class="cb me long"><i></i><i></i><i></i><i></i></div><div class="cb ai">${tr("Расскажите о проекте…")}</div>`,
        `<div class="cb me">${tr("Продолжим пилот?")}</div><div class="cb ai ok">${tr("Да! 3 ноября, Казань.")}</div>`,
      ),
      t: tr("Не нужно объяснять заново"),
      p: tr("Mnemai помнит, кто ты, твои проекты и как с тобой говорить. Сразу к делу."),
    },
    {
      case: 2,
      art: `<div class="worb"><div class="wcore">${ic("mem")}<span>${tr("Память")}</span></div>${["Claude", "ChatGPT", "Gemini", "Cursor"].map((n, k) => `<span class="wsat s${k}">${n}</span>`).join("")}<svg class="wlines" viewBox="0 0 300 150"><path d="M150 75L52 30M150 75L248 30M150 75L52 120M150 75L248 120"/></svg></div>`,
      t: tr("Одна память во всех ИИ"),
      p: tr("Сменил модель — ничего не потерял. Claude, ChatGPT и другие знают одно и то же."),
    },
    {
      case: 3,
      // the measured case from the knowledge base: a 153 000-character contract, input tokens without and with the economy
      art: `<div class="wtok"><div class="wtokh">${ic("file")}<span>${tr("Вопрос по договору на 153 000 знаков")}</span><small>${tr("входные токены")}</small></div>
        <div class="wtrow raw"><span>${tr("Весь текст")}</span><i style="--w:100%"></i><b data-noi18n>29 643</b></div>
        <div class="wtrow mn"><span>Mnemai</span><i style="--w:21%"></i><b data-noi18n>6 159</b></div>
        <div class="wtais">${["Claude", "ChatGPT", "Gemini", tr("на компьютере")].map((n, k) => `<em style="--k:${k}">${ic("check")}${esc(n)}</em>`).join("")}</div></div>`,
      t: tr("Меньше токенов в любом ИИ"),
      p: tr(
        "Mnemai отправляет только нужное: из памяти — то, что относится к вопросу, документ — подходящими кусками, старые сообщения — короче. На этом договоре входных токенов в 4,8 раза меньше.",
      ),
    },
    {
      case: 4,
      art: `<div class="wmeet"><div class="wwave">${Array.from({ length: 18 }, (_, k) => `<i style="--k:${k}"></i>`).join("")}</div><div class="warrow">→</div><div class="wtasks"><b>${tr("Итоги")}</b><span>${ic("check")}${tr("Олег — тарифы до пятницы")}</span><span>${ic("check")}${tr("Я — договор")}</span><span>${ic("check")}${tr("Старт 3 ноября")}</span></div></div>`,
      t: tr("Встреча → задачи"),
      p: tr("Запиши созвон: будет расшифровка, итоги и кто что делает. Важное попадёт в память."),
    },
    {
      case: 5,
      art: vs(
        `<div class="cb me">${tr("Что решили по цене?")}</div><div class="cb ai">${tr("Не знаю, о чём речь.")}</div>`,
        `<div class="cb me">${tr("Что решили по цене?")}</div><div class="cb ai ok">${tr("4 900 ₽, решено 20.10")}<em class="wpill">${tr("решение")}</em></div>`,
      ),
      t: tr("Помнит решения и сроки"),
      p: tr("Договорённости, статусы, даты. Устаревшее Mnemai переспросит, а не выдумает."),
    },
    {
      case: 6,
      art: `<div class="wsec"><div class="wpc">${ic("file")}<span>${tr("Твой запрос")}</span></div><div class="wtrack"><em class="wraw">4111 1111…</em><em class="wlbl">[${tr("КАРТА")}-1]</em></div><div class="wpc cl">${ic("globe")}<span>${tr("Облачный ИИ")}</span></div><div class="wshield">${ic("shield")}</div></div>`,
      t: tr("Секреты остаются у тебя"),
      p: tr("Карты, пароли и ключи заменяются метками до отправки. Память — файлы на твоём компьютере."),
    },
    {
      mem: true,
      t: tr("Включить память?"),
      p: tr(
        "С памятью ИИ знают, кто ты и над чем работаешь, а Mnemai учится по ходу разговора. Без неё — обычный чат: ничего не запоминается, всё остальное работает. Поменять можно в любой момент.",
      ),
    },
    ...(cry && !cry.on
      ? [
          {
            lock: true,
            t: tr("Защитить память паролем?"),
            p: tr(
              "Как в KeePass: заметки и разговоры шифруются на диске по AES-256, ключ получается из твоего пароля. Без пароля их не прочитать, даже скопировав папку. Шифрование открытое и проверенное, код Mnemai открыт.",
            ),
          },
        ]
      : []),
    {
      pick: true,
      t: tr("С каким ИИ говорить?"),
      p: claude
        ? tr("Платный ИИ уже подключён — можно начинать. Бесплатный на компьютере пригодится как запасной.")
        : tr(
            "Бесплатный ИИ работает прямо на компьютере, без ключей и подписок. Платные — по подписке или ключу API — можно подключить потом.",
          ),
    },
  ];
  const draw = () => {
    const s = S[i];
    pop.innerHTML = `<div class="card"><button class="wskip" data-skip>${tr("Пропустить")}</button><div class="wslide" key="${i}">
      ${s.pick || s.mem || s.lock ? "" : `<div class="wart">${s.art}</div>`}
      ${s.case ? `<div class="wcase">${tr("Кейс")} ${s.case} ${tr("из")} ${S.filter((x) => x.case).length}</div>` : ""}<h2>${s.case === 1 && name ? esc(name) + ", " + s.t.charAt(0).toLowerCase() + s.t.slice(1) : s.t}</h2><p>${s.p}</p>
      ${
        s.mem
          ? `<div class="wpick"><div class="wopt ${memChoice ? "on" : ""}" data-mem="1"><span class="wic ${memChoice ? "ok" : ""}">${ic(memChoice ? "check" : "user")}</span><div><b>${tr("Включить память")}</b><small>${tr("ИИ знают тебя, Mnemai учится и запоминает")}</small></div></div><div class="wopt ${memChoice ? "" : "on"}" data-mem="0"><span class="wic ${memChoice ? "" : "ok"}">${ic(memChoice ? "eyeoff" : "check")}</span><div><b>${tr("Без памяти")}</b><small>${tr("обычный чат, ничего не запоминается")}</small></div></div></div>`
          : ""
      }
      ${s.lock ? lockStep(lock) : ""}
      ${
        s.pick
          ? `<div class="wpick">${claude ? `<div class="wsec">${tr("Платные")} · ${tr(claude.id === "claude_code" ? "по подписке" : "по ключу API")}</div><div class="wopt ${choice === "claude" ? "on" : ""}" id="wcl"><span class="wic ${choice === "claude" ? "ok" : ""}">${ic(choice === "claude" ? "check" : "chat")}</span><div><b data-noi18n>${esc(claude.name)}</b><small>${tr("уже подключён")}</small></div></div>` : ""}
        ${pick ? `<div class="wsec">${tr("Бесплатные")}</div><div class="wopt ${choice === "local" ? "on" : ""}" id="wloc"><span class="wic ${choice === "local" ? "ok" : ""}">${ic(choice === "local" ? "check" : "folder")}</span><div><b>${tr("Бесплатный ИИ на компьютере")}</b><small>${esc(pick.name)} · ${fmtSize(pick.size)}${pick.eta ? " · ≈ " + fmtEta(pick.eta) : ""}</small><div class="wbar" hidden><i></i></div></div><button class="btn ${claude ? "l" : ""} sm" id="wdl">${pick.installed ? tr("Уже скачан") : tr("Скачать")}</button></div>` : ""}
        <a href="#" class="wmore" id="wmore">${tr("Другие модели и ключи…")}</a></div>`
          : ""
      }</div>
      <div class="wfoot"><div class="wdots">${S.map((_, k) => `<b class="${k === i ? "on" : k < i ? "done" : ""}"></b>`).join("")}</div>${i ? `<button class="btn g" data-back>${tr("Назад")}</button>` : ""}<button class="btn" data-next>${i === S.length - 1 ? tr("Начать") : tr("Дальше")}</button></div></div>`;
    $("[data-next]", pop).onclick = async () => {
      if (S[i].lock && lock.on && !lock.busy) {
        lock.err =
          lock.pw.length < 8 ? "Пароль — не короче 8 знаков" : lock.pw !== lock.pw2 ? "Пароли не совпадают" : "";
        if (lock.err) return draw();
        lock.busy = true;
        draw();
        try {
          const d = await post("/api/crypto", {
            action: "on",
            password: lock.pw,
            remember: lock.remember,
          });
          S.splice(i, 1); // done: the step is not shown again on «Назад»
          lock.pw = lock.pw2 = "";
          if (d.recovery) {
            // the recovery key is shown exactly once, right here in the wizard
            pop.innerHTML = `<div class="card"><h2>${tr("Ключ восстановления")}</h2>
              <p class="hint">${tr("Сохрани этот ключ — он показывается один раз. Забудешь пароль — восстановишь память только по нему: «Настройки → Шифровать память паролем → Восстановить пароль».")}</p>
              <div class="recovery-key" data-noi18n>${esc(d.recovery)}</div>
              <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn l" id="rccopy">${tr("Скопировать")}</button><button class="btn" id="rcdone">${tr("Дальше")}</button></div></div>`;
            $("#rccopy", pop).onclick = async () => {
              try {
                await navigator.clipboard.writeText(d.recovery);
              } catch (e) {}
              toast(tr("Ключ скопирован — сохрани его в надёжном месте"));
            };
            $("#rcdone", pop).onclick = () => draw();
            return;
          }
          toast(tr("Память зашифрована"));
        } catch (err) {
          lock.err = err.message;
          lock.busy = false;
          return draw();
        }
        lock.busy = false;
        return draw();
      }
      if (i < S.length - 1) {
        i++;
        draw();
      } else finish();
    };
    if ($("[data-back]", pop))
      $("[data-back]", pop).onclick = () => {
        i--;
        draw();
      };
    $("[data-skip]", pop).onclick = finish;
    if ($("#wmore", pop))
      $("#wmore", pop).onclick = (e) => {
        e.preventDefault(); // the list opens on top; closing it brings the welcome back
        localModal(false, async () => {
          try {
            const d = await api("/api/local");
            lc.catalog = d.catalog;
            const p2 = d.catalog.find((m) => m.id === (pick || {}).id);
            if (p2) Object.assign(pick, p2);
          } catch (err) {}
          if (document.body.contains(pop)) draw();
        });
      };
    bindLockStep(pop, lock, draw);
    $$("[data-mem]", pop).forEach(
      (x) =>
        (x.onclick = () => {
          memChoice = x.dataset.mem === "1";
          draw();
        }),
    );
    if ($("#wcl", pop))
      $("#wcl", pop).onclick = () => {
        choice = "claude";
        draw();
      };
    if ($("#wloc", pop))
      $("#wloc", pop).onclick = (e) => {
        if (e.target.closest("#wdl")) return;
        choice = "local";
        draw();
        if (!pick.installed && !dl) $("#wdl", pop).click(); // picking a model not on the computer yet downloads it
      };
    if ($("#wdl", pop))
      $("#wdl", pop).onclick = async (e) => {
        choice = "local";
        $("#wloc", pop).classList.add("on");
        if ($("#wcl", pop)) $("#wcl", pop).classList.remove("on");
        if (pick.installed) return;
        const b = e.currentTarget;
        b.disabled = true;
        if ($(".werr", pop)) $(".werr", pop).remove();
        try {
          await post("/api/local/download", { id: pick.id });
          dl = true;
          b.textContent = tr("Скачивается…");
          $(".wbar", pop).hidden = false;
          tick();
        } catch (err) {
          b.disabled = false;
          toast(err.message);
        }
      };
  };
  const tick = async () => {
    if (!document.body.contains(pop) || !$(".wbar", pop)) return;
    try {
      const d = await api("/api/local");
      const x = d.download;
      if (x.id === pick.id && x.status === "error") {
        const b = $("#wdl", pop);
        b.disabled = false;
        b.textContent = tr("Повторить");
        $(".wbar", pop).hidden = true;
        let e = $(".werr", pop);
        if (!e) {
          e = document.createElement("small");
          e.className = "werr";
          $("#wloc div", pop).appendChild(e);
        }
        e.textContent = x.error || tr("Не скачалось");
        return;
      }
      if (x.id === pick.id && x.total) {
        $(".wbar i", pop).style.width = Math.round((x.done / x.total) * 100) + "%";
        if (x.status === "done") {
          $("#wdl", pop).textContent = tr("Готово");
          return;
        }
      }
    } catch (e) {}
    setTimeout(tick, 1000);
  };
  draw();
}
// «Защитить память паролем?» on the first start: no password (default) or Mnemai's own encryption, set right here
function pwScore(pw) {
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (pw.length >= 16) s++;
  if (/[a-zа-яё]/.test(pw) && /[A-ZА-ЯЁ]/.test(pw)) s++;
  if (/\d/.test(pw) && /[^\wа-яё]/i.test(pw)) s++;
  return Math.min(4, Math.max(pw ? 1 : 0, s - 1));
}
function newPassword() {
  const abc = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789-_!@#%";
  const r = crypto.getRandomValues(new Uint32Array(20));
  return Array.from(r, (x) => abc[x % abc.length]).join("");
}
function lockStep(L) {
  const sc = pwScore(L.pw),
    lab = ["", "слабый", "так себе", "хороший", "надёжный"][sc];
  return `<div class="wpick"><div class="wopt ${L.on ? "" : "on"}" data-lock="0"><span class="wic ${L.on ? "" : "ok"}">${ic(L.on ? "folder" : "check")}</span><div><b>${tr("Без пароля")}</b><small>${tr("обычные файлы, их видят Obsidian и другие программы")}</small></div></div>
    <div class="wopt ${L.on ? "on" : ""}" data-lock="1"><span class="wic ${L.on ? "ok" : ""}">${ic(L.on ? "check" : "lock")}</span><div><b>${tr("Зашифровать паролем")}</b><small>${tr("AES-256, без пароля память не открыть")}</small></div></div>
    ${
      L.on
        ? `<div class="wlock"><div class="wpw"><input id="wpw1" type="${L.show ? "text" : "password"}" autocomplete="new-password" placeholder="${tr("Пароль, не короче 8 знаков")}" value="${esc(L.pw)}"><button class="wpwb" data-pwshow title="${tr(L.show ? "Скрыть" : "Показать")}">${ic(L.show ? "eyeoff" : "eye")}</button><button class="wpwb" data-pwgen title="${tr("Придумать надёжный")}">${ic("redo")}</button></div>
        <div class="wpwm s${sc}"><i></i><i></i><i></i><i></i><span>${L.pw ? tr(lab) : ""}</span></div>
        <div class="wpw"><input id="wpw2" type="${L.show ? "text" : "password"}" autocomplete="new-password" placeholder="${tr("Ещё раз")}" value="${esc(L.pw2)}"></div>
        <label class="ulrem"><input type="checkbox" id="wpwrem" ${L.remember ? "checked" : ""}> ${tr("Помнить на этом компьютере — не спрашивать при каждом запуске")}</label>
        <p class="wwarn">${ic("x")}${tr("После включения покажется ключ восстановления — сохрани его: он показывается один раз, по нему восстанавливается забытый пароль. Шифруются только текст-файлы; бинарные (PDF, картинки, записи) остаются открытыми.")}</p>
        ${L.err ? `<div class="ulerr">${esc(tr(L.err))}</div>` : ""}${L.busy ? `<div class="hint">${tr("Шифрую…")}</div>` : ""}</div>`
        : ""
    }</div>`;
}
function bindLockStep(pop, L, draw) {
  $$("[data-lock]", pop).forEach(
    (x) =>
      (x.onclick = () => {
        L.on = x.dataset.lock === "1";
        L.err = "";
        draw();
        if (L.on) setTimeout(() => $("#wpw1", pop) && $("#wpw1", pop).focus(), 30);
      }),
  );
  const inp = (id, k) => {
    const e = $("#" + id, pop);
    if (!e) return;
    e.oninput = () => {
      L[k] = e.value;
      if (k === "pw") {
        const m = $(".wpwm", pop),
          sc = pwScore(L.pw);
        m.className = "wpwm s" + sc;
        $("span", m).textContent = L.pw ? tr(["", "слабый", "так себе", "хороший", "надёжный"][sc]) : "";
      }
    };
  };
  inp("wpw1", "pw");
  inp("wpw2", "pw2");
  if ($("#wpwrem", pop)) $("#wpwrem", pop).onchange = (e) => (L.remember = e.target.checked);
  if ($("[data-pwshow]", pop))
    $("[data-pwshow]", pop).onclick = () => {
      L.show = !L.show;
      draw();
    };
  if ($("[data-pwgen]", pop))
    $("[data-pwgen]", pop).onclick = () => {
      L.pw = L.pw2 = newPassword();
      L.show = true;
      L.err = "";
      draw();
    };
}
// ---------------------------------------------------------------- may Mnemai look outside itself; then what exactly
async function sourcesAsk() {
  if (APP.demo || $(".srcask")) return;
  if ($(".wlc")) {
    setTimeout(sourcesAsk, 1500);
    return;
  }
  let d;
  try {
    d = await api("/api/learn/status");
  } catch (e) {
    return;
  }
  const s = d.settings || {},
    f = s.found || {},
    ids = Object.keys(f).filter((k) => d.sources[k]);
  if ((s.outside !== null && s.outside !== undefined) || !ids.length) return;
  const pop = document.createElement("div");
  pop.className = "modal srcask";
  document.body.appendChild(pop);
  const sub = (k) => f[k].path || d.sources[k].note || "";
  const ask = () => {
    pop.innerHTML = `<div class="card"><div class="saart">${["💬", "📝", "📄", "✈️", "🌐"].map((e, k) => `<span style="--k:${k}">${e}</span>`).join("")}<i class="sahub">${ic("mem")}</i></div>
    <h2>${tr("Можно Mnemai смотреть другие программы?")}</h2>
    <p>${tr("Так Mnemai узнает тебя быстрее — по тому, что ты уже пишешь в других местах: чаты с ИИ, заметки, документы, Telegram, браузер. Всё читается здесь, на компьютере, и только то, что ты выберешь.")}</p>
    <p class="hint">${tr("Если нет — Mnemai учится только на разговорах с ней. Передумать можно в Настройки → Обучение.")}</p>
    <div class="safoot"><button class="btn g" data-no>${tr("Нет, только Mnemai")}</button><button class="btn" data-yes>${tr("Да, выберу что")}</button></div></div>`;
    $("[data-no]", pop).onclick = () => done(false, []);
    $("[data-yes]", pop).onclick = pick;
  };
  const pick = () => {
    pop.innerHTML = `<div class="card"><h2>${tr("Что Mnemai можно смотреть?")}</h2><p>${tr("Нашла это на твоём компьютере. Читаю только то, что отметишь.")}</p>
    <div class="salist">${ids.map((k) => `<label class="sarow"><input type="checkbox" data-sid="${k}"><span><b>${esc(tr(d.sources[k].name))}</b><small data-noi18n>${esc(sub(k))}</small></span></label>`).join("")}</div>
    <div class="safoot"><button class="btn g" data-back>${tr("Назад")}</button><button class="btn" data-ok disabled>${tr("Включить отмеченное")}</button></div></div>`;
    const ok = $("[data-ok]", pop),
      ticked = () =>
        $$("[data-sid]", pop)
          .filter((x) => x.checked)
          .map((x) => x.dataset.sid);
    $$("[data-sid]", pop).forEach(
      (x) =>
        (x.onchange = () => {
          ok.disabled = !ticked().length;
        }),
    );
    ok.onclick = () => done(true, ticked());
    $("[data-back]", pop).onclick = ask;
  };
  const done = async (yes, on) => {
    const src = {};
    on.forEach((k) => (src[k] = { enabled: true }));
    try {
      await post("/api/learn/settings", {
        sources: src,
        outside: yes,
        found_asked: true,
      });
    } catch (e) {
      toast(e.message);
      return;
    }
    pop.remove();
    if (on.length) {
      toast(tr("Включила. Начинаю читать"));
      post("/api/learn/run", {}).catch(() => {});
    } else if (!yes) toast(tr("Хорошо: учусь только на наших разговорах"));
  };
  ask();
}

// a new memory whose tour didn't run: the same choice on its own
function memAsk() {
  const pop = document.createElement("div");
  pop.className = "modal memask";
  let on = false;
  const draw = () => {
    pop.innerHTML = `<div class="card"><h2>${tr("Включить память?")}</h2><p class="hint">${tr("С памятью ИИ знают, кто ты и над чем работаешь, а Mnemai учится по ходу разговора. Без неё — обычный чат: ничего не запоминается, всё остальное работает. Поменять можно в любой момент.")}</p>
      <div class="wpick"><div class="wopt ${on ? "on" : ""}" data-m="1"><span class="wic ${on ? "ok" : ""}">${ic(on ? "check" : "user")}</span><div><b>${tr("Включить память")}</b><small>${tr("ИИ знают тебя, Mnemai учится и запоминает")}</small></div></div><div class="wopt ${on ? "" : "on"}" data-m="0"><span class="wic ${on ? "" : "ok"}">${ic(on ? "eyeoff" : "check")}</span><div><b>${tr("Без памяти")}</b><small>${tr("обычный чат, ничего не запоминается")}</small></div></div></div>
      <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="btn" data-ok>${tr("Готово")}</button></div></div>`;
    $$("[data-m]", pop).forEach((x) => (x.onclick = () => ((on = x.dataset.m === "1"), draw())));
    $("[data-ok]", pop).onclick = async () => {
      pop.remove();
      await memSet(on, true).catch((e) => toast(e.message));
    };
  };
  draw();
  document.body.appendChild(pop);
}
