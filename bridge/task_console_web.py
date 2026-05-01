from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Callable

from bridge.task_control import append_control_command
from bridge.task_index import build_task_index, summarize_events
from bridge.task_ops import ack_task, retry_golembot_task

RetryFunc = Callable[..., dict[str, Any]]


def render_console_html(tasks_root: Path, event_dir: Path, flash: str = "") -> str:
    tasks = build_task_index(tasks_root)
    events = summarize_events(event_dir)
    rows = "\n".join(_task_card(task) for task in tasks) or _empty_state()
    flash_html = f'<p class="flash">{escape(flash)}</p>' if flash else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent-Pilot 多端协同办公助手</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --card: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --primary: #2563eb;
      --primary-soft: #dbeafe;
      --green: #16a34a;
      --green-soft: #dcfce7;
      --red: #dc2626;
      --red-soft: #fee2e2;
      --yellow: #ca8a04;
      --yellow-soft: #fef9c3;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, #e0f2fe 0, transparent 32%),
        linear-gradient(180deg, #f8fafc 0%, var(--bg) 100%);
    }}

    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 24px 56px;
    }}

    h1 {{
      font-size: 34px;
      margin: 0;
      letter-spacing: -0.04em;
    }}

    h2 {{
      font-size: 26px;
      margin: 4px 0 0;
      letter-spacing: -0.02em;
    }}

    h3 {{
      margin: 0 0 12px;
      font-size: 16px;
    }}

    .meta,
    .muted {{
      color: var(--muted);
      font-size: 13px;
    }}

    .hero {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      margin-bottom: 24px;
    }}

    .hero-subtitle {{
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 15px;
    }}

    .hero-card {{
      min-width: 260px;
      background: rgba(255, 255, 255, 0.86);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 20px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
    }}

    .hero-card strong {{
      display: block;
      margin-bottom: 8px;
    }}

    .flash {{
      background: var(--green-soft);
      border: 1px solid #86efac;
      padding: 10px 12px;
      border-radius: 12px;
      margin: 16px 0;
    }}

    .empty {{
      background: white;
      border: 1px dashed #cbd5e1;
      border-radius: 22px;
      padding: 36px;
      text-align: center;
      color: var(--muted);
    }}

    .task {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      margin: 22px 0;
      box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
    }}

    .task-head {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      margin-bottom: 24px;
    }}

    .eyebrow {{
      margin: 0 0 10px;
      color: var(--primary);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .state {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      padding: 8px 14px;
      border-radius: 999px;
      background: #eef2f6;
      color: #334155;
      white-space: nowrap;
      font-weight: 700;
    }}

    .state-completed {{
      background: var(--green-soft);
      color: #166534;
    }}

    .state-running {{
      background: var(--primary-soft);
      color: #1d4ed8;
    }}

    .state-waiting_for_user {{
      background: var(--yellow-soft);
      color: #854d0e;
    }}

    .state-failed {{
      background: var(--red-soft);
      color: #991b1b;
    }}

    .task-grid {{
      display: grid;
      grid-template-columns: 1.2fr 1fr 1fr;
      gap: 18px;
    }}

    .panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: #ffffff;
      padding: 20px;
      min-height: 280px;
    }}

    .panel h3 {{
      margin-bottom: 16px;
      font-size: 15px;
      letter-spacing: -0.02em;
    }}

    .chat-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .chat-bubble {{
      padding: 14px 16px;
      border-radius: 20px;
      line-height: 1.7;
      font-size: 14px;
      max-width: 100%;
      white-space: pre-wrap;
    }}

    .chat-bubble.user {{
      align-self: flex-end;
      background: var(--primary);
      color: white;
      border-bottom-right-radius: 6px;
    }}

    .chat-bubble.agent {{
      align-self: flex-start;
      background: #f1f5f9;
      color: #0f172a;
      border-bottom-left-radius: 6px;
    }}

    .timeline {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}

    .timeline li {{
      position: relative;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 0;
      color: var(--muted);
    }}

    .timeline li::before {{
      content: "";
      width: 14px;
      height: 14px;
      border-radius: 999px;
      border: 2px solid #cbd5e1;
      background: white;
      flex: 0 0 auto;
    }}

    .timeline li.done {{
      color: #166534;
      font-weight: 650;
    }}

    .timeline li.done::before {{
      background: var(--green);
      border-color: var(--green);
    }}

    .timeline li.active {{
      color: #1d4ed8;
      font-weight: 700;
    }}

    .timeline li.active::before {{
      background: var(--primary);
      border-color: var(--primary);
      box-shadow: 0 0 0 6px var(--primary-soft);
    }}

    .timeline li.failed {{
      color: #991b1b;
      font-weight: 700;
    }}

    .timeline li.failed::before {{
      background: var(--red);
      border-color: var(--red);
    }}

    .summary-box {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: #f8fafc;
      color: #334155;
      line-height: 1.7;
      white-space: pre-wrap;
      margin-bottom: 16px;
    }}

    .understanding-list {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}

    .understanding-list li {{
      color: #334155;
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }}

    .understanding-list strong {{
      min-width: 72px;
      display: inline-block;
    }}

    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}

    .meta-grid div {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
      background: #f8fafc;
    }}

    .meta-grid span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }}

    .meta-grid strong {{
      color: var(--text);
      font-size: 14px;
    }}

    .artifact-grid {{
      display: grid;
      gap: 12px;
      margin-top: 16px;
    }}

    .artifact {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 16px;
      border: 1px dashed #cbd5e1;
      border-radius: 18px;
      color: var(--muted);
      text-decoration: none;
      background: #f8fafc;
    }}

    .artifact.ready {{
      border-style: solid;
      border-color: #93c5fd;
      background: #eff6ff;
      color: var(--text);
    }}

    .artifact strong {{
      color: var(--text);
    }}

    .task-footer {{
      display: grid;
      grid-template-columns: 1.4fr 0.6fr;
      gap: 18px;
      margin-top: 24px;
    }}

    .task-actions {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .task-input-form {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 16px;
    }}

    .task-input-form input {{
      min-width: 0;
      flex: 1;
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
    }}

    .task-input-form button {{
      padding: 14px 18px;
      border-radius: 16px;
      min-width: 160px;
    }}

    form {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }}

    input,
    select,
    button {{
      font: inherit;
      padding: 9px 11px;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
    }}

    button {{
      background: var(--primary);
      color: white;
      border-color: var(--primary);
      cursor: pointer;
      font-weight: 650;
    }}

    .secondary {{
      background: #475569;
      border-color: #475569;
    }}

    .danger {{
      background: var(--red);
      border-color: var(--red);
    }}

    .error {{
      color: #991b1b;
      background: var(--red-soft);
      border: 1px solid #fecaca;
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 13px;
    }}

    @media (max-width: 1024px) {{
      .task-grid {{
        grid-template-columns: 1fr;
      }}

      .task-footer {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 900px) {{
      .hero {{
        display: block;
      }}

      .hero-card {{
        margin-top: 16px;
      }}

      .task-input-form input {{
        min-width: 100%;
      }}
    }}
  </style>
</head>
<body>
<main>
  <div class="hero">
    <div>
      <p class="eyebrow">Agent-Pilot 办公助手</p>
      <h1>多端协同办公工作台</h1>
      <p class="hero-subtitle">用自然语言驱动 Agent，展示理解、执行与交付。</p>
    </div>
    <div class="hero-card">
      <strong>当前工作概览</strong>
      <p class="meta">IM 事件：{events.total} · 任务：{len(tasks)}</p>
      <p class="meta">最近任务：{escape(tasks[0].task_id) if tasks else '暂无'}</p>
    </div>
  </div>

  {flash_html}
  {rows}
</main>
</body>
</html>
"""


def handle_console_action(
    tasks_root: Path,
    form: dict[str, str],
    retry: RetryFunc = retry_golembot_task,
) -> str:
    action = form.get("action", "")
    task_id = _required(form, "task_id")
    task_dir = tasks_root / task_id

    if action == "append":
        append_control_command(
            task_dir,
            "append_instruction",
            {"text": _required(form, "text")},
            operator="operator",
        )
        return f"已为任务 {task_id} 追加指令"

    if action == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        return f"已向任务 {task_id} 发送打断指令"

    if action == "ack":
        ack_task(task_dir, operator="operator", note=form.get("note", ""))
        return f"已确认任务 {task_id}"

    if action == "retry":
        retry(
            task_dir,
            generator=form.get("generator") or "local",
            publish=form.get("publish") in {"1", "true", "on"},
        )
        return f"已重新启动任务 {task_id}"

    raise ValueError(f"unsupported action: {action}")


def _task_card(task: Any) -> str:
    error_html = f'<p class="error">错误：{escape(task.error)}</p>' if task.error else ""

    document = getattr(task, "document_url", "") or ""
    slides = getattr(task, "slides_url", "") or ""
    whiteboard = getattr(task, "whiteboard_token", "") or ""
    summary_text = escape(task.summary or "Agent 正在把群聊内容转为可交付的方案文档、演示稿与白板流程图。")

    return f"""<section class="task">
  <div class="task-head">
    <div>
      <p class="eyebrow">Agent 工作台</p>
      <h2>{escape(task.task_id)}</h2>
      <p class="muted">最后更新：{escape(task.updated_at or "-")}</p>
    </div>
    <div class="status-block">
      <span class="state state-{escape(task.state)}">{escape(_state_label(task.state))}</span>
      <p class="meta">Session：{escape(task.session_key or "本地演示")}</p>
    </div>
  </div>

  <div class="task-grid">
    <div class="panel">
      <h3>① 自然语言输入</h3>
      <div class="chat-list">
        <div class="chat-bubble user">{summary_text}</div>
        <div class="chat-bubble agent">Agent 已接收，请确认理解、进度与交付内容。</div>
      </div>
      {_append_form(task.task_id)}
    </div>

    <div class="panel">
      <h3>② Agent 理解</h3>
      <div class="summary-box">{summary_text}</div>
      <ul class="understanding-list">
        <li><strong>目标：</strong>生成比赛答辩材料</li>
        <li><strong>产物：</strong>方案文档 / 7 页答辩 PPT / 白板流程图</li>
        <li><strong>待确认：</strong>是否固定 7 页 PPT？是否采用流程图白板？</li>
      </ul>
      <div class="meta-grid">
        <div><span>最新操作</span><strong>{escape(task.last_control_type or "无")}</strong></div>
        <div><span>控制次数</span><strong>{task.control_count}</strong></div>
        <div><span>Codex 线程</span><strong>{escape(task.codex_thread_id or "-")}</strong><span class="muted">活跃回合：{escape(task.active_turn_id or "-")}</span></div>
      </div>
    </div>

    <div class="panel">
      <h3>③ 执行进度</h3>
      <ol class="timeline">
        <li class="{_step_class(task, "intent")}"><span>理解 IM 意图</span></li>
        <li class="{_step_class(task, "brief")}"><span>生成群聊 brief</span></li>
        <li class="{_step_class(task, "doc")}"><span>生成方案文档</span></li>
        <li class="{_step_class(task, "slides")}"><span>生成答辩 PPT</span></li>
        <li class="{_step_class(task, "whiteboard")}"><span>生成白板流程图</span></li>
        <li class="{_step_class(task, "delivery")}"><span>汇总交付</span></li>
      </ol>
      <p class="muted">{escape(task.summary or "正在生成中...")}</p>
    </div>
  </div>

  <div class="task-footer">
    <div class="panel">
      <h3>已生成产物</h3>
      <div class="artifact-grid">
        {_artifact_card("方案文档", document, "等待生成")}
        {_artifact_card("演示稿 PPT", slides, "等待生成")}
        {_artifact_card("白板流程图", whiteboard, "等待生成")}
      </div>
      {error_html}
    </div>
    <div class="task-actions">
      <div class="panel">
        <h3>人工接管 / 操作</h3>
        {_interrupt_ack_retry_form(task.task_id)}
      </div>
    </div>
  </div>
</section>"""


def _append_form(task_id: str) -> str:
    escaped_task_id = escape(task_id)

    return f"""<form method="post" class="task-input-form">
    <input type="hidden" name="action" value="append">
    <input type="hidden" name="task_id" value="{escaped_task_id}">
    <input name="text" placeholder="继续修改：把 PPT 改成更正式、适合比赛答辩" required>
    <button type="submit">发送给 Agent</button>
  </form>"""


def _interrupt_ack_retry_form(task_id: str) -> str:
    escaped_task_id = escape(task_id)

    return f"""<form method="post">
    <input type="hidden" name="task_id" value="{escaped_task_id}">
    <button class="danger" name="action" value="interrupt" type="submit">打断任务</button>
    <input name="note" placeholder="确认备注">
    <button class="secondary" name="action" value="ack" type="submit">确认</button>
    <select name="generator">
      <option value="local">local 本地演示</option>
      <option value="app-server">app-server</option>
      <option value="codex">codex</option>
    </select>
    <label><input type="checkbox" name="publish" value="1"> 发布到飞书</label>
    <button name="action" value="retry" type="submit">重试任务</button>
  </form>"""


def _state_label(state: str) -> str:
    labels = {
        "queued": "排队中",
        "running": "运行中",
        "waiting_for_user": "等待用户确认",
        "completed": "已完成",
        "failed": "失败",
    }
    return labels.get(state, state)


def _step_class(task: Any, step: str) -> str:
    state = task.state

    if state == "failed":
        return "failed"

    if step == "intent":
        return "done"

    if step == "brief":
        return "done" if state in {"running", "waiting_for_user", "completed"} else "todo"

    if step == "doc":
        return "done" if task.document_url or state == "completed" else ("active" if state == "running" else "todo")

    if step == "slides":
        return "done" if task.slides_url or state == "completed" else ("active" if state == "running" else "todo")

    if step == "whiteboard":
        return "done" if task.whiteboard_token or state == "completed" else ("active" if state == "running" else "todo")

    if step == "delivery":
        return "done" if state == "completed" else ("active" if state == "running" else "todo")

    return "todo"


def _artifact_card(title: str, value: str, empty: str) -> str:
    if value:
        safe_value = escape(value)

        if value.startswith("http"):
            return f"""<a class="artifact ready" href="{safe_value}" target="_blank">
        <strong>{escape(title)}</strong>
        <span>已生成，点击打开</span>
      </a>"""

        return f"""<div class="artifact ready">
        <strong>{escape(title)}</strong>
        <span>{safe_value}</span>
      </div>"""

    return f"""<div class="artifact">
        <strong>{escape(title)}</strong>
        <span>{escape(empty)}</span>
      </div>"""


def _empty_state() -> str:
    return """<div class="empty">
      <h2>暂无任务</h2>
      <p>请先运行本地 demo，或从飞书 IM 触发一个任务。</p>
    </div>"""


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value