from __future__ import annotations

from typing import Any


ANNOTATION_TYPES = {
    "task_goal",
    "deadline",
    "submission_method",
    "document_requirement",
    "slides_requirement",
    "whiteboard_requirement",
    "assignment",
    "authority_note",
    "attachment_reference",
    "conflict",
    "open_question",
    "source_note",
}


def build_group_brief(chat_id: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    source_messages = [_normalize_message(index, message) for index, message in enumerate(messages, start=1)]
    annotations: list[dict[str, Any]] = []
    for message in source_messages:
        annotations.append(_annotation(len(annotations) + 1, "source_note", _sentence(message["content"]), message, confidence="source"))
        if message.get("attachments"):
            annotations.append(_annotation(len(annotations) + 1, "attachment_reference", "该消息包含附件引用。", message))
    brief = {
        "chat_id": chat_id,
        "source_messages": source_messages,
        "annotations": annotations,
        "summary": _summary_from_annotations(annotations, source_message_count=len(source_messages)),
    }
    validate_group_brief(brief)
    return brief


def build_group_brief_from_evidence(
    chat_id: str,
    messages: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    source_messages = [_normalize_message(index, message) for index, message in enumerate(messages, start=1)]
    annotations = [_annotation_from_evidence(index, item) for index, item in enumerate(evidence_items, start=1)]
    brief = {
        "chat_id": chat_id,
        "source_messages": source_messages,
        "annotations": annotations,
        "summary": _summary_from_annotations(annotations, source_message_count=len(source_messages)),
    }
    validate_group_brief(brief)
    return brief


def validate_group_brief(brief: dict[str, Any]) -> None:
    message_ids = {message.get("message_id") for message in brief.get("source_messages", [])}
    for annotation in brief.get("annotations", []):
        annotation_type = annotation.get("type")
        if annotation_type not in ANNOTATION_TYPES:
            raise ValueError(f"unsupported annotation type: {annotation_type}")
        evidence = annotation.get("evidence_message_ids")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"annotation missing evidence: {annotation.get('annotation_id')}")
        missing = [message_id for message_id in evidence if message_id not in message_ids]
        if missing:
            raise ValueError(f"annotation references unknown messages: {missing}")


def render_group_brief_markdown(brief: dict[str, Any]) -> str:
    lines = ["# 群聊旁批汇总", "", f"chat_id: {brief['chat_id']}", "", "## 原始群聊记录", ""]
    for message in brief["source_messages"]:
        sender = message.get("sender") or "unknown"
        sent_at = message.get("sent_at") or ""
        prefix = f"- [{message['message_id']}] {sender}"
        if sent_at:
            prefix += f" {sent_at}"
        lines.append(f"{prefix}: {message.get('content', '')}")
        for attachment in message.get("attachments", []):
            name = attachment.get("name") or attachment.get("url") or attachment.get("type") or "attachment"
            lines.append(f"  - 附件: {name}")
    lines.extend(["", "## 旁批标注", ""])
    for annotation in brief["annotations"]:
        lines.append(
            f"- {annotation['annotation_id']} `{annotation['type']}`: {annotation['claim']} "
            f"(引用: {', '.join(annotation['evidence_message_ids'])})"
        )
    lines.extend(["", "## 总汇总区", ""])
    summary = brief["summary"]
    for title, key in [
        ("任务目标", "task_goal"),
        ("截止时间", "deadlines"),
        ("交付物/格式要求", "format_requirements"),
        ("分工", "assignments"),
        ("风险/冲突", "risks"),
        ("待确认项", "open_questions"),
    ]:
        lines.append(f"### {title}")
        items = summary.get(key, [])
        if not items:
            lines.append("- 未在群聊中找到可引用信息。")
        for item in items:
            lines.append(f"- {item['claim']} (引用: {', '.join(item['evidence_message_ids'])})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def brief_needs_confirmation(brief: dict[str, Any]) -> bool:
    return any(
        annotation.get("type") in {"conflict", "open_question"} or annotation.get("needs_confirmation") is True
        for annotation in brief.get("annotations", [])
    )


def render_confirmation_markdown(brief: dict[str, Any]) -> str:
    uncertain = [
        annotation
        for annotation in brief.get("annotations", [])
        if annotation.get("type") in {"conflict", "open_question"} or annotation.get("needs_confirmation") is True
    ]
    lines = [
        "你好，我是你的办公协作助手。",
        "",
        "我已先完成群聊旁批汇总，但发现以下信息需要确认，暂不开始生成文档/PPT/白板：",
        "",
    ]
    for annotation in uncertain:
        lines.append(f"- {annotation['claim']}（引用: {', '.join(annotation['evidence_message_ids'])}）")
    lines.extend(
        [
            "",
            "请在群里补充或确认这些问题；确认后我会继续执行生成。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_confirmation_card(brief: dict[str, Any], task_id: str, session_key: str | None = None) -> dict[str, Any]:
    uncertain = [
        annotation
        for annotation in brief.get("annotations", [])
        if annotation.get("type") in {"conflict", "open_question"} or annotation.get("needs_confirmation") is True
    ]
    elements: list[dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": "我已完成群聊旁批汇总，但发现以下信息需要确认，暂不开始生成文档/PPT/白板。",
        }
    ]
    for annotation in uncertain:
        refs = ", ".join(annotation["evidence_message_ids"])
        elements.append({"tag": "markdown", "content": f"- {annotation['claim']}\\n  引用: {refs}"})
    start_value = {"action": "start_task", "task_id": task_id}
    append_value = {"action": "append_requirement", "task_id": task_id}
    if session_key:
        start_value["session_key"] = session_key
        append_value["session_key"] = session_key
    elements.extend(
        [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "开始执行"},
                "type": "primary",
                "value": start_value,
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "补充要求"},
                "type": "default",
                "value": append_value,
            },
        ]
    )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "请确认群聊需求"},
        },
        "elements": elements,
    }


def _normalize_message(index: int, message: dict[str, Any]) -> dict[str, Any]:
    message_id = str(message.get("message_id") or message.get("id") or f"msg_{index:03d}")
    sender = str(message.get("sender") or message.get("sender_id") or message.get("sender_name") or "unknown")
    attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
    return {
        "message_id": message_id,
        "sender": sender,
        "sent_at": str(message.get("sent_at") or message.get("time") or ""),
        "content": str(message.get("content") or message.get("text") or ""),
        "attachments": [attachment for attachment in attachments if isinstance(attachment, dict)],
    }


def _summary_from_annotations(annotations: list[dict[str, Any]], source_message_count: int) -> dict[str, Any]:
    summary = {
        "source_message_count": source_message_count,
        "annotation_count": len(annotations),
        "task_goal": [],
        "deadlines": [],
        "deliverables": [],
        "format_requirements": [],
        "assignments": [],
        "risks": [],
        "open_questions": [],
    }
    for annotation in annotations:
        item = {"claim": annotation["claim"], "evidence_message_ids": annotation["evidence_message_ids"]}
        annotation_type = annotation["type"]
        if annotation_type == "task_goal":
            summary["task_goal"].append(item)
        elif annotation_type == "deadline":
            summary["deadlines"].append(item)
        elif annotation_type in {"document_requirement", "slides_requirement", "whiteboard_requirement", "submission_method"}:
            summary["format_requirements"].append(item)
        elif annotation_type == "assignment":
            summary["assignments"].append(item)
        elif annotation_type == "conflict":
            summary["risks"].append(item)
        elif annotation_type == "open_question":
            summary["open_questions"].append(item)
    return summary


def _annotation(
    number: int,
    annotation_type: str,
    claim: str,
    message: dict[str, Any],
    confidence: str = "high",
    needs_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "annotation_id": f"ann_{number:03d}",
        "type": annotation_type,
        "claim": claim,
        "evidence_message_ids": [message["message_id"]],
        "confidence": confidence,
        "needs_confirmation": needs_confirmation,
    }


def _annotation_from_evidence(number: int, evidence: dict[str, Any]) -> dict[str, Any]:
    annotation_type = str(evidence.get("kind") or "")
    needs_confirmation = annotation_type in {"conflict", "open_question"} or evidence.get("needs_confirmation") is True
    return {
        "annotation_id": f"lx_{number:03d}",
        "type": annotation_type,
        "claim": str(evidence.get("claim") or evidence.get("source_text") or ""),
        "evidence_message_ids": [str(message_id) for message_id in evidence.get("source_message_ids", [])],
        "confidence": str(evidence.get("confidence") or "medium"),
        "needs_confirmation": needs_confirmation,
        "extractor": str(evidence.get("extractor") or "external"),
    }


def _sentence(content: str) -> str:
    compact = " ".join(content.split())
    return compact if len(compact) <= 120 else compact[:117] + "..."
