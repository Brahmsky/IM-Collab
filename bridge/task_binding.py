from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_golembot_session_key(
    channel_type: str,
    chat_id: str,
    sender_id: str,
    chat_type: str,
    thread_id: str | None = None,
) -> str:
    if channel_type == "slack" and chat_type in {"group", "channel"} and thread_id:
        return f"{channel_type}:{chat_id}:thread:{thread_id}"
    if channel_type == "feishu" and chat_type in {"group", "channel"} and thread_id:
        return f"{channel_type}:{chat_id}:session:{thread_id}"
    if chat_type in {"group", "channel"}:
        return f"{channel_type}:{chat_id}"
    if channel_type == "slack" and thread_id:
        return f"{channel_type}:{chat_id}:{sender_id}:thread:{thread_id}"
    return f"{channel_type}:{chat_id}:{sender_id}"


def get_task_binding(index_path: Path, session_key: str) -> dict[str, Any] | None:
    return _read_index(index_path).get(session_key)


def find_latest_active_group_session_binding(
    index_path: Path,
    channel_type: str,
    chat_id: str,
) -> dict[str, Any] | None:
    prefix = f"{channel_type}:{chat_id}:session:"
    candidates = [
        binding
        for key, binding in _read_index(index_path).items()
        if key.startswith(prefix) and binding.get("active_task_id")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda binding: str(binding.get("updated_at") or binding.get("created_at") or ""))


def bind_active_task(
    index_path: Path,
    session_key: str,
    task_id: str,
    chat_id: str,
    channel_type: str,
    sender_id: str,
    chat_name: str | None = None,
    codex_thread_id: str | None = None,
    active_turn_id: str | None = None,
    last_absorbed_message_id: str | None = None,
) -> dict[str, Any]:
    data = _read_index(index_path)
    current = data.get(session_key, {})
    now = _now()
    entry = {
        "session_key": session_key,
        "channel_type": channel_type,
        "chat_id": chat_id,
        "sender_id": sender_id,
        "chat_name": chat_name if chat_name is not None else current.get("chat_name"),
        "active_task_id": task_id,
        "last_task_id": current.get("last_task_id"),
        "codex_thread_id": codex_thread_id if codex_thread_id is not None else current.get("codex_thread_id"),
        "active_turn_id": active_turn_id if active_turn_id is not None else current.get("active_turn_id"),
        "last_absorbed_message_id": (
            last_absorbed_message_id
            if last_absorbed_message_id is not None
            else current.get("last_absorbed_message_id")
        ),
        "created_at": current.get("created_at", now),
        "updated_at": now,
    }
    data[session_key] = entry
    _write_index(index_path, data)
    return entry


def clear_active_task(index_path: Path, session_key: str) -> dict[str, Any]:
    data = _read_index(index_path)
    if session_key not in data:
        raise KeyError(f"unknown session: {session_key}")
    current = data[session_key]
    entry = {
        **current,
        "active_task_id": None,
        "active_turn_id": None,
        "last_task_id": current.get("active_task_id") or current.get("last_task_id"),
        "updated_at": _now(),
    }
    data[session_key] = entry
    _write_index(index_path, data)
    return entry


def _read_index(index_path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"task binding index root must be an object: {index_path}")
    return data


def _write_index(index_path: Path, data: dict[str, dict[str, Any]]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
