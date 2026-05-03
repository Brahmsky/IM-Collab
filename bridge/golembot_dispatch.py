from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import is_card_action_event, parse_card_action_event, parse_im_event
from bridge.feishu_delivery import publish_task_artifacts_to_feishu
from bridge.golembot_forwarder import forward_event_to_golembot
from bridge.golembot_office_loop import run_golembot_office_task
from bridge.lark_im import list_chat_messages
from bridge.lark_im import build_delivery_markdown, reply_to_message
from bridge.lark_im import reply_card_to_message
from bridge.task_binding import get_task_binding
from bridge.task_binding import build_golembot_session_key
from bridge.task_control import append_control_command
from bridge.task_protocol import read_status

Forwarder = Callable[..., dict[str, Any]]
Replier = Callable[[str, str, str, bool], dict[str, Any]]
CardReplier = Callable[[str, Path, str, bool], dict[str, Any]]
Publisher = Callable[[Path], dict[str, Any]]
OfficeRunner = Callable[..., dict[str, Any]]
ContextReader = Callable[..., list[dict[str, Any]]]


def dispatch_event_via_golembot(
    event_path: Path,
    gateway_url: str,
    token: str,
    publish: bool = False,
    generator: str = "app-server",
    execute_reply: bool = False,
    tasks_root: Path = Path("tasks"),
    forwarder: Forwarder = forward_event_to_golembot,
    office_runner: OfficeRunner = run_golembot_office_task,
    publisher: Publisher = publish_task_artifacts_to_feishu,
    replier: Replier = reply_to_message,
    card_replier: CardReplier = reply_card_to_message,
    context_reader: ContextReader = list_chat_messages,
) -> dict[str, Any]:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    if is_card_action_event(payload):
        return _dispatch_card_action(
            payload,
            publish=publish,
            generator=generator,
            execute_reply=execute_reply,
            tasks_root=tasks_root,
            office_runner=office_runner,
            publisher=publisher,
            replier=replier,
            card_replier=card_replier,
        )
    parsed = parse_im_event(payload)
    session_key = build_golembot_session_key("feishu", parsed.chat_id, parsed.sender_open_id, parsed.chat_type)
    active_result = _append_to_active_turn_if_available(tasks_root, session_key, parsed)
    if active_result is not None:
        reply_markdown = "收到，我会把这条补充进当前任务。"
        reply = replier(
            parsed.message_id,
            reply_markdown,
            f"{parsed.message_id}-golembot-active-turn",
            not execute_reply,
        )
        return {
            **active_result,
            "session_key": session_key,
            "message_id": parsed.message_id,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }
    waiting_result = _append_to_waiting_task_if_available(tasks_root, session_key, parsed)
    if waiting_result is not None:
        reply_markdown = "收到，我会把这条补充进当前任务。"
        reply = replier(
            parsed.message_id,
            reply_markdown,
            f"{parsed.message_id}-golembot-waiting-append",
            not execute_reply,
        )
        return {
            **waiting_result,
            "session_key": session_key,
            "message_id": parsed.message_id,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }

    if publish:
        task_id = _task_id(parsed.message_id)
        task_result = office_runner(
            message=parsed.text,
            session_key=session_key,
            chat_id=parsed.chat_id,
            sender_id=parsed.sender_open_id,
            tasks_root=tasks_root,
            task_id=task_id,
            generator=generator,
            publish=False,
            conversation_context=_conversation_context(parsed, context_reader),
        )
        publish_result = None
        if task_result.get("state") == "waiting_for_user":
            reply_markdown = str(task_result.get("reply_markdown") or "我已完成群聊信息汇总，但需要你确认后再继续。")
            card_name = "confirmation_card.json"
        else:
            publish_result = publisher(Path(str(task_result["task_dir"])))
            reply_markdown = build_delivery_markdown(publish_result["artifacts"])
            card_name = "delivery_card.json"
        reply = _reply_with_optional_card(
            parsed.message_id,
            reply_markdown,
            f"{parsed.message_id}-golembot-forwarded",
            not execute_reply,
            task_dir=Path(str(task_result["task_dir"])),
            card_name=card_name,
            replier=replier,
            card_replier=card_replier,
        )
        return {
            "session_key": session_key,
            "message_id": parsed.message_id,
            "task": task_result,
            "publish": publish_result,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }

    forwarded = forwarder(payload, gateway_url, token, publish=False, generator=generator)
    response = forwarded.get("response", {})
    final_text = response.get("finalText", "") if isinstance(response, dict) else ""
    reply_markdown = str(final_text).strip()
    reply = _reply_with_optional_card(
        parsed.message_id,
        reply_markdown,
        f"{parsed.message_id}-golembot-forwarded",
        not execute_reply,
        task_dir=None,
        card_name="delivery_card.json",
        replier=replier,
        card_replier=card_replier,
    )
    return {**forwarded, "publish": None, "reply_markdown": reply_markdown, "reply": reply}


def _dispatch_card_action(
    payload: dict[str, Any],
    publish: bool,
    generator: str,
    execute_reply: bool,
    tasks_root: Path,
    office_runner: OfficeRunner,
    publisher: Publisher,
    replier: Replier,
    card_replier: CardReplier,
) -> dict[str, Any]:
    parsed = parse_card_action_event(payload)
    task_dir = tasks_root / parsed.task_id
    command = append_control_command(
        task_dir,
        "card_action",
        {
            "action": parsed.action,
            "message_id": parsed.message_id,
            "chat_id": parsed.chat_id,
            "sender_id": parsed.sender_open_id,
            "value": parsed.value,
        },
        operator="feishu_card",
    )
    if parsed.action == "start_task":
        task_result = office_runner(
            message="开始执行",
            session_key=f"feishu:{parsed.chat_id}",
            chat_id=parsed.chat_id,
            sender_id=parsed.sender_open_id,
            tasks_root=tasks_root,
            task_id=parsed.task_id,
            generator=generator,
            publish=False,
            conversation_context=[],
        )
        publish_result = publisher(Path(str(task_result["task_dir"]))) if publish else None
        if publish_result is not None:
            reply_markdown = build_delivery_markdown(publish_result["artifacts"])
            reply = _reply_with_optional_card(
                parsed.message_id,
                reply_markdown,
                f"{parsed.message_id}-card-start",
                not execute_reply,
                task_dir=Path(str(task_result["task_dir"])),
                card_name="delivery_card.json",
                replier=replier,
                card_replier=card_replier,
            )
        else:
            reply = replier(parsed.message_id, "已开始执行。", f"{parsed.message_id}-card-start", not execute_reply)
        return {"task_id": parsed.task_id, "control": command, "task": task_result, "publish": publish_result, "reply": reply}
    reply = replier(parsed.message_id, "已记录你的补充。", f"{parsed.message_id}-card-action", not execute_reply)
    return {"task_id": parsed.task_id, "control": command, "reply": reply}


def _reply_with_optional_card(
    message_id: str,
    markdown: str,
    idempotency_key: str,
    dry_run: bool,
    task_dir: Path | None,
    card_name: str,
    replier: Replier,
    card_replier: CardReplier,
) -> dict[str, Any]:
    card_path = task_dir / card_name if task_dir else None
    if card_path and card_path.exists():
        return card_replier(message_id, card_path, idempotency_key, dry_run)
    return replier(message_id, markdown, idempotency_key, dry_run)


def _append_to_active_turn_if_available(
    tasks_root: Path,
    session_key: str,
    parsed: Any,
) -> dict[str, Any] | None:
    binding = get_task_binding(tasks_root / "task-bindings.json", session_key)
    if not binding:
        return None
    task_id = binding.get("active_task_id")
    codex_thread_id = binding.get("codex_thread_id")
    active_turn_id = binding.get("active_turn_id")
    if not task_id or not codex_thread_id or not active_turn_id:
        return None
    command = append_control_command(
        tasks_root / str(task_id),
        "append_instruction",
        {
            "text": parsed.text,
            "message_id": parsed.message_id,
            "session_key": session_key,
            "chat_id": parsed.chat_id,
            "sender_id": parsed.sender_open_id,
            "codex_thread_id": codex_thread_id,
            "active_turn_id": active_turn_id,
        },
        operator="feishu",
    )
    return {"task_id": str(task_id), "control": command}


def _append_to_waiting_task_if_available(
    tasks_root: Path,
    session_key: str,
    parsed: Any,
) -> dict[str, Any] | None:
    binding = get_task_binding(tasks_root / "task-bindings.json", session_key)
    if not binding:
        return None
    task_id = binding.get("active_task_id")
    if not task_id:
        return None
    task_dir = tasks_root / str(task_id)
    try:
        status = read_status(task_dir)
    except Exception:
        return None
    if status.get("state") != "waiting_for_user":
        return None
    command = append_control_command(
        task_dir,
        "append_instruction",
        {
            "text": parsed.text,
            "message_id": parsed.message_id,
            "session_key": session_key,
            "chat_id": parsed.chat_id,
            "sender_id": parsed.sender_open_id,
        },
        operator="feishu",
    )
    return {"task_id": str(task_id), "control": command}


def _task_id(message_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "_.-" else "-" for char in message_id)
    return f"im-{safe}"


def _conversation_context(parsed: Any, context_reader: ContextReader) -> list[dict[str, Any]]:
    if parsed.chat_type not in {"group", "channel"}:
        return []
    messages = context_reader(parsed.chat_id, page_size=20)
    return [message for message in messages if message.get("message_id") != parsed.message_id]
