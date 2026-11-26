const API = (window.API_BASE_URL || "").replace(/\/$/, "");
const $ = (id) => document.getElementById(id);
const won = (n) => Number(n).toLocaleString("ko-KR") + "원";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let currentConv = null; // 현재 대화 id
let rows = [];
let shown = 20;
let editingId = null;

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = typeof j.detail === "string" ? j.detail : "입력값을 확인하세요."; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

/* ---------- 테마 ---------- */
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("themeBtn").textContent = t === "dark" ? "☀️" : "🌙";
  try { localStorage.setItem("theme", t); } catch {}
}
$("themeBtn").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
let saved = null;
try { saved = localStorage.getItem("theme"); } catch {}
applyTheme(saved || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

/* ---------- 요약 + 차트 ---------- */
async function loadSummary() {
  const s = await api("/api/data/summary");
  if (!s.count) { $("summary").textContent = "데이터가 없습니다. 아래에서 추가하세요."; return; }
  const m = s.metrics;
  $("summary").innerHTML =
    `기간: <b>${esc(s.period)}</b> · 개수: <b>${s.count}</b>개<br>` +
    `총합 ${won(m.total)} · 평균 ${won(m.average)} · 중앙값 ${won(m.median)} · 표준편차 ${won(m.stdev)}<br>` +
    `최대 ${won(m.max)} (${m.max_date}) · 최소 ${won(m.min)} (${m.min_date})<br>` +
    `트렌드: <b>${esc(s.trend)}</b>`;
}

async function loadChart() {
  const { series } = await api("/api/data/statistics");
  const c = $("chart"), g = c.getContext("2d");
  const css = getComputedStyle(document.documentElement);
  g.clearRect(0, 0, c.width, c.height);
  if (series.length < 2) return;
  const pad = 28, W = c.width - pad * 2, H = c.height - pad * 2;
  const vals = series.map((p) => p.value), max = Math.max(...vals), min = Math.min(...vals);
  const x = (i) => pad + (i / (series.length - 1)) * W;
  const y = (v) => pad + H - ((v - min) / (max - min || 1)) * H;
  g.strokeStyle = css.getPropertyValue("--accent"); g.lineWidth = 2; g.beginPath();
  series.forEach((p, i) => (i ? g.lineTo(x(i), y(p.value)) : g.moveTo(x(i), y(p.value))));
  g.stroke();
  g.fillStyle = css.getPropertyValue("--muted"); g.font = "11px sans-serif";
  g.fillText(won(max), 2, pad - 8); g.fillText(won(min), 2, c.height - 6);
  g.fillText(series[0].date, pad, c.height - 6);
  g.textAlign = "right"; g.fillText(series[series.length - 1].date, c.width - pad, c.height - 6); g.textAlign = "left";
}
new MutationObserver(() => loadChart().catch(() => {})).observe(document.documentElement, { attributes: true });

/* ---------- 데이터 CRUD ---------- */
function renderData() {
  $("dataBody").innerHTML = rows.slice().reverse().slice(0, shown).map((r) =>
    `<tr><td>${r.date}</td><td>${won(r.value)}</td><td>${esc(r.memo)}</td>` +
    `<td><button class="ghost" data-edit="${r.id}">수정</button> <button class="danger" data-del="${r.id}">삭제</button></td></tr>`
  ).join("");
  $("count").textContent = `${Math.min(shown, rows.length)} / ${rows.length}`;
  $("more").hidden = shown >= rows.length;
}

async function loadData() {
  rows = await api("/api/data");
  renderData();
}

function resetForm() {
  editingId = null;
  $("dataForm").reset();
  $("dSubmit").textContent = "추가";
  $("dCancel").hidden = true;
}

$("dataForm").onsubmit = async (e) => {
  e.preventDefault();
  const body = { date: $("dDate").value, value: Number($("dValue").value), memo: $("dMemo").value };
  try {
    if (editingId) { await api(`/api/data/${editingId}`, { method: "PUT", body }); toast("수정 완료"); }
    else { await api("/api/data", { method: "POST", body }); toast("추가 완료"); }
    resetForm();
    await Promise.all([loadData(), loadSummary(), loadChart()]);
  } catch (err) { toast("저장 실패: " + err.message); }
};
$("dCancel").onclick = resetForm;
$("more").onclick = () => { shown += 20; renderData(); };

$("dataBody").onclick = async (e) => {
  const edit = e.target.dataset.edit, del = e.target.dataset.del;
  if (edit) {
    const r = rows.find((x) => x.id === edit);
    editingId = edit;
    $("dDate").value = r.date; $("dValue").value = r.value; $("dMemo").value = r.memo;
    $("dSubmit").textContent = "수정 저장"; $("dCancel").hidden = false;
    $("dataForm").scrollIntoView({ behavior: "smooth" });
  } else if (del && confirm("삭제할까요?")) {
    try {
      await api(`/api/data/${del}`, { method: "DELETE" });
      toast("삭제 완료");
      await Promise.all([loadData(), loadSummary(), loadChart()]);
    } catch (err) { toast("삭제 실패: " + err.message); }
  }
};

/* 내보내기 (보너스) */
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
$("jsonBtn").onclick = () => download("data.json", JSON.stringify(rows, null, 2), "application/json");
$("csvBtn").onclick = () => {
  const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const csv = "﻿date,value,memo\n" + rows.map((r) => [r.date, r.value, q(r.memo)].join(",")).join("\n");
  download("data.csv", csv, "text/csv");
};

/* ---------- 채팅 ---------- */
function addMsg(role, content) {
  const d = document.createElement("div");
  d.className = "msg " + role; d.textContent = content;
  $("messages").appendChild(d);
  $("messages").scrollTop = $("messages").scrollHeight;
}

$("chatForm").onsubmit = async (e) => {
  e.preventDefault();
  const message = $("chatInput").value.trim();
  if (!message) return;
  $("chatInput").value = "";
  addMsg("user", message);
  $("loading").hidden = false;
  $("chatForm").querySelector("button").disabled = true;
  try {
    const r = await api("/api/chat", { method: "POST", body: { message, conversation_id: currentConv } });
    currentConv = r.conversation_id;
    addMsg("assistant", r.answer);
    loadConversations();
  } catch (err) {
    addMsg("assistant", "⚠️ " + err.message);
  } finally {
    $("loading").hidden = true;
    $("chatForm").querySelector("button").disabled = false;
  }
};

/* ---------- 대화 기록 ---------- */
async function loadConversations() {
  const list = await api("/api/conversations");
  $("convList").innerHTML = list.length
    ? list.map((c) =>
        `<li data-id="${c.id}" class="${c.id === currentConv ? "active" : ""}">` +
        `<span>${esc(c.title)} <small>(${c.message_count}개)</small></span>` +
        `<button class="danger" data-del="${c.id}">삭제</button></li>`).join("")
    : "<li>저장된 대화가 없습니다.</li>";
}

$("convList").onclick = async (e) => {
  const li = e.target.closest("li[data-id]");
  if (!li) return;
  const id = li.dataset.id;
  try {
    if (e.target.dataset.del) {
      if (!confirm("대화를 삭제할까요?")) return;
      await api(`/api/conversations/${id}`, { method: "DELETE" });
      if (id === currentConv) { currentConv = null; $("messages").innerHTML = ""; }
      toast("대화 삭제 완료");
    } else {
      const c = await api(`/api/conversations/${id}`);
      currentConv = id;
      $("messages").innerHTML = "";
      c.messages.forEach((m) => addMsg(m.role, m.content));
      toast("대화를 불러왔어요");
    }
    loadConversations();
  } catch (err) { toast("실패: " + err.message); }
};

$("newConv").onclick = () => { currentConv = null; $("messages").innerHTML = ""; loadConversations(); };

/* ---------- 시작 ---------- */
(async function init() {
  $("dDate").valueAsDate = new Date();
  try {
    await fetch(API + "/health"); // 콜드스타트 깨우기
    $("wake").hidden = true;
    await Promise.all([loadSummary(), loadChart(), loadData(), loadConversations()]);
  } catch (err) {
    $("wake").hidden = false;
    $("wake").textContent = "서버에 연결하지 못했어요: " + err.message;
  }
})();
