"use strict";

// ===== 分层样式映射 =====
const TIER_STYLE = {
  "低危":   { color: "#2f9e5b", bg: "#e8f6ee", icon: "●", desc: "年度复评，生活方式指导" },
  "中危":   { color: "#d98a1f", bg: "#fdf3e3", icon: "▲", desc: "半年复评，强化干预" },
  "高危":   { color: "#e0672f", bg: "#fdeee6", icon: "◆", desc: "90 天内重点随访，专科复核" },
  "极高危": { color: "#d64545", bg: "#fbe9e9", icon: "★", desc: "30 天内高优先级预警 + 双向转诊" },
};

// ===== 演示队列（本地研究队列示例 6 例）=====
const QUEUE = [
  { patient_id: "7167", age: 51, sex: "男", sbp: 139, dbp: 83, diabetes: 0, hypertension: 0, ecg_abnormal: 0, risk_probability: 0.2625, risk_tier_label: "低危", top_reasons: "收缩压;脉压;男性", next_follow_up_days: 365, referral: "无症状时不建议常规上转" },
  { patient_id: "11535", age: 79, sex: "女", sbp: 130, dbp: 78, diabetes: 0, hypertension: 1, ecg_abnormal: 0, risk_probability: 0.1493, risk_tier_label: "低危", top_reasons: "收缩压;年龄;高血压", next_follow_up_days: 365, referral: "无症状时不建议常规上转" },
  { patient_id: "13553", age: 81, sex: "男", sbp: 125, dbp: 79, diabetes: 1, hypertension: 1, ecg_abnormal: 1, risk_probability: 0.3271, risk_tier_label: "中危", top_reasons: "心电图异常;糖尿病;年龄;脉压", next_follow_up_days: 180, referral: "指标持续异常或症状提示时建议专科咨询" },
  { patient_id: "27991", age: 72, sex: "女", sbp: 130, dbp: 78, diabetes: 0, hypertension: 1, ecg_abnormal: 1, glucose: 5.93, risk_probability: 0.5584, risk_tier_label: "中危", top_reasons: "有任一检验;心电图异常;收缩压;有血糖检验", next_follow_up_days: 180, referral: "指标持续异常或症状提示时建议专科咨询" },
  { patient_id: "3662", age: 72, sex: "女", sbp: 150, dbp: 89, diabetes: 1, hypertension: 1, ldl_c: 2.47, ecg_abnormal: 0, risk_probability: 0.616, risk_tier_label: "高危", top_reasons: "收缩压;有任一检验;有血脂检验;脉压", next_follow_up_days: 90, referral: "建议心血管专科复核" },
  { patient_id: "13520", age: 83, sex: "女", sbp: 117, dbp: 61, diabetes: 1, hypertension: 0, ecg_abnormal: 1, glucose: 7.5, risk_probability: 0.6124, risk_tier_label: "高危", top_reasons: "有任一检验;心电图异常;糖尿病;脉压", next_follow_up_days: 90, referral: "建议心血管专科复核" },
];

// ===== 状态 =====
let queue = [...QUEUE];
let activeId = null;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ===== 渲染队列 =====
function renderQueue() {
  const keyword = ($("search").value || "").trim().toLowerCase();
  const list = queue.filter((p) =>
    String(p.patient_id).toLowerCase().includes(keyword) ||
    String(p.age).includes(keyword) || (p.risk_tier_label || "").includes(keyword)
  );
  $("queue").innerHTML = list.map((p) => {
    const t = TIER_STYLE[p.risk_tier_label] || TIER_STYLE["低危"];
    return `<li class="${p.patient_id === activeId ? "active" : ""}" onclick="openDetail('${esc(p.patient_id)}')">
      <div class="q-top">
        <span class="q-id">患者 ${esc(p.patient_id)}</span>
        <span class="pill" style="background:${t.bg};color:${t.color}">${t.icon} ${esc(p.risk_tier_label)}</span>
      </div>
      <div class="q-meta">${p.age} 岁 · ${p.sex} · 风险 ${(p.risk_probability * 100).toFixed(1)}% · ${p.next_follow_up_days} 天复评</div>
    </li>`;
  }).join("") || '<li class="q-meta" style="padding:10px">无匹配患者</li>';
}

// ===== 结果卡渲染 =====
function renderResult(p) {
  const t = TIER_STYLE[p.risk_tier_label] || TIER_STYLE["低危"];
  const gauge = `conic-gradient(${t.color} ${(p.risk_probability * 100).toFixed(1)}%, #e8edf3 0)`;
  const reasons = Array.isArray(p.reasons) && p.reasons.length
    ? p.reasons.slice(0, 5).map((reason) => ({
        label: reason.label || reason.feature,
        contribution: Number(reason.contribution) || 0,
      }))
    : (p.top_reasons || "").split(";").filter(Boolean).slice(0, 5)
        .map((label) => ({ label, contribution: 1 }));
  const maxReason = Math.max(...reasons.map((reason) => reason.contribution), 0.01);
  $("detail-name").textContent = `患者 ${p.patient_id} · 风险评估报告`;
  $("detail-sub").textContent = `${p.age} 岁 · ${p.sex} · ${p.model_source || "训练模型"}${p.reference_date ? " · " + p.reference_date : ""}`;
  $("detail-body").innerHTML = `
  <div class="result-grid">
    <div class="risk-card">
      <div class="gauge-wrap"><div class="gauge" style="background:${gauge}">
        <div class="gauge-core">
          <div class="gauge-num">${(p.risk_probability * 100).toFixed(1)}%</div>
          <div class="gauge-unit">住院风险概率</div>
        </div>
      </div></div>
      <div class="tier-badge" style="background:${t.color}">${t.icon} ${esc(p.risk_tier_label)}</div>
      <div class="tier-desc">${esc(t.desc)}</div>
    </div>
    <div>
      <div class="detail-card">
        <h3>主要风险因素</h3>
        ${reasons.length ? reasons.map((reason) => {
          const width = Math.max(8, Math.min(100, reason.contribution / maxReason * 100));
          const value = reason.contribution === 1 ? "+1" : `+${reason.contribution.toFixed(2)}`;
          const row = `<div class="reason-row"><span>${esc(reason.label)}</span><div class="reason-bar"><i style="width:${width}%;background:${t.color}"></i></div><span class="reason-val">${value}</span></div>`;
          return row;
        }).join("") : '<p class="muted">—</p>'}
      </div>
      <div class="detail-card" style="margin-top:14px">
        <h3>管理建议</h3>
        <div class="kv"><span>管理责任方</span><b class="val">${esc(p.plan_owner || "社区卫生服务中心/家庭医生团队")}</b></div>
        <div class="kv"><span>建议复评时间</span><b class="val">${p.next_follow_up_days || "—"} 天</b></div>
        <div class="kv"><span>转诊建议</span><b class="val">${esc(p.referral || "—")}</b></div>
      </div>
      <p class="note">模型：${esc(p.model_source || "trained")} · 结果用于辅助分层管理，不替代临床判断。真实数据使用时需伦理与临床审批。</p>
    </div>
  </div>`;
}

function openDetail(id) {
  const p = queue.find((x) => String(x.patient_id) === String(id));
  if (!p) return;
  activeId = p.patient_id;
  $("view-form").classList.add("hidden");
  $("view-detail").classList.remove("hidden");
  renderResult(p);
  renderQueue();
}

// ===== 新评估表单 =====
const SAMPLE = {
  patient_id: "PAT-001", age: 68, sex: "男", bmi: 26.8, sbp: 152, dbp: 88,
  total_chol: 5.7, ldl_c: 3.6, hdl_c: 0.92, triglyceride: 1.9,
  fasting_glucose: 7.4, glucose: 8.1, hba1c: 7.2, creatinine: 92, uric_acid: 430, bun: 6.8,
  smoker: true, diabetes: true, hypertension: true, ecg_abnormal: true,
  chest_pain_visit_last_year: true, family_history_chd: true,
  statin_adherence_gap: true, medication_adherence_rate: 0.62,
  outpatient_visits_12m: 8, emergency_visits_12m: 1,
};

function showForm() {
  $("view-detail").classList.add("hidden");
  $("view-form").classList.remove("hidden");
}
function loadSample() {
  for (const [k, v] of Object.entries(SAMPLE)) {
    const el = document.querySelector(`[name="${k}"]`);
    if (!el) continue;
    if (el.type === "checkbox") el.checked = Boolean(v);
    else el.value = v ?? "";
  }
}
function collectForm() {
  const payload = {};
  for (const el of document.querySelectorAll("#assess-form [name]")) {
    const name = el.name;
    if (el.type === "checkbox") { payload[name] = el.checked; continue; }
    if (el.value === "" || el.value == null) { payload[name] = null; continue; }
    payload[name] = el.type === "number" ? Number(el.value) : el.value;
  }
  return payload;
}

async function submitAssessment(ev) {
  ev.preventDefault();
  const payload = collectForm();
  const btn = document.querySelector('#assess-form button[type="submit"]');
  btn.disabled = true; btn.textContent = "评估中…";
  try {
    let result;
    const resp = await fetch("/assess", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || ("HTTP " + resp.status));
    }
    result = await resp.json();
    updateModelBadge({
      model_ready: String(result.model_source || "").startsWith("trained:"),
      model_status: String(result.model_source || "").startsWith("trained:") ? "trained" : "fallback",
      model_source: result.model_source,
    });
    // 映射到详情视图
    queue = [{ ...result, patient_id: result.patient_id, risk_probability: result.probability, risk_tier_label: result.tier_label, top_reasons: (result.reasons || []).map(r => r.label).join(";"), next_follow_up_days: result.management_plan.follow_up_days, referral: result.management_plan.referral, plan_owner: result.management_plan.owner, model_source: result.model_source, age: payload.age, sex: payload.sex }, ...queue];
    openDetail(result.patient_id);
    toast("评估完成 ✓");
  } catch (err) {
    updateModelBadge(null);
    toast("评估失败：" + err.message + "（请确认后端已启动：uvicorn chd_risk.api:app --reload）");
  } finally {
    btn.disabled = false; btn.textContent = "开始评估 →";
  }
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg; el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 4000);
}

// ===== 模型徽章 =====
function updateModelBadge(info) {
  const badge = $("model-badge");
  badge.classList.remove("ok", "warn", "offline");
  if (!info) {
    badge.textContent = "后端未连接";
    badge.classList.add("offline");
    badge.title = "无法连接本机评估服务";
    return;
  }
  if (info.model_ready) {
    badge.textContent = "训练模型已加载";
    badge.classList.add("ok");
    badge.title = info.model_source || "训练模型可用";
    return;
  }
  badge.textContent = "规则模型（训练模型不可用）";
  badge.classList.add("warn");
  badge.title = info.model_error
    ? `训练模型加载失败：${info.model_error}`
    : "未找到训练模型，当前使用规则模型";
}

async function loadModelInfo() {
  try {
    const r = await fetch("/health");
    if (r.ok) {
      updateModelBadge(await r.json());
      return;
    }
  } catch (_) { /* ignore */ }
  updateModelBadge(null);
}

// ===== 初始化 =====
$("search").addEventListener("input", renderQueue);
$("btn-new-assess").addEventListener("click", showForm);
$("btn-back").addEventListener("click", () => { activeId = null; $("view-form").classList.add("hidden"); $("view-detail").classList.remove("hidden"); renderResult(queue[0]); renderQueue(); });
$("btn-load-sample").addEventListener("click", loadSample);
$("assess-form").addEventListener("submit", submitAssessment);
loadModelInfo();
setInterval(loadModelInfo, 30000);
renderQueue();
if (queue.length) openDetail(queue[0].patient_id);
