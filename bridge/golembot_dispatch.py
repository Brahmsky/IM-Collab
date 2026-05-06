from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from bridge.feishu_events import is_card_action_event, parse_card_action_event, parse_im_event
from bridge.feishu_delivery import publish_task_artifacts_to_feishu
from bridge.golembot_forwarder import forward_event_to_golembot
from bridge.golembot_office_loop import run_golembot_office_task
from bridge.group_session import collect_group_delta_context, collect_new_session_context, parse_new_session_command
from bridge.lark_chats import get_chat_name
from bridge.lark_im import list_chat_messages
from bridge.lark_im import build_delivery_markdown, reply_to_message
from bridge.lark_im import reply_card_to_message
from bridge.task_binding import get_task_binding
from bridge.task_binding import build_golembot_session_key
from bridge.task_binding import find_latest_active_group_session_binding
from bridge.task_binding import bind_active_task
from bridge.task_binding import clear_active_task
from bridge.task_control import append_control_command
from bridge.task_protocol import create_task, write_status
from bridge.task_protocol import read_status

Forwarder = Callable[..., dict[str, Any]]
Replier = Callable[[str, str, str, bool], dict[str, Any]]
CardReplier = Callable[[str, Path, str, bool], dict[str, Any]]
Publisher = Callable[[Path], dict[str, Any]]
OfficeRunner = Callable[..., dict[str, Any]]
ContextReader = Callable[..., list[dict[str, Any]]]
ChatNameResolver = Callable[..., str]


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
    chat_name_resolver: ChatNameResolver = get_chat_name,
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
    if not _is_group_message_addressed_to_bot(parsed):
        return {"ignored": True, "reason": "group message missing bot mention", "message_id": parsed.message_id}
    chat_name = _resolve_chat_name(parsed, chat_name_resolver)
    new_command = parse_new_session_command(parsed.text)
    session_key = build_golembot_session_key(
        "feishu",
        parsed.chat_id,
        parsed.sender_open_id,
        parsed.chat_type,
        thread_id=parsed.message_id if new_command is not None and parsed.chat_type in {"group", "channel"} else None,
    )
    active_session_key = _resolve_active_session_key(tasks_root, session_key, parsed, new_command)
    active_result = _append_to_active_turn_if_available(
        tasks_root,
        active_session_key,
        parsed,
        context_reader=context_reader,
    )
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
            "session_key": active_session_key,
            "message_id": parsed.message_id,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }
    waiting_result = _append_to_waiting_task_if_available(
        tasks_root,
        active_session_key,
        parsed,
        context_reader=context_reader,
    )
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
            "session_key": active_session_key,
            "message_id": parsed.message_id,
            "reply_markdown": reply_markdown,
            "reply": reply,
        }

    if publish:
        task_id = _task_id(parsed.message_id)
        try:
            conversation_context = _conversation_context(parsed, context_reader, new_command=new_command)
        except Exception as exc:
            if parsed.chat_type in {"group", "channel"} and _is_group_context_permission_error(exc):
                return _handle_group_context_permission_failure(
                    parsed,
                    tasks_root=tasks_root,
                    task_id=task_id,
                    session_key=session_key,
                    chat_name=chat_name,
                    error=exc,
                    execute_reply=execute_reply,
                    replier=replier,
                )
            raise
        task_result = office_runner(
            message=new_command.instruction if new_command is not None else parsed.text,
            session_key=session_key,
            chat_id=parsed.chat_id,
            sender_id=parsed.sender_open_id,
            chat_name=chat_name,
            tasks_root=tasks_root,
            task_id=task_id,
            generator=generator,
            publish=False,
            conversation_context=conversation_context,
            brief_extractor="langextract-deepseek" if parsed.chat_type in {"group", "channel"} else "rules",
            absorbed_message_id=parsed.message_id if parsed.chat_type in {"group", "channel"} else None,
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
        session_key = str(parsed.value.get("session_key") or f"feishu:{parsed.chat_id}")
        task_result = office_runner(
            message="开始执行",
            session_key=session_key,
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
        return {
            "task_id": parsed.task_id,
            "session_key": session_key,
            "control": command,
            "task": task_result,
            "publish": publish_result,
            "reply": reply,
        }
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


def _handle_group_context_permission_failure(
    parsed: Any,
    *,
    tasks_root: Path,
    task_id: str,
    session_key: str,
    chat_name: str,
    error: Exception,
    execute_reply: bool,
    replier: Replier,
) -> dict[str, Any]:
    task_dir = tasks_root / task_id
    if not task_dir.exists():
        create_task(tasks_root, task_id, _dispatch_failure_request_markdown(parsed, session_key))
    write_status(
        task_dir,
        "failed",
        error=f"无法读取群聊历史，缺少飞书权限: {error}",
    )
    binding = bind_active_task(
        tasks_root / "task-bindings.json",
        session_key=session_key,
        task_id=task_id,
        chat_id=parsed.chat_id,
        channel_type="feishu",
        sender_id=parsed.sender_open_id,
        chat_name=chat_name,
        last_absorbed_message_id=parsed.message_id,
    )
    clear_active_task(tasks_root / "task-bindings.json", session_key)
    reply_markdown = (
        "无法读取群聊历史，当前飞书 bot 缺少群聊历史读取权限。"
        "\n\n错误: `230027 Permission denied`"
        "\n\n请补齐应用权限并重新授权后再重试。"
    )
    reply = replier(
        parsed.message_id,
        reply_markdown,
        f"{parsed.message_id}-golembot-context-permission",
        not execute_reply,
    )
    return {
        "task_id": task_id,
        "task_dir": task_dir.as_posix(),
        "session_key": session_key,
        "binding": binding,
        "reply_markdown": reply_markdown,
        "reply": reply,
    }


def _dispatch_failure_request_markdown(parsed: Any, session_key: str) -> str:
    return f"""# GolemBot Dispatch Failure

session_key: {session_key}
chat_id: {parsed.chat_id}
sender_id: {parsed.sender_open_id}
message_id: {parsed.message_id}
chat_type: {parsed.chat_type}
message_type: {parsed.message_type}

## User Message

{parsed.text}
"""


def _is_group_context_permission_error(error: Exception) -> bool:
    text = str(error)
    return "Permission denied" in text or "need_user_authorization" in text or "230027" in text


def _is_group_message_addressed_to_bot(parsed: Any) -> bool:
    if parsed.chat_type not in {"group", "channel"}:
        return True
    raw_mentions = parsed.raw.get("mentions")
    if isinstance(raw_mentions, list) and raw_mentions:
        return True
    return str(parsed.text).lstrip().startswith("@")


def _resolve_chat_name(parsed: Any, chat_name_resolver: ChatNameResolver) -> str:
    if parsed.chat_name.strip():
        return parsed.chat_name.strip()
    if parsed.chat_type not in {"group", "channel"}:
        return ""
    try:
        return str(chat_name_resolver(parsed.chat_id, identity="user") or "").strip()
    except Exception:
        return ""


def _resolve_active_session_key(
    tasks_root: Path,
    session_key: str,
    parsed: Any,
    new_command: Any | None,
) -> str:
    if new_command is not None or parsed.chat_type not in {"group", "channel"}:
        return session_key
    if get_task_binding(tasks_root / "task-bindings.json", session_key):
        return session_key
    binding = find_latest_active_group_session_binding(
        tasks_root / "task-bindings.json",
        "feishu",
        parsed.chat_id,
    )
    if not binding:
        return session_key
    return str(binding.get("session_key") or session_key)


def _attach_group_delta_payload(
    payload: dict[str, Any],
    *,
    tasks_root: Path,
    session_key: str,
    binding: dict[str, Any],
    parsed: Any,
    context_reader: ContextReader | None,
) -> None:
    if parsed.chat_type not in {"group", "channel"} or context_reader is None:
        return
    last_absorbed_message_id = str(binding.get("last_absorbed_message_id") or "").strip()
    if not last_absorbed_message_id:
        return
    messages = _read_followup_context(parsed, context_reader, last_absorbed_message_id)
    delta = collect_group_delta_context(
        messages,
        last_absorbed_message_id=last_absorbed_message_id,
        trigger_message_id=parsed.message_id,
        max_messages=80,
    )
    if not delta:
        return
    payload["group_context"] = delta
    payload["codex_input_text"] = _compose_group_followup_input(parsed.text, delta)


def _read_followup_context(parsed: Any, context_reader: ContextReader, last_absorbed_message_id: str) -> list[dict[str, Any]]:
    try:
        return context_reader(parsed.chat_id, page_size=80, stop_at_message_id=last_absorbed_message_id)
    except TypeError:
        return context_reader(parsed.chat_id, page_size=80)


def _compose_group_followup_input(text: str, group_context: list[dict[str, Any]]) -> str:
    lines = [
        "当前群聊补充指令：",
        text.strip(),
        "",
        "距离上一次群聊吸收边界之后的新群聊消息：",
    ]
    for message in group_context:
        sender = message.get("sender_id") or message.get("sender", {}).get("id") or message.get("sender") or "unknown"
        message_id = message.get("message_id") or message.get("id") or "unknown"
        sent_at = str(message.get("sent_at") or message.get("create_time") or "")
        content = str(message.get("content") or message.get("text") or "").strip()
        prefix = f"- [{message_id}] {sender}"
        if sent_at:
            prefix += f" {sent_at}"
        lines.append(f"{prefix}: {content}")
    lines.extend(["", "仅把上面这些群聊增量视为新的群聊上下文。"])
    return "\n".join(lines).strip()


def _advance_absorbed_message_boundary(
    tasks_root: Path,
    session_key: str,
    binding: dict[str, Any],
    parsed: Any,
) -> None:
    if parsed.chat_type not in {"group", "channel"}:
        return
    task_id = binding.get("active_task_id")
    chat_id = binding.get("chat_id")
    sender_id = binding.get("sender_id")
    channel_type = binding.get("channel_type")
    if not task_id or not chat_id or not sender_id or not channel_type:
        return
    bind_active_task(
        tasks_root / "task-bindings.json",
        session_key=session_key,
        task_id=str(task_id),
        chat_id=str(chat_id),
        channel_type=str(channel_type),
        sender_id=str(sender_id),
        codex_thread_id=binding.get("codex_thread_id"),
        active_turn_id=binding.get("active_turn_id"),
        last_absorbed_message_id=parsed.message_id,
    )


def _append_to_active_turn_if_available(
    tasks_root: Path,
    session_key: str,
    parsed: Any,
    context_reader: ContextReader | None = None,
) -> dict[str, Any] | None:
    binding = get_task_binding(tasks_root / "task-bindings.json", session_key)
    if not binding:
        return None
    task_id = binding.get("active_task_id")
    codex_thread_id = binding.get("codex_thread_id")
    active_turn_id = binding.get("active_turn_id")
    if not task_id or not codex_thread_id or not active_turn_id:
        return None
    payload = {
        "text": parsed.text,
        "message_id": parsed.message_id,
        "session_key": session_key,
        "chat_id": parsed.chat_id,
        "sender_id": parsed.sender_open_id,
        "codex_thread_id": codex_thread_id,
        "active_turn_id": active_turn_id,
    }
    _attach_group_delta_payload(
        payload,
        tasks_root=tasks_root,
        session_key=session_key,
        binding=binding,
        parsed=parsed,
        context_reader=context_reader,
    )
    command = append_control_command(
        tasks_root / str(task_id),
        "append_instruction",
        payload,
        operator="feishu",
    )
    _advance_absorbed_message_boundary(tasks_root, session_key, binding, parsed)
    return {"task_id": str(task_id), "control": command}


def _append_to_waiting_task_if_available(
    tasks_root: Path,
    session_key: str,
    parsed: Any,
    context_reader: ContextReader | None = None,
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
    payload = {
        "text": parsed.text,
        "message_id": parsed.message_id,
        "session_key": session_key,
        "chat_id": parsed.chat_id,
        "sender_id": parsed.sender_open_id,
    }
    _attach_group_delta_payload(
        payload,
        tasks_root=tasks_root,
        session_key=session_key,
        binding=binding,
        parsed=parsed,
        context_reader=context_reader,
    )
    command = append_control_command(
        task_dir,
        "append_instruction",
        payload,
        operator="feishu",
    )
    _advance_absorbed_message_boundary(tasks_root, session_key, binding, parsed)
    return {"task_id": str(task_id), "control": command}


def _task_id(message_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "_.-" else "-" for char in message_id)
    return f"im-{safe}"


def _conversation_context(parsed: Any, context_reader: ContextReader, new_command: Any | None = None) -> list[dict[str, Any]]:
    if parsed.chat_type not in {"group", "channel"}:
        return []
    page_size = 80 if new_command is not None else 20
    messages = _read_context(parsed, context_reader, page_size=page_size, new_command=new_command)
    if new_command is not None:
        return collect_new_session_context(
            messages,
            trigger_message_id=parsed.message_id,
            command=new_command,
            max_messages=80,
        )
    return [message for message in messages if message.get("message_id") != parsed.message_id]


def _read_context(parsed: Any, context_reader: ContextReader, page_size: int, new_command: Any | None) -> list[dict[str, Any]]:
    cutoff_after = None
    if new_command is not None and new_command.lookback is not None:
        event_time = _event_time(parsed.raw)
        if event_time is not None:
            cutoff_after = event_time - new_command.lookback
    if cutoff_after is not None:
        try:
            return context_reader(parsed.chat_id, page_size=page_size, cutoff_after=cutoff_after)
        except TypeError:
            return context_reader(parsed.chat_id, page_size=page_size)
    return context_reader(parsed.chat_id, page_size=page_size)


def _event_time(payload: dict[str, Any]) -> datetime | None:
    event = payload.get("event", payload)
    message = event.get("message", {}) if isinstance(event, dict) else {}
    raw = str(
        payload.get("timestamp")
        or payload.get("create_time")
        or message.get("create_time")
        or message.get("update_time")
        or ""
    ).strip()
    if not raw:
        return None
    if raw.isdigit():
        timestamp = int(raw)
        if timestamp > 10_000_000_000:
            timestamp = timestamp // 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
