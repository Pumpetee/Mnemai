// Схема задачи: несколько ИИ по шагам, с оценкой времени и токенов — и три варианта на выбор.
let PLAN_PLANS = [],
  PLAN_TASK = "",
  PLAN_WHO = LS.get("plan_who", "auto");

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
  if (e.cost_min == null && e.cost == null) return ""; // old cards have no prices
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

function planActionsWord(n) {
  const m = n % 10,
    h = n % 100;
  if (h >= 11 && h <= 14) return "действий";
  return m === 1 ? "действие" : m >= 2 && m <= 4 ? "действия" : "действий";
}

// a step says how it ended: a normal one gets a tick, an empty, timed-out or stopped one — a visible mark
const PLAN_STEP_MARKS = {
  ok: ["check", "готово", "ok"],
  empty: ["x", "нет текста", "bad"],
  timeout: ["clock", "ошибка", "bad"],
  stopped: ["pause", "стоп", "warn"],
};

function planStepMark(status) {
  const key = String(status || "").trim();
  return key ? PLAN_STEP_MARKS[key] || ["x", key, "bad"] : null;
}

function planStepStatusHTML(s, mark) {
  const acts = Math.max(0, Math.round(Number(s.actions) || 0));
  const tip = [tr(mark[1]), acts ? `${acts} ${planActionsWord(acts)}` : "", String(s.note || "").trim()]
    .filter(Boolean)
    .join(" · ");
  return `<span class="psts ${mark[2]}" title="${esc(tip)}">${ic(mark[0])}${esc(tr(mark[1]))}</span>`;
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
        a = s.actual,
        mark = planStepMark(s.status);
      const title = `прогноз ${planTokRange(e)} · ${planSecRange(e)}${a ? ` / факт ${fmtTok(a.tokens || 0, true)} · ${planSecs(a.seconds)}` : ""}`;
      const acts = Math.max(0, Math.round(Number(s.actions) || 0));
      const note =
        String(s.note || "").trim() || (mark && mark[2] !== "ok" && acts ? `${acts} ${planActionsWord(acts)}` : "");
      return `<div class="pstep${mark ? " " + mark[2] : ""}" title="${esc(title)}"><span class="pnum">${i + 1}</span><span class="pst"><b>${esc(s.role || "Шаг")}</b><small>${esc(s.model_name || s.model || "")}</small>${note ? `<small class="pstepnote">${esc(note)}</small>` : ""}</span>${mark ? planStepStatusHTML(s, mark) : ""}<span class="pest">≈ ${planTokRange(e)} · ${planSecRange(e)}</span></div>`;
    })
    .join("");
  const done = plan.actual;
  const running = plan.status === "running" ? `<span class="pstat">${tr("идёт")}</span>` : "";
  const stopName = {
    empty_step: "шаг не дал текста",
    timeout: "превышен лимит времени",
    owner: "остановлено владельцем",
    failed: "ошибка",
  };
  const stopped =
    plan.status === "stopped" || plan.status === "failed"
      ? `<span class="pstat bad"${plan.stop_reason ? ` title="${esc(stopName[plan.stop_reason] || plan.stop_reason)}"` : ""}>${tr(plan.status === "failed" ? "ошибка" : "остановлено")}</span>`
      : "";
  const status = running + stopped;
  const tokens = `${planTokRange(est)}${done ? ` → ${fmtTok(done.tokens || 0, true)}` : ""}`;
  const secs = `${planSecRange(est)}${done ? ` → ${planSecs(done.seconds)}` : ""}`;
  const money = planMoneyRange(est);
  const moneyPill = money ? `<span class="ptot ptot-money" title="${tr("Оценка по прайсу API")}">${money}</span>` : "";
  const ctx = plan.context
    ? `<span class="pctx" title="${tr("В план вошли память о тебе и последние сообщения разговора")}">${ic("mem")}${tr("память + история")}</span>`
    : "";
  return `<div class="plancard tone-${tone} ${inChat ? "inchat" : ""}" data-plan="${esc(plan.id || "")}">
    <div class="planh"><span class="planbadge">${esc(plan.title || "План")}</span><small>${esc(plan.note || "")}</small>${ctx}<span class="ptotals"><span class="ptot" title="${tr("прогноз → факт")}">${ic("clock")}${secs}</span><span class="ptot" title="${tr("прогноз → факт")}">${ic("coin")}${tokens}</span>${moneyPill}${status}</span></div>
    <div class="psteps">${nodes}</div>
    ${!inChat && plan.why ? `<div class="pwhy">${esc(plan.why)}</div>` : ""}
    ${inChat ? "" : `<div class="pfoot"><span class="phint">${tr("Оценка в диапазоне: минимум — если модели ответят коротко, максимум — если разойдутся")}</span>${plan.doc ? `<button class="btn g sm" data-fopen="${esc(plan.doc)}">${ic("file")}${tr("Документ")}</button>` : ""}<button class="btn sm" data-plan-run="${esc(plan.id || "")}">${tr("Запустить")}</button></div>`}
  </div>`;
}

function planClose() {
  const m = $("#planm");
  if (m) m.remove();
}

function planOpen(prefill = "") {
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
      ${planWhoHTML()}
    </div>
    <div class="planfoot">
      <div class="plannote">${ic("mem")}${tr("учтём память и историю разговора")} · ${ic("users")}${tr("исполнители из подключённых ИИ")}</div>
      <div class="planacts">
        <button class="btn g" id="planrecalc">${ic("redo")}<span>${tr("Пересчитать")}</span></button>
        <button class="btn" id="plango">${ic("flow")}<span>${tr("Предложить варианты")}</span></button>
      </div>
    </div>
    <div id="planout"></div>
  </div>`;
  document.body.appendChild(pop);
  $("[data-x]", pop).onclick = planClose;
  pop.onclick = (e) => {
    if (e.target === pop) planClose();
  };
  $("#plango", pop).onclick = planPropose;
  $("#planrecalc", pop).onclick = planPropose;
  planWhoWire(pop);
  loadPlanModels();
  const task = typeof prefill === "string" ? prefill.trim() : "";
  const inp = $("#plantask", pop);
  if (inp && task) inp.value = task; // rebuild from the result card: pre-filled, nothing runs by itself
  setTimeout(() => {
    const f = $("#plantask", pop);
    if (f) f.focus();
  }, 60);
}

async function planPropose() {
  const task = ($("#plantask") || {}).value?.trim() || "";
  const out = $("#planout");
  if (!task) return toast(tr("Напиши задачу"));
  const b = $("#plango"),
    recalc = $("#planrecalc");
  if (!b || b.disabled) return;
  const was = b.textContent;
  b.disabled = true;
  b.textContent = tr("Подбираю…");
  if (recalc) recalc.disabled = true;
  if (out)
    out.innerHTML = `<div class="planwait"><i class="planspin"></i><span>${tr("Подбираю исполнителей из подключённых ИИ…")}</span></div>`;
  try {
    const r = await post("/api/plan/propose", { task, chat: CHAT.id || "", planner: PLAN_WHO });
    PLAN_TASK = task;
    PLAN_PLANS = r.plans || [];
    const info = $("#planwhoinfo");
    const who = PLAN_PLANS[0] && PLAN_PLANS[0].planner;
    if (info && who) info.textContent = `${tr("Подобрал")}: ${who.name} · ${who.provider}`;
    renderPlans();
  } catch (e) {
    toast(e.message);
    if (out) out.innerHTML = `<p class="hint">${esc(e.message)}</p>`;
  } finally {
    b.disabled = false;
    b.textContent = was;
    if (recalc) recalc.disabled = false;
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
    `<p class="planpricenote">${tr("Деньги — ориентир по прайсу API: Claude Code показан по API-цене для сравнения, по подписке он $0; локальные модели $0.")}</p>`;
  $$("[data-plan-run]", out).forEach((b) => {
    b.onclick = () => planAsk(b.dataset.planRun);
  });
}

function planWhoList() {
  return (CHAT.providers || [])
    .filter((p) => p.ready)
    .flatMap((p) =>
      (p.models || []).map((m) => ({
        model: p.id + ":" + m.id,
        v: p.id + ":" + m.id,
        pid: p.id,
        name: m.name,
        provider: p.name,
        free: ["local", "ollama", "strata"].includes(p.id),
        tier: ["local", "ollama", "strata"].includes(p.id) ? 1 : 3,
        price_in: 0,
        price_out: 0,
      })),
    );
}

let PLAN_MODELS = [];

function planWhoLabel() {
  if (PLAN_WHO === "auto") return tr("Авто · дешёвая");
  if (PLAN_WHO === "strong") return tr("Сильная");
  if (PLAN_WHO === "medium") return tr("Средняя");
  if (PLAN_WHO === "local") return tr("Локально");
  const m = PLAN_MODELS.find((x) => x.model === PLAN_WHO) || planWhoList().find((x) => x.v === PLAN_WHO);
  return m ? m.name : PLAN_WHO;
}

function planWhoHTML() {
  const models = planWhoList();
  if (
    !["auto", "strong", "local"].includes(PLAN_WHO) &&
    !models.some((m) => m.v === PLAN_WHO) &&
    !PLAN_MODELS.some((m) => m.model === PLAN_WHO)
  )
    PLAN_WHO = "auto";
  const hasLocal = models.some((m) => ["local", "ollama", "strata"].includes(m.pid));
  const chip = (v, title, sub) =>
    `<button type="button" class="pwopt ${PLAN_WHO === v ? "on" : ""}" data-pw="${v}"><b>${tr(title)}</b><small>${tr(sub)}</small></button>`;
  const customOn = !["auto", "strong", "medium", "local"].includes(PLAN_WHO);
  return `<div class="planwho">
    <div class="planwhoh"><span>${tr("Исполнителей подбирает")}</span><small>${tr("от планировщика зависят качество, время и цена схемы")}</small></div>
    <div class="planwhoopts">
      ${chip("auto", "Авто", "дешёвая и быстрая")}
      ${chip("strong", "Сильная", "умнее план")}
      ${chip("medium", "Средняя", "баланс цены и качества")}
      ${hasLocal ? chip("local", "Локально", "без оплаты") : ""}
      <button type="button" class="pwopt pwoptall ${customOn ? "on" : ""}" id="planwhoall"><b>${tr("Все модели")}</b><small id="planwhopick">${esc(planWhoLabel())}</small></button>
    </div>
    <div class="planwhoinfo" id="planwhoinfo"></div>
  </div>`;
}

function planWhoWire(pop) {
  $$("[data-pw]", pop).forEach(
    (b) =>
      (b.onclick = () => {
        PLAN_WHO = b.dataset.pw;
        LS.set("plan_who", PLAN_WHO);
        $$("[data-pw]", pop).forEach((x) => x.classList.toggle("on", x === b));
        const all = $("#planwhoall", pop);
        if (all) {
          all.classList.remove("on");
          const lbl = $("#planwhopick", pop);
          if (lbl) lbl.textContent = planWhoLabel();
        }
        const info = $("#planwhoinfo", pop);
        if (info) info.textContent = "";
      }),
  );
  const all = $("#planwhoall", pop);
  if (all) all.onclick = () => planModelPicker();
}

async function loadPlanModels() {
  try {
    const r = await api("/api/plan/models");
    PLAN_MODELS = r.models || [];
  } catch (e) {
    PLAN_MODELS = [];
  }
  const pick = $("#planwhopick");
  if (pick) pick.textContent = planWhoLabel();
}

function planPrice(v) {
  const n = Number(v) || 0;
  if (!n) return "$0";
  return n < 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(2)}`;
}

function planKind(m) {
  if (m.free) return tr("локальная · бесплатно");
  return m.tier >= 3 ? tr("сильная") : m.tier === 2 ? tr("средняя") : tr("дешёвая");
}

function planRole(m) {
  if (m.free) return tr("черновик и проверка");
  return m.tier >= 3 ? tr("план и критика") : m.tier === 2 ? tr("план и шаги") : tr("быстрые шаги");
}

function planModelPicker() {
  const old = $("#planpick");
  if (old) {
    old.remove();
    return;
  }
  const pop = document.createElement("div");
  pop.className = "modal planpick";
  pop.id = "planpick";
  pop.innerHTML = `<div class="card ppcard">
    <button class="lmx" data-x title="${tr("Закрыть")}">×</button>
    <h2>${tr("Кого поставить планировщиком?")}</h2>
    <p class="hint">${tr("Это модель, которая будет подбирать исполнителей для шагов, а не выполнять шаги. Цены — ориентир за 1 млн токенов; локальные — $0.")}</p>
    <input class="inp" id="ppsearch" placeholder="${tr("Поиск по модели или провайдеру")}">
    <div class="ppwrap"><table class="pptable"><thead><tr><th>${tr("Модель")}</th><th>${tr("Провайдер")}</th><th>${tr("Вход / 1М")}</th><th>${tr("Выход / 1М")}</th><th>${tr("Хорошо для")}</th><th>${tr("Класс")}</th><th></th></tr></thead><tbody id="pprows"></tbody></table></div>
    <p class="ppnote" id="ppmore"></p>
    <p class="ppnote">${tr("Цены — ориентир по прайсу API; Claude Code по подписке и локальные модели — $0.")}</p>
  </div>`;
  document.body.appendChild(pop);
  const close = () => pop.remove();
  $("[data-x]", pop).onclick = close;
  pop.onclick = (e) => {
    if (e.target === pop) close();
  };
  const rows = PLAN_MODELS.length ? PLAN_MODELS : planWhoList();
  const draw = () => {
    const q = ($("#ppsearch", pop).value || "").trim().toLowerCase();
    const all = rows
      .filter((m) => !q || (m.name + " " + m.provider + " " + m.model).toLowerCase().includes(q))
      .sort((a, b) => (a.free === b.free ? a.price_in - b.price_in || a.name.localeCompare(b.name) : a.free ? -1 : 1));
    const list = all.slice(0, 60);
    const more = $("#ppmore", pop);
    if (more)
      more.textContent = all.length > 60 ? `${tr("Показаны первые 60 из")} ${all.length} — ${tr("уточни поиск.")}` : "";
    $("#pprows", pop).innerHTML = list.length
      ? list
          .map(
            (m) =>
              `<tr class="${m.model === PLAN_WHO ? "cur" : ""}"><td><b>${esc(m.name)}</b><small>${esc(m.model.split(":").slice(1).join(":"))}</small></td><td>${esc(m.provider)}</td><td>${planPrice(m.price_in)}</td><td>${planPrice(m.price_out)}</td><td>${planRole(m)}</td><td><span class="pptag ${m.free ? "free" : m.tier >= 3 ? "strong" : "cheap"}">${planKind(m)}</span></td><td><button class="btn sm" data-pick="${esc(m.model)}">${m.model === PLAN_WHO ? tr("Выбрана") : tr("Выбрать")}</button></td></tr>`,
          )
          .join("")
      : `<tr><td colspan="7" class="ppempty">${tr("Ничего не нашлось")}</td></tr>`;
    $$("[data-pick]", pop).forEach((b) => {
      b.onclick = () => {
        PLAN_WHO = b.dataset.pick;
        LS.set("plan_who", PLAN_WHO);
        close();
        const main = $("#planwhoopts");
        if (main) {
          $$("[data-pw]", main).forEach((x) => x.classList.remove("on"));
          const allb = $("#planwhoall", main);
          if (allb) {
            allb.classList.add("on");
            const lbl = $("#planwhopick", main);
            if (lbl) lbl.textContent = planWhoLabel();
          }
        }
        const info = $("#planwhoinfo");
        if (info) info.textContent = `${tr("Планировщик")}: ${planWhoLabel()}`;
      };
    });
  };
  $("#ppsearch", pop).oninput = draw;
  draw();
  $("#ppsearch", pop).focus();
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
    CHAT.reading = false;
    const r = await post("/api/plan/run", { chat: CHAT.id || "", plan });
    planClose();
    if (r.chat && CHAT.id !== r.chat) await viewChat(r.chat);
    CHAT.reading = false;
    scrollEnd();
    poll();
  } catch (e) {
    toast(e.message);
    if (b) {
      b.disabled = false;
      b.textContent = tr("Запустить");
    }
  }
}
