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
from bridge.task_binding import get_task_binding
from bridge.task_binding import build_golembot_session_key

Forwarder = Callable[..., dict[str, Any]]
Replier = Callable[[str, str, str, bool], dict[str, Any]]
Publisher = Callable[[Path], dict[str, Any]]
OfficeRunner = Callable[..., dict[str, Any]]
ContextReader = Callable[..., list[dict[str, Any]]]


def dispatch_event_via_golembot(
    event_path: Path,
    gateway_url: str,
    token: str,
    publish: bool = False,
    generator: str = "codex",
    execute_reply: bool = False,
    tasks_root: Path = Path("tasks"),
    forwarder: Forwarder = forward_event_to_golembot,
    office_runner: OfficeRunner = run_golembot_office_task,
    publisher: Publisher = publish_task_artifacts_to_feishu,
    replier: Replier = reply_to_message,
    context_reader: ContextReader = list_chat_messages,
) -> dict[str, Any]:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    parsed = parse_im_event(payload)
    session_key = build_golembot_session_key("feishu", parsed.chat_id, parsed.sender_open_id, parsed.chat_type)

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
        publish_result = publisher(Path(str(task_result["task_dir"])))
        reply_markdown = build_delivery_markdown(publish_result["artifacts"])
        reply = replier(
            parsed.message_id,
            reply_markdown,
            f"{parsed.message_id}-golembot-forwarded",
            not execute_reply,
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
    reply = replier(
        parsed.message_id,
        reply_markdown,
        f"{parsed.message_id}-golembot-forwarded",
        not execute_reply,
    )
    return {**forwarded, "publish": publish_result, "reply_markdown": reply_markdown, "reply": reply}


def _publish_bound_task(tasks_root: Path, session_key: str, publisher: Publisher) -> dict[str, Any]:
    binding = get_task_binding(tasks_root / "task-bindings.json", session_key)
    task_id = binding.get("active_task_id") if binding else None
    if not task_id:
        raise RuntimeError(f"no active task binding for session {session_key}")
    return publisher(tasks_root / str(task_id))


def _is_office_deliverable(text: str) -> bool:
    action_terms = ("生成", "整理", "创建", "输出", "做", "写")
    artifact_terms = ("文档", "方案", "演示稿", "PPT", "幻灯片", "白板", "流程", "纪要", "报告")
    if any(term in text for term in action_terms) and any(term in text for term in artifact_terms):
        return True
    return "IM-Collab" in text and "6" in text


def _task_id(message_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "_.-" else "-" for char in message_id)
    return f"im-{safe}"


def _conversation_context(parsed: Any, context_reader: ContextReader) -> list[dict[str, Any]]:
    if parsed.chat_type not in {"group", "channel"}:
        return []
    messages = context_reader(parsed.chat_id, page_size=20)
    return [message for message in messages if message.get("message_id") != parsed.message_id]
