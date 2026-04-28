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
    rows = "\n".join(_task_card(task) for task in tasks) or "<p>No tasks.</p>"
    flash_html = f'<p class="flash">{escape(flash)}</p>' if flash else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IM-Collab Agent Console</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; color: #182026; background: #f7f8fa; }}
    main {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ font-size: 24px; margin: 0 0 8px; }}
    .meta, .muted {{ color: #5c6670; font-size: 13px; }}
    .flash {{ background: #e6f4ea; border: 1px solid #b7dfc1; padding: 8px 10px; border-radius: 6px; }}
    .task {{ background: #fff; border: 1px solid #d9dee3; border-radius: 8px; padding: 14px; margin: 12px 0; }}
    .title {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }}
    .state {{ font-size: 12px; padding: 2px 7px; border-radius: 999px; background: #eef2f6; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 6px 14px; margin: 10px 0; }}
    form {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    input, select, button {{ font: inherit; padding: 7px 8px; border: 1px solid #c8d0d8; border-radius: 6px; }}
    button {{ background: #1f6feb; color: white; border-color: #1f6feb; cursor: pointer; }}
    .secondary {{ background: #59636e; border-color: #59636e; }}
    .danger {{ background: #b42318; border-color: #b42318; }}
  </style>
</head>
<body>
<main>
  <h1>IM-Collab Agent Console</h1>
  <p class="meta">events: {events.total}</p>
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
        append_control_command(task_dir, "append_instruction", {"text": _required(form, "text")}, operator="operator")
        return f"append queued for {task_id}"
    if action == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        return f"interrupt queued for {task_id}"
    if action == "ack":
        ack_task(task_dir, operator="operator", note=form.get("note", ""))
        return f"ack saved for {task_id}"
    if action == "retry":
        retry(
            task_dir,
            generator=form.get("generator") or "app-server",
            publish=form.get("publish") in {"1", "true", "on"},
        )
        return f"retry started for {task_id}"
    raise ValueError(f"unsupported action: {action}")


def _task_card(task: Any) -> str:
    facts = [
        ("updated", task.updated_at),
        ("session", task.session_key),
        ("thread", task.codex_thread_id),
        ("turn", task.active_turn_id),
        ("control", f"{task.control_count} queued" if task.control_count else ""),
        ("ack", task.ack_operator),
        ("document", task.document_url),
        ("slides", task.slides_url),
        ("whiteboard", task.whiteboard_token),
    ]
    fact_html = "\n".join(
        f"<div><strong>{escape(label)}:</strong> {escape(value)}</div>" for label, value in facts if value
    )
    error_html = f'<p class="muted">error: {escape(task.error)}</p>' if task.error else ""
    return f"""<section class="task">
  <div class="title"><h2>{escape(task.task_id)}</h2><span class="state">{escape(task.state)}</span></div>
  <div class="grid">{fact_html}</div>
  {error_html}
  {_append_form(task.task_id)}
  {_interrupt_ack_retry_form(task.task_id)}
</section>"""


def _append_form(task_id: str) -> str:
    escaped_task_id = escape(task_id)
    return f"""<form method="post">
    <input type="hidden" name="action" value="append">
    <input type="hidden" name="task_id" value="{escaped_task_id}">
    <input name="text" placeholder="追加指令" required>
    <button type="submit">Append</button>
  </form>"""


def _interrupt_ack_retry_form(task_id: str) -> str:
    escaped_task_id = escape(task_id)
    return f"""<form method="post">
    <input type="hidden" name="task_id" value="{escaped_task_id}">
    <button class="danger" name="action" value="interrupt" type="submit">Interrupt</button>
    <input name="note" placeholder="确认备注">
    <button class="secondary" name="action" value="ack" type="submit">Ack</button>
    <select name="generator">
      <option value="app-server">app-server</option>
      <option value="codex">codex</option>
      <option value="local">local</option>
    </select>
    <label><input type="checkbox" name="publish" value="1"> publish</label>
    <button name="action" value="retry" type="submit">Retry</button>
  </form>"""


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value
