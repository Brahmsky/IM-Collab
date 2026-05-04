from __future__ import annotations

import json
import shutil
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
            {
                "source": "gui",
                "kind": "operator_followup",
                "text": _required(form, "text"),
            },
            operator="operator",
        )
        return ""

    if action == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        return ""

    if action == "ack":
        ack_task(task_dir, operator="operator", note=form.get("note", ""))
        return ""

    if action == "retry":
        retry(
            task_dir,
            generator=form.get("generator") or "local",
            publish=form.get("publish") in {"1", "true", "on"},
        )
        return ""

    if action == "rename_session":
        title = _required(form, "session_title")
        _rename_session(tasks_root / "task-bindings.json", form.get("session_key", ""), task_id, title)
        return ""

    if action == "delete_session":
        _delete_session(tasks_root, task_id, form.get("session_key", ""))
        return ""

    raise ValueError(f"unsupported action: {action}")


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value


def _read_bindings(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"task binding index root must be an object: {path}")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _write_bindings(path: Path, bindings: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rename_session(index_path: Path, session_key: str, task_id: str, title: str) -> None:
    bindings = _read_bindings(index_path)
    if not session_key:
        session_key = f"local:{task_id}"
    if session_key not in bindings:
        bindings[session_key] = {
            "session_key": session_key,
            "chat_id": "local",
            "chat_name": "本地会话",
            "active_task_id": None,
            "last_task_id": task_id,
        }
    bindings[session_key] = {**bindings[session_key], "session_title": title}
    _write_bindings(index_path, bindings)


def _delete_session(tasks_root: Path, task_id: str, session_key: str) -> None:
    bindings_path = tasks_root / "task-bindings.json"
    bindings = _read_bindings(bindings_path)
    if session_key:
        bindings.pop(session_key, None)
    else:
        bindings = {
            key: value
            for key, value in bindings.items()
            if value.get("active_task_id") != task_id and value.get("last_task_id") != task_id
        }
    _write_bindings(bindings_path, bindings)

    task_dir = tasks_root / task_id
    if not task_dir.exists():
        return
    archive_root = tasks_root / ".archived"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / task_id
    if destination.exists():
        suffix = 1
        while (archive_root / f"{task_id}-{suffix}").exists():
            suffix += 1
        destination = archive_root / f"{task_id}-{suffix}"
    shutil.move(task_dir.as_posix(), destination.as_posix())
