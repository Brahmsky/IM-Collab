from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bridge.artifacts import artifact_items
from bridge.task_control import read_control_commands

CHAT_MESSAGES_LOG = "chat_messages.jsonl"


def append_chat_message(
    task_dir: Path,
    role: str,
    text: str,
    *,
    timestamp: str | None = None,
    source: str = "",
) -> dict[str, Any]:
    value = text.strip()
    if not value:
        raise ValueError("chat message text must not be empty")
    if role not in {"user", "assistant"}:
        raise ValueError("chat message role must be user or assistant")
    message = {
        "timestamp": timestamp or datetime.now(UTC).isoformat(),
        "role": role,
        "text": value,
    }
    if source:
        message["source"] = source
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / CHAT_MESSAGES_LOG).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(message, ensure_ascii=False) + "\n")
    return message


def read_chat_messages(task_dir: Path) -> list[dict[str, Any]]:
    path = task_dir / CHAT_MESSAGES_LOG
    if not path.is_file():
        return []
    messages: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        text = str(message.get("text") or "").strip()
        if role in {"user", "assistant"} and text:
            messages.append({**message, "role": role, "text": text})
    return messages


def seed_chat_messages_from_task(
    task_dir: Path,
    *,
    created_at: str = "",
    assistant_text: str = "",
    assistant_timestamp: str = "",
) -> None:
    if (task_dir / CHAT_MESSAGES_LOG).is_file():
        return
    request = _task_request_message(task_dir)
    if request:
        append_chat_message(task_dir, "user", request, timestamp=created_at or None, source="request")
    if assistant_text.strip():
        append_chat_message(
            task_dir,
            "assistant",
            assistant_text,
            timestamp=assistant_timestamp or None,
            source="artifacts",
        )
    for command in read_control_commands(task_dir):
        if command.get("type") != "append_instruction":
            continue
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            append_chat_message(
                task_dir,
                "user",
                text,
                timestamp=str(command.get("timestamp") or ""),
                source="control",
            )


def assistant_text_from_artifacts(artifacts: dict[str, Any]) -> str:
    for item in artifact_items(artifacts):
        if str(item.get("kind") or "").lower() == "message":
            text = str(item.get("text") or "").strip()
            if text:
                return text
    return str(artifacts.get("summary") or "").strip()


def append_assistant_message_from_artifacts(task_dir: Path, artifacts: dict[str, Any]) -> dict[str, Any] | None:
    text = assistant_text_from_artifacts(artifacts)
    if not text:
        return None
    return append_chat_message(task_dir, "assistant", text, source="artifacts")


def _task_request_message(task_dir: Path) -> str:
    path = task_dir / "request.md"
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8")
    marker = "## User Message"
    if marker in raw:
        section = raw.split(marker, 1)[1]
        lines: list[str] = []
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            lines.append(line)
        return "\n".join(lines).strip()
    return raw.strip()
