from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bridge.task_protocol import create_task


@dataclass(frozen=True)
class ImEvent:
    task_id: str
    message_id: str
    chat_id: str
    chat_type: str
    sender_open_id: str
    message_type: str
    text: str
    raw: dict[str, Any]


def parse_im_event(payload: dict[str, Any]) -> ImEvent:
    if payload.get("type") == "im.message.receive_v1" or "message_id" in payload:
        message_id = _require(payload, "message_id")
        return ImEvent(
            task_id=f"im-{_safe_id(message_id)}",
            message_id=message_id,
            chat_id=_require(payload, "chat_id"),
            chat_type=str(payload.get("chat_type", "")),
            sender_open_id=str(payload.get("sender_id", "")),
            message_type=str(payload.get("message_type", "")),
            text=str(payload.get("content", "")),
            raw=payload,
        )

    event = payload.get("event", payload)
    message = event.get("message", {})
    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    message_id = _require(message, "message_id")
    text = _extract_text(message)
    return ImEvent(
        task_id=f"im-{_safe_id(message_id)}",
        message_id=message_id,
        chat_id=_require(message, "chat_id"),
        chat_type=str(message.get("chat_type", "")),
        sender_open_id=str(sender_id.get("open_id", "")),
        message_type=str(message.get("message_type", "")),
        text=text,
        raw=payload,
    )


def create_task_from_event(payload: dict[str, Any], tasks_root: Path) -> Path:
    parsed = parse_im_event(payload)
    return create_task(tasks_root, parsed.task_id, _request_markdown(parsed))


def _request_markdown(event: ImEvent) -> str:
    return f"""# Feishu IM Request

message_id: {event.message_id}
chat_id: {event.chat_id}
chat_type: {event.chat_type}
sender_open_id: {event.sender_open_id}
message_type: {event.message_type}

## User Message

{event.text}

## Execution Boundary

Use Codex + superpowers as the only orchestration layer. Prefer Feishu CLI built-in skills, lark-openapi-mcp, and Presenton over local office logic.

## Acceptance Criteria

- Create or update Feishu document, slides, and whiteboard artifacts.
- Write final delivery metadata to artifacts.json.
- Reply to the source Feishu message with artifact links.
"""


def _extract_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            return content
    elif isinstance(content, dict):
        decoded = content
    else:
        return ""

    if isinstance(decoded, dict):
        if isinstance(decoded.get("text"), str):
            return decoded["text"]
        if isinstance(decoded.get("content"), str):
            return decoded["content"]
    return json.dumps(decoded, ensure_ascii=False)


def _require(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not value:
        raise ValueError(f"missing event field: {key}")
    return str(value)


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
