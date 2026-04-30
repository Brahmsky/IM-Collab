from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import parse_im_event

ContextReader = Callable[..., list[dict[str, Any]]]


def normalize_feishu_message(payload: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_im_event(payload)
    raw_message = payload.get("event", {}).get("message", {}) if isinstance(payload.get("event"), dict) else {}
    sent_at = str(payload.get("timestamp") or raw_message.get("create_time") or payload.get("create_time") or "")
    return {
        "message_id": parsed.message_id,
        "chat_id": parsed.chat_id,
        "chat_type": parsed.chat_type,
        "sender_id": parsed.sender_open_id,
        "sender": parsed.sender_open_id,
        "sent_at": sent_at,
        "message_type": parsed.message_type,
        "content": parsed.text,
        "attachments": _attachments_from_payload(payload),
        "raw": payload,
    }


def build_standard_group_context(
    path: Path,
    chat_id: str | None = None,
    page_size: int | None = None,
) -> list[dict[str, Any]]:
    messages = _read_fixture_messages(path)
    if chat_id:
        messages = [message for message in messages if not message.get("chat_id") or message.get("chat_id") == chat_id]
    if page_size is not None:
        messages = messages[-page_size:]
    return messages


def read_fixture_context(path: Path, chat_id: str, page_size: int = 20) -> list[dict[str, Any]]:
    return build_standard_group_context(path, chat_id=chat_id, page_size=page_size)


def build_context_reader(
    fixture_path: Path | None,
    real_reader: ContextReader,
) -> ContextReader:
    if fixture_path is None:
        return real_reader

    def fixture_reader(chat_id: str, page_size: int = 20) -> list[dict[str, Any]]:
        return read_fixture_context(fixture_path, chat_id=chat_id, page_size=page_size)

    return fixture_reader


def _read_fixture_messages(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        messages = []
        for event_path in sorted(path.glob("*.json")):
            payload = _read_json(event_path)
            if isinstance(payload, dict):
                messages.append(normalize_feishu_message(payload))
        return messages
    if path.suffix == ".jsonl":
        return [_coerce_fixture_item(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = _read_json(path)
    if isinstance(data, list):
        return [_coerce_fixture_item(item) for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("messages"), list):
        return [_coerce_fixture_item(item) for item in data["messages"] if isinstance(item, dict)]
    if isinstance(data, dict):
        return [normalize_feishu_message(data)]
    raise ValueError(f"unsupported context fixture: {path}")


def _coerce_fixture_item(item: dict[str, Any]) -> dict[str, Any]:
    if "message_id" in item and "content" in item:
        return item
    return normalize_feishu_message(item)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _attachments_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    attachments = payload.get("attachments")
    if isinstance(attachments, list):
        return [attachment for attachment in attachments if isinstance(attachment, dict)]
    return []
