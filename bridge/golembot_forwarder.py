from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import ImEvent, parse_im_event
from bridge.task_binding import build_golembot_session_key

Transport = Callable[[str, str, dict[str, str]], dict[str, Any]]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_golembot_prompt(payload: dict[str, Any], publish: bool = False, generator: str = "app-server") -> str:
    event = parse_im_event(payload)
    session_key = _session_key(event)
    task_id = _task_id(event.message_id)
    publish_note = (
        "\nWhen possible, Codex should directly create or update the requested Feishu-native artifacts through `lark-cli` or other available office wheels, and persist their remote metadata into `artifacts.json`. Only fall back to a second publishing pass when direct remote execution is genuinely unavailable."
        if publish
        else ""
    )
    return f"""A Feishu IM message arrived through the lark-cli channel wheel.

Use the `golembot-task-protocol` skill for this request.

message_id: {event.message_id}
chat_id: {event.chat_id}
chat_type: {event.chat_type}
sender_id: {event.sender_open_id}
session_key: {session_key}

User message:
{event.text}

If this is a concrete office deliverable request, run:

cd {PROJECT_ROOT.as_posix()} && rtk .venv/bin/python scripts/run_golembot_office_task.py --message "{_shell_safe(event.text)}" --session-key "{session_key}" --chat-id "{event.chat_id}" --sender-id "{event.sender_open_id}" --task-id {task_id} --generator {generator}

Then send the returned `reply_markdown` as your final answer. Treat `artifacts.json` as the durable result contract, and prefer direct Feishu execution over local placeholder generation. If this is not an office task, answer normally and do not create a durable task.{publish_note}
"""


def forward_event_to_golembot(
    payload: dict[str, Any],
    gateway_url: str,
    token: str,
    publish: bool = False,
    generator: str = "app-server",
    transport: Transport | None = None,
) -> dict[str, Any]:
    event = parse_im_event(payload)
    session_key = _session_key(event)
    chat_payload = {"message": build_golembot_prompt(payload, publish=publish, generator=generator), "sessionKey": session_key}
    url = gateway_url.rstrip("/") + "/chat"
    response = transport(url, token, chat_payload) if transport else _post_chat(url, token, chat_payload)
    return {"session_key": session_key, "message_id": event.message_id, "response": response}


def _session_key(event: ImEvent) -> str:
    return build_golembot_session_key(
        channel_type="feishu",
        chat_id=event.chat_id,
        sender_id=event.sender_open_id,
        chat_type=event.chat_type,
    )


def _post_chat(url: str, token: str, payload: dict[str, str]) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        text = response.read().decode("utf-8")
    return _parse_sse_or_json(text)


def _parse_sse_or_json(text: str) -> dict[str, Any]:
    last_event: dict[str, Any] | None = None
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        raw = line.removeprefix("data:").strip()
        if raw:
            last_event = json.loads(raw)
    if last_event is not None:
        return last_event
    return json.loads(text)


def _shell_safe(value: str) -> str:
    return value.replace('"', '\\"')


def _task_id(message_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "_.-" else "-" for char in message_id)
    return f"im-{safe}"
