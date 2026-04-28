from __future__ import annotations

import re
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
}


def build_group_brief(chat_id: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    source_messages = [_normalize_message(index, message) for index, message in enumerate(messages, start=1)]
    annotations: list[dict[str, Any]] = []
    for message in source_messages:
        annotations.extend(_annotations_for_message(len(annotations), message))
    annotations.extend(_conflict_annotations(len(annotations), source_messages))
    brief = {
        "chat_id": chat_id,
        "source_messages": source_messages,
        "annotations": annotations,
        "summary": _summary_from_annotations(annotations),
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


def build_confirmation_card(brief: dict[str, Any], task_id: str) -> dict[str, Any]:
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
    elements.extend(
        [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "开始执行"},
                "type": "primary",
                "value": {"action": "start_task", "task_id": task_id},
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "补充要求"},
                "type": "default",
                "value": {"action": "append_requirement", "task_id": task_id},
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


def _annotations_for_message(offset: int, message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message["content"]
    annotations: list[dict[str, Any]] = []
    if _mentions_deadline(content):
        annotations.append(_annotation(offset + len(annotations) + 1, "deadline", _sentence(content), message))
    if any(term in content for term in ("提交", "上传", "交到", "发到", "提交方式")):
        annotations.append(_annotation(offset + len(annotations) + 1, "submission_method", _sentence(content), message))
    if any(term in content for term in ("文档", "Markdown", "word", "Word", "docx", "方案")):
        annotations.append(_annotation(offset + len(annotations) + 1, "document_requirement", _sentence(content), message))
    if any(term in content for term in ("PPT", "ppt", "演示稿", "幻灯片", "页")):
        annotations.append(_annotation(offset + len(annotations) + 1, "slides_requirement", _sentence(content), message))
    if any(term in content for term in ("白板", "流程图", "流程", "Mermaid")):
        annotations.append(_annotation(offset + len(annotations) + 1, "whiteboard_requirement", _sentence(content), message))
    if any(term in content for term in ("负责", "分工", "你来", "我来")):
        annotations.append(_annotation(offset + len(annotations) + 1, "assignment", _sentence(content), message))
    if message.get("attachments"):
        annotations.append(_annotation(offset + len(annotations) + 1, "attachment_reference", "该消息包含附件引用。", message))
    if any(term in content for term in ("？", "?", "确认", "不确定", "是不是")):
        annotations.append(
            _annotation(offset + len(annotations) + 1, "open_question", _sentence(content), message, confidence="medium", needs_confirmation=True)
        )
    return annotations


def _conflict_annotations(offset: int, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slide_page_mentions: list[tuple[str, str]] = []
    for message in messages:
        content = message["content"]
        if not any(term in content for term in ("PPT", "ppt", "演示稿", "幻灯片")):
            continue
        pages = re.findall(r"(\d+)\s*页", content)
        for page in pages:
            slide_page_mentions.append((message["message_id"], page))
    page_values = {page for _, page in slide_page_mentions}
    if len(page_values) <= 1:
        return []
    evidence = [message_id for message_id, _ in slide_page_mentions]
    return [
        {
            "annotation_id": f"ann_{offset + 1:03d}",
            "type": "conflict",
            "claim": f"PPT 页数出现多个版本：{', '.join(sorted(page_values))} 页，需要人工确认。",
            "evidence_message_ids": evidence,
            "confidence": "medium",
            "needs_confirmation": True,
        }
    ]


def _summary_from_annotations(annotations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    summary = {
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


def _mentions_deadline(content: str) -> bool:
    return any(term in content for term in ("截止", "前", "周一", "周二", "周三", "周四", "周五", "周六", "周日")) and any(
        term in content for term in ("提交", "交", "完成", "截止", "前")
    )


def _sentence(content: str) -> str:
    compact = " ".join(content.split())
    return compact if len(compact) <= 120 else compact[:117] + "..."
