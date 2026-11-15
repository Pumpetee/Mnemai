// Схема задачи: несколько ИИ по шагам, с оценкой времени и токенов — и три варианта на выбор.
let PLAN_PLANS = [],
  PLAN_TASK = "";

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
  const flow = steps
    .map((s, i) => {
      const e = s.est || {};
      return `<div class="pnode"><span class="pnum">${i + 1}</span><span class="prole">${esc(s.role || "Шаг")}</span><span class="pmodel">${esc(s.model_name || s.model || "")}</span><span class="pmeta">≈ ${fmtTok(e.tokens || 0, true)} · ${planSecs(e.seconds)}</span></div>`;
    })
    .join('<span class="parrow">→</span>');
  const status =
    plan.status === "running" ? ` · <b>идёт</b>` : plan.actual ? ` · ${planSecs(plan.actual.seconds)}` : "";
  return `<div class="plancard ${inChat ? "inchat" : ""}" data-plan="${esc(plan.id || "")}">
    <div class="planh"><b>${esc(plan.title || "План")}</b><small>${esc(plan.note || "")}</small></div>
    <div class="pflow">${flow}</div>
    <div class="ptotals">${ic("clock")}≈ ${planSecs(est.seconds)} ${ic("coin")}≈ ${fmtTok(est.tokens || 0, true)}${status}</div>
    ${inChat ? "" : `<div class="row" style="justify-content:flex-end"><button class="btn sm" data-plan-run="${esc(plan.id || "")}">Запустить</button></div>`}
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
    <button class="lmx" data-x>×</button>
    <h2>${tr("Схема задачи")}</h2>
    <p class="hint">${tr("Опиши задачу — Mnemai подберёт исполнителей из подключённых ИИ, разложит работу по шагам и покажет время и токены. Выбери вариант и запусти.")}</p>
    <textarea id="plantask" class="inp" rows="3" placeholder="${tr("Например: разбери договоры в папке, найди риски и сделай короткий отчёт")}"></textarea>
    <div class="row" style="justify-content:flex-end;margin-top:10px"><button class="btn" id="plango">${tr("Предложить варианты")}</button></div>
    <div id="planout"></div>
  </div>`;
  document.body.appendChild(pop);
  $("[data-x]", pop).onclick = planClose;
  pop.onclick = (e) => {
    if (e.target === pop) planClose();
  };
  $("#plango", pop).onclick = planPropose;
  setTimeout(() => $("#plantask", pop).focus(), 60);
}

async function planPropose() {
  const task = ($("#plantask") || {}).value?.trim() || "";
  if (!task) return toast(tr("Напиши задачу"));
  const b = $("#plango");
  b.disabled = true;
  const was = b.textContent;
  b.textContent = tr("Подбираю…");
  try {
    const r = await post("/api/plan/propose", { task });
    PLAN_TASK = task;
    PLAN_PLANS = r.plans || [];
    renderPlans();
  } catch (e) {
    toast(e.message);
  } finally {
    b.disabled = false;
    b.textContent = was;
  }
}

function renderPlans() {
  const out = $("#planout");
  if (!out) return;
  out.innerHTML = PLAN_PLANS.map((p) => planCardHTML(p, false)).join("");
  $$("[data-plan-run]", out).forEach((b) => {
    b.onclick = () => planRun(b.dataset.planRun);
  });
}

async function planRun(id) {
  const plan = PLAN_PLANS.find((p) => p.id === id);
  if (!plan) return;
  plan.task = PLAN_TASK;
  const b = document.querySelector(`[data-plan-run="${id}"]`);
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
