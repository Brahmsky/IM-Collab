from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import parse_im_event
from bridge.feishu_delivery import publish_task_artifacts_to_feishu
from bridge.golembot_forwarder import extract_reply_markdown, forward_event_to_golembot
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
        if publish and _is_start_command(parsed.text):
            task_result = office_runner(
                message=parsed.text,
                session_key=session_key,
                chat_id=parsed.chat_id,
                sender_id=parsed.sender_open_id,
                tasks_root=tasks_root,
                task_id=str(waiting_result["task_id"]),
                generator=generator,
                publish=False,
                conversation_context=[],
            )
            publish_result = None
            if task_result.get("state") == "waiting_for_user":
                reply_markdown = str(task_result.get("reply_markdown") or "我已记录确认，但仍需要补充信息后再继续。")
            else:
                publish_result = publisher(Path(str(task_result["task_dir"])))
                reply_markdown = build_delivery_markdown(publish_result["artifacts"])
            reply = _reply_with_optional_card(
                parsed.message_id,
                reply_markdown,
                f"{parsed.message_id}-golembot-waiting-start",
                not execute_reply,
                task_dir=Path(str(task_result["task_dir"])),
                card_name="delivery_card.json",
                replier=replier,
                card_replier=card_replier,
            )
            return {
                **waiting_result,
                "session_key": session_key,
                "message_id": parsed.message_id,
                "task": task_result,
                "publish": publish_result,
                "reply_markdown": reply_markdown,
                "reply": reply,
            }
        reply_markdown = "已记录这条确认。我会在继续执行时把它纳入当前任务。"
        reply = replier(
            parsed.message_id,
            reply_markdown,
            f"{parsed.message_id}-golembot-waiting-confirmation",
            not execute_reply,
        )
        return {
            **waiting_result,
            "session_key": session_key,
            "message_id": parsed.message_id,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }

    if publish and _is_office_deliverable(parsed.text):
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
    reply_markdown = extract_reply_markdown(str(final_text))
    publish_result = None
    if publish and reply_markdown.startswith("任务 `"):
        publish_result = _publish_bound_task(tasks_root, str(forwarded["session_key"]), publisher)
        reply_markdown = build_delivery_markdown(publish_result["artifacts"])
    task_dir = _bound_task_dir(tasks_root, str(forwarded["session_key"])) if publish_result else None
    reply = _reply_with_optional_card(
        parsed.message_id,
        reply_markdown,
        f"{parsed.message_id}-golembot-forwarded",
        not execute_reply,
        task_dir=task_dir,
        card_name="delivery_card.json",
        replier=replier,
        card_replier=card_replier,
    )
    return {**forwarded, "publish": publish_result, "reply_markdown": reply_markdown, "reply": reply}


def _publish_bound_task(tasks_root: Path, session_key: str, publisher: Publisher) -> dict[str, Any]:
    return publisher(_bound_task_dir(tasks_root, session_key))


def _bound_task_dir(tasks_root: Path, session_key: str) -> Path:
    binding = get_task_binding(tasks_root / "task-bindings.json", session_key)
    task_id = binding.get("active_task_id") if binding else None
    if not task_id:
        raise RuntimeError(f"no active task binding for session {session_key}")
    return tasks_root / str(task_id)


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
        "confirm_instruction",
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


def _is_office_deliverable(text: str) -> bool:
    action_terms = ("生成", "整理", "创建", "输出", "做", "写")
    artifact_terms = ("文档", "方案", "演示稿", "PPT", "幻灯片", "白板", "流程", "纪要", "报告")
    if any(term in text for term in action_terms) and any(term in text for term in artifact_terms):
        return True
    return "IM-Collab" in text and "6" in text


def _is_start_command(text: str) -> bool:
    normalized = " ".join(text.split())
    return any(term in normalized for term in ("开始执行", "开始生成", "确认开始", "开始做"))


def _task_id(message_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "_.-" else "-" for char in message_id)
    return f"im-{safe}"


def _conversation_context(parsed: Any, context_reader: ContextReader) -> list[dict[str, Any]]:
    if parsed.chat_type not in {"group", "channel"}:
        return []
    messages = context_reader(parsed.chat_id, page_size=20)
    return [message for message in messages if message.get("message_id") != parsed.message_id]
