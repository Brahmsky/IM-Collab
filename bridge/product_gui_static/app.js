const state = {
  workspace: null,
  selectedSessionId: "",
  selected: null,
  query: "",
  toastTimer: null,
};

const $ = (selector) => document.querySelector(selector);

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

async function loadWorkspace() {
  state.workspace = await fetchJson("/api/workspace");
  state.selectedSessionId = state.selectedSessionId || state.workspace.selected_session_id;
  renderGroups();
  if (state.selectedSessionId) {
    await loadSession(state.selectedSessionId);
  }
}

async function loadSession(sessionId) {
  state.selectedSessionId = sessionId;
  state.selected = await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}`);
  renderGroups();
  renderSelected();
}

function renderGroups() {
  const root = $("#groupList");
  root.innerHTML = "";
  const query = state.query.trim().toLowerCase();
  for (const group of state.workspace?.groups || []) {
    const sessions = group.sessions.filter((session) => {
      if (!query) return true;
      return `${session.title} ${group.group_name} ${session.summary} ${session.session_id}`.toLowerCase().includes(query);
    });
    if (!sessions.length) continue;

    const section = document.createElement("section");
    section.className = "group";
    section.innerHTML = `
      <div class="group-header">
        <div class="group-title"><span class="icon">♙</span><span>${escapeHtml(group.group_name)}</span></div>
        <span>⌄</span>
      </div>
      <div class="session-list"></div>
    `;
    const list = section.querySelector(".session-list");
    for (const session of sessions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `session-btn ${session.session_id === state.selectedSessionId ? "active" : ""}`;
      button.dataset.sessionId = session.session_id;
      button.innerHTML = `
        <span class="session-name">${escapeHtml(session.title)}</span>
        <span class="session-time">${relativeTime(session.updated_at)}</span>
        <span class="session-dot"></span>
      `;
      button.addEventListener("click", () => loadSession(session.session_id));
      list.appendChild(button);
    }
    root.appendChild(section);
  }
}

function renderSelected() {
  const selected = state.selected;
  $("#sessionTitle").textContent = selected.title;
  $("#userBubble").textContent = selected.user_request || "等待任务输入";
  $("#agentMessage").textContent = selected.agent_messages?.[0] || "Agent 已接收任务。";

  const steps = $("#stepList");
  steps.innerHTML = "";
  for (const step of selected.execution_steps || []) {
    const li = document.createElement("li");
    li.className = `step-${step.status}`;
    li.innerHTML = `<span class="step-mark"></span><span>${escapeHtml(step.label)}</span>`;
    steps.appendChild(li);
  }

  const completed = selected.artifacts.filter((item) => item.status === "completed").length;
  $("#artifactSummary").textContent = `已生成 ${selected.artifacts.length} 个产物`;
  renderArtifacts($("#centerArtifacts"), selected.artifacts, true);
  renderArtifacts($("#sideArtifacts"), selected.artifacts, false);
  $("#artifactCount").textContent = String(selected.artifacts.length);
  renderMeta(selected, completed);
}

function renderMeta(selected) {
  const meta = $("#taskMeta");
  const detail = selected.task_detail;
  meta.innerHTML = `
    <dt>状态</dt><dd><span class="blue-dot"></span>${stateLabel(detail.state)}</dd>
    <dt>来源</dt><dd>♙ ${escapeHtml(selected.source_group || "-")}</dd>
    <dt>目标</dt><dd>${escapeHtml(detail.target || "-")}</dd>
    <dt>创建时间</dt><dd>${shortTime(detail.created_at)}</dd>
    <dt>任务 ID</dt><dd>${escapeHtml(detail.task_id || "-")}</dd>
  `;
}

function renderArtifacts(root, artifacts) {
  root.innerHTML = "";
  for (const item of artifacts) {
    const node = document.createElement(item.url ? "a" : "div");
    node.className = "artifact-card";
    if (item.url) {
      node.href = item.url;
      node.target = "_blank";
      node.rel = "noopener";
    }
    const letter = iconLetter(item.kind);
    node.innerHTML = `
      <span class="artifact-icon kind-${cssKind(item.kind)}">${letter}</span>
      <span>
        <span class="artifact-title">${escapeHtml(item.title)}</span>
        <span class="artifact-format">${escapeHtml(item.format_hint || item.kind)}</span>
      </span>
      <span class="artifact-status status-${item.status}">
        ${statusLabel(item.status)}<span class="status-ring"></span>
      </span>
    `;
    root.appendChild(node);
  }
}

async function submitComposer(event) {
  event.preventDefault();
  const input = $("#composerInput");
  const text = input.value.trim();
  if (!text || !state.selectedSessionId) return;
  await fetchJson(`/api/sessions/${encodeURIComponent(state.selectedSessionId)}/messages`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text}),
  });
  input.value = "";
  showToast("已追加到当前 Codex 会话");
  await loadSession(state.selectedSessionId);
}

async function refreshCurrentSession() {
  if (!state.selectedSessionId) {
    await loadWorkspace();
    showToast("已刷新工作区");
    return;
  }
  await loadSession(state.selectedSessionId);
  showToast("已刷新当前任务");
}

function openFirstArtifact() {
  const artifact = state.selected?.artifacts?.find((item) => item.url);
  if (!artifact) {
    showToast("当前任务没有可打开的远端产物");
    return;
  }
  window.open(artifact.url, "_blank", "noopener");
}

function focusArtifactList() {
  const root = $("#centerArtifacts");
  root.scrollIntoView({block: "center", behavior: "smooth"});
  const firstLink = root.querySelector("a.artifact-card");
  if (firstLink) firstLink.focus();
}

function toggleInspector() {
  $(".detail-card").classList.toggle("collapsed");
}

function toggleSidebar() {
  $("#app").classList.toggle("sidebar-collapsed");
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 1800);
}

function iconLetter(kind) {
  if (kind.includes("slide") || kind === "deck") return "P";
  if (kind.includes("text") || kind.includes("reply")) return "T";
  if (kind.includes("document") || kind.includes("brief")) return "D";
  return "A";
}

function cssKind(kind) {
  return String(kind || "artifact").replace(/[^a-z0-9_-]/gi, "-").toLowerCase();
}

function statusLabel(status) {
  return {
    completed: "已生成",
    generating: "生成中",
    pending: "待生成",
    failed: "失败",
  }[status] || status;
}

function stateLabel(status) {
  return {
    queued: "排队中",
    running: "生成中",
    waiting_for_user: "待确认",
    completed: "已完成",
    failed: "失败",
  }[status] || status;
}

function shortTime(value) {
  if (!value) return "-";
  if (value.includes("T")) {
    return value.split("T")[1].slice(0, 5);
  }
  return value;
}

function relativeTime(value) {
  if (!value) return "";
  if (value.includes("2026-05-03")) return "今天";
  if (value.includes("2026-05-02")) return "昨天";
  return shortTime(value);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

$("#sessionSearch").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderGroups();
});
$("#composer").addEventListener("submit", submitComposer);
$(".collapse-btn").addEventListener("click", toggleSidebar);
$("#sessionTitle").addEventListener("click", () => $("#sessionSearch").focus());
$("#refreshSession").addEventListener("click", () => refreshCurrentSession().catch((error) => showToast(error.message)));
$("#openArtifact").addEventListener("click", openFirstArtifact);
$(".panel-title button").addEventListener("click", toggleInspector);
$(".all-artifacts").addEventListener("click", focusArtifactList);
$(".settings").addEventListener("click", () => showToast(`${state.workspace?.total_sessions || 0} 个真实会话`));

loadWorkspace().catch((error) => {
  console.error(error);
  $("#agentMessage").textContent = `无法加载 Agent-Pilot 数据：${error.message}`;
});
