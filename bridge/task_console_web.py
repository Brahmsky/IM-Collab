from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from bridge.cockpit_console_html import render_cockpit_document
from bridge.task_control import append_control_command
from bridge.task_index import build_task_index, summarize_events
from bridge.task_ops import ack_task, retry_golembot_task

RetryFunc = Callable[..., dict[str, Any]]


def render_console_html(
    tasks_root: Path,
    event_dir: Path,
    flash: str = "",
    *,
    selected_task_id: str | None = None,
    search_query: str = "",
) -> str:
    tasks = build_task_index(tasks_root)
    events = summarize_events(event_dir)
    return render_cockpit_document(
        tasks,
        events,
        flash,
        selected_task_id=selected_task_id,
        search_query=search_query,
    )


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


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value
