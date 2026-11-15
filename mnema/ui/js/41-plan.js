// Схема задачи: несколько ИИ по шагам, с оценкой времени и токенов — и три варианта на выбор.
let PLAN_PLANS = [],
  PLAN_TASK = "";

function planTokRange(e) {
  const lo = e.tokens_min ?? e.tokens ?? 0,
    hi = e.tokens_max ?? e.tokens ?? 0;
  return lo === hi ? fmtTok(lo, true) : `${fmtTok(lo, true)}–${fmtTok(hi, true)}`;
}

function planMoney(v) {
  const n = Number(v) || 0;
  if (n <= 0) return "$0";
  return n < 0.01 ? `$${n.toFixed(4).replace(".", ",")}` : `$${n.toFixed(2).replace(".", ",")}`;
}

function planMoneyRange(e) {
  const lo = e.cost_min ?? e.cost ?? 0,
    hi = e.cost_max ?? e.cost ?? 0;
  return planMoney(lo) === planMoney(hi) ? planMoney(lo) : `${planMoney(lo)}–${planMoney(hi)}`;
}

function planSecRange(e) {
  const lo = e.seconds_min ?? e.seconds ?? 0,
    hi = e.seconds_max ?? e.seconds ?? 0;
  return lo === hi ? planSecs(lo) : `${planSecs(lo)}–${planSecs(hi)}`;
}

function planStepsWord(n) {
  const m = n % 10,
    h = n % 100;
  if (h >= 11 && h <= 14) return "шагов";
  return m === 1 ? "шаг" : m >= 2 && m <= 4 ? "шага" : "шагов";
}

function planSecs(sec) {
  const s = Math.max(1, Math.round(Number(sec) || 0));
  if (s < 60) return s + " с";
  const m = Math.floor(s / 60),
    r = s % 60;
  return r ? `${m} мин ${r} с` : `${m} мин`;
}

function planCardHTML(plan, inChat) {
  const steps = plan.steps || [];
  const est = plan.estimate || {};
  const tone = ["fast", "optimal", "quality"].includes(plan.id) ? plan.id : "optimal";
  const nodes = steps
    .map((s, i) => {
      const e = s.est || {},
        a = s.actual;
      const title = `прогноз ${planTokRange(e)} · ${planSecRange(e)}${a ? ` / факт ${fmtTok(a.tokens || 0, true)} · ${planSecs(a.seconds)}` : ""}`;
      return `<div class="pnode" title="${title}"><div class="phead"><span class="pnum">${i + 1}</span><span class="prole">${esc(s.role || "Шаг")}</span></div><span class="pmodel">${esc(s.model_name || s.model || "")}</span><span class="pmeta">≈ ${planTokRange(e)} · ${planSecRange(e)}</span></div>`;
    })
    .join('<span class="parrow">→</span>');
  const done = plan.actual;
  const status = plan.status === "running" ? `<span class="pstat">идёт</span>` : "";
  const tokens = `${planTokRange(est)}${done ? ` → ${fmtTok(done.tokens || 0, true)}` : ""}`;
  const secs = `${planSecRange(est)}${done ? ` → ${planSecs(done.seconds)}` : ""}`;
  const money = planMoneyRange(est);
  const ctx = plan.context
    ? `<span class="pctx" title="${tr("В план вошли память о тебе и последние сообщения разговора")}">${ic("mem")}${tr("память + история")}</span>`
    : "";
  return `<div class="plancard tone-${tone} ${inChat ? "inchat" : ""}" data-plan="${esc(plan.id || "")}">
    <div class="planh"><span class="planbadge">${esc(plan.title || "План")}</span><small>${esc(plan.note || "")}</small>${ctx}<span class="ptotals"><span class="ptot" title="${tr("прогноз → факт")}">${ic("clock")}${secs}</span><span class="ptot" title="${tr("прогноз → факт")}">${ic("coin")}${tokens}</span><span class="ptot ptot-money" title="${tr("Оценка по прайсу API")}">$ ${money}</span>${status}</span></div>
    <div class="pflow ${steps.length > 1 ? "multi" : ""}">${nodes}</div>
    ${plan.why ? `<div class="pwhy">${esc(plan.why)}</div>` : ""}
    ${inChat ? "" : `<div class="pfoot"><span class="phint">${tr("Оценка в диапазоне: минимум — если модели ответят коротко, максимум — если разойдутся")}</span><button class="btn sm" data-plan-run="${esc(plan.id || "")}">${tr("Запустить")}</button></div>`}
  </div>`;
}

function planClose() {
  const m = $("#planm");
  if (m) m.remove();
}

function planOpen() {
  planClose();
  const pop = document.createElement("div");
  pop.className = "modal planm";
  pop.id = "planm";
  pop.innerHTML = `<div class="card planc">
    <button class="lmx" data-x title="${tr("Закрыть")}">×</button>
    <div class="planhead">
      <span class="planic">${ic("flow")}</span>
      <div class="planht">
        <h2>${tr("Схема задачи")}</h2>
        <p class="hint">${tr("Опиши задачу — Mnemai разложит её на шаги, подберёт ИИ из подключённых, покажет время и токены и даст три варианта на выбор.")}</p>
      </div>
    </div>
    <div class="planbox">
      <textarea id="plantask" class="planinp" rows="4" placeholder="${tr("Например: разбери договоры в папке, найди риски и сделай короткий отчёт")}"></textarea>
      <div class="planex">
        <span>${tr("Примеры")}</span>
        <button type="button" class="exchip" data-ex="${tr("Разбери договоры в папке, найди риски и сделай короткий отчёт")}">${tr("Договоры")}</button>
        <button type="button" class="exchip" data-ex="${tr("Сравни поставщиков по цене и надёжности, дай рекомендацию")}">${tr("Поставщики")}</button>
        <button type="button" class="exchip" data-ex="${tr("Спланируй миграцию данных без простоя")}">${tr("Миграция")}</button>
      </div>
    </div>
    <div class="planfoot">
      <div class="plannote">${ic("mem")}${tr("учтём память и историю разговора")} · ${ic("users")}${tr("исполнители из подключённых ИИ")}</div>
      <button class="btn" id="plango">${ic("flow")}<span>${tr("Предложить варианты")}</span></button>
    </div>
    <div id="planout"></div>
  </div>`;
  document.body.appendChild(pop);
  $("[data-x]", pop).onclick = planClose;
  pop.onclick = (e) => {
    if (e.target === pop) planClose();
  };
  $("#plango", pop).onclick = planPropose;
  $$("[data-ex]", pop).forEach(
    (b) =>
      (b.onclick = () => {
        const t = $("#plantask", pop);
        t.value = b.dataset.ex;
        t.focus();
      }),
  );
  setTimeout(() => $("#plantask", pop).focus(), 60);
}

async function planPropose() {
  const task = ($("#plantask") || {}).value?.trim() || "";
  const out = $("#planout");
  if (!task) return toast(tr("Напиши задачу"));
  const b = $("#plango");
  const was = b.textContent;
  b.disabled = true;
  b.textContent = tr("Подбираю…");
  if (out)
    out.innerHTML = `<div class="planwait"><i class="planspin"></i><span>${tr("Подбираю исполнителей из подключённых ИИ…")}</span></div>`;
  try {
    const r = await post("/api/plan/propose", { task, chat: CHAT.id || "" });
    PLAN_TASK = task;
    PLAN_PLANS = r.plans || [];
    renderPlans();
  } catch (e) {
    toast(e.message);
    if (out) out.innerHTML = `<p class="hint">${esc(e.message)}</p>`;
  } finally {
    b.disabled = false;
    b.textContent = was;
  }
}

function renderPlans() {
  const out = $("#planout");
  if (!out) return;
  if (!PLAN_PLANS.length) {
    out.innerHTML = `<p class="hint">${tr("Не удалось собрать варианты — попробуй ещё раз.")}</p>`;
    return;
  }
  out.innerHTML =
    PLAN_PLANS.map((p) => planCardHTML(p, false)).join("") +
    `<p class="planpricenote">${tr("Деньги — ориентир по прайсу API: Claude Code по подписке и локальные модели считаются как $0.")}</p>`;
  $$("[data-plan-run]", out).forEach((b) => {
    b.onclick = () => planAsk(b.dataset.planRun);
  });
}

function planCloseAsk() {
  const q = $("#planq");
  if (q) q.remove();
}

function planAsk(id) {
  const plan = PLAN_PLANS.find((p) => p.id === id);
  if (!plan) return;
  const now = ($("#plantask") || {}).value?.trim() || "";
  if (now && now !== PLAN_TASK) {
    // the task was edited after the variants were built: rebuild them instead of asking about the old one
    planPropose();
    toast(tr("Задача изменилась — варианты обновляются"));
    return;
  }
  planCloseAsk();
  const tone = ["fast", "optimal", "quality"].includes(plan.id) ? plan.id : "optimal";
  const steps = plan.steps || [];
  const names = [...new Set(steps.map((s) => s.model_name || s.model).filter(Boolean))].join(" → ");
  const chatName = esc((CHAT.chat && CHAT.chat.title) || tr("новый разговор"));
  const est = plan.estimate || {};
  const pop = document.createElement("div");
  pop.className = "modal planq";
  pop.id = "planq";
  pop.innerHTML = `<div class="card pqcard tone-${tone}">
    <button class="lmx" data-qx title="${tr("Закрыть")}">×</button>
    <div class="pqhead"><span class="pqic">${ic("flow")}</span><div><h2>${tr("Применить схему к чату?")}</h2><p class="hint">${tr("Схема готова. Можно сразу применить её в этом разговоре, переделать или отменить.")}</p></div></div>
    <div class="pqsum">
      <div class="pqrow"><span class="planbadge">${esc(plan.title || tr("План"))}</span><span class="pqmeta">${steps.length} ${planStepsWord(steps.length)} · ${esc(names)}</span></div>
      <div class="pqrow pqmeta"><span>${ic("clock")}${planSecRange(est)}</span><span>${ic("coin")}${planTokRange(est)}</span>${plan.context ? `<span>${ic("mem")}${tr("память + история")}</span>` : ""}</div>
    </div>
    <p class="hint pqnote">${tr("План выполнится прямо в разговоре «") + chatName + tr("»; его можно остановить в любой момент.")}</p>
    <div class="pqact">
      <button class="btn g" data-pq="cancel">${tr("Отменить")}</button>
      <button class="btn l" data-pq="redo">${tr("Переделать")}</button>
      <button class="btn" data-pq="apply">${tr("Применить к чату")}</button>
    </div>
  </div>`;
  document.body.appendChild(pop);
  $("[data-qx]", pop).onclick = planCloseAsk;
  pop.onclick = (e) => {
    if (e.target === pop) planCloseAsk();
  };
  $$("[data-pq]", pop).forEach((b) => {
    b.onclick = () => {
      if (b.dataset.pq === "cancel") {
        planCloseAsk();
        planClose();
      } else if (b.dataset.pq === "redo") {
        planCloseAsk();
        planPropose();
      } else {
        planCloseAsk();
        planApply(plan);
      }
    };
  });
}

async function planApply(plan) {
  plan.task = PLAN_TASK;
  const b = document.querySelector(`[data-plan-run="${plan.id}"]`);
  if (b) {
    b.disabled = true;
    b.textContent = tr("Запускаю…");
  }
  try {
    const r = await post("/api/plan/run", { chat: CHAT.id || "", plan });
    planClose();
    if (r.chat && CHAT.id !== r.chat) await viewChat(r.chat);
    poll();
  } catch (e) {
    toast(e.message);
    if (b) {
      b.disabled = false;
      b.textContent = tr("Запустить");
    }
  }
}
