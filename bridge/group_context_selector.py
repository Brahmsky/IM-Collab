from __future__ import annotations

from typing import Any

PRIORITY_TAGS = {
    "formal_notice",
    "deadline",
    "budget_rule",
    "requirement",
    "decision",
    "correction",
    "conflict",
    "open_question",
    "latest",
    "final",
    "attachment",
    "template",
    "deliverable",
    "bot_request",
}

def select_briefing_context(
    messages: list[dict[str, Any]],
    max_messages: int = 45,
    recent_tail: int = 12,
) -> list[dict[str, Any]]:
    if max_messages <= 0:
        return []
    if len(messages) <= max_messages:
        return messages
    selected: dict[str, dict[str, Any]] = {}
    protected_keys: set[str] = set()

    for message in messages:
        if _is_priority_message(message):
            selected[_message_key(message)] = message

    for message in messages[-max(recent_tail, 0) :]:
        selected[_message_key(message)] = message
        protected_keys.add(_message_key(message))

    if len(selected) > max_messages:
        selected = _trim_selected(selected, max_messages, protected_keys)
    return sorted(selected.values(), key=lambda message: _message_index(messages, message))


def _is_priority_message(message: dict[str, Any]) -> bool:
    tags = {str(tag) for tag in message.get("tags", []) if isinstance(tag, str)}
    if tags & PRIORITY_TAGS:
        return True
    if message.get("attachments"):
        return True
    return False


def _trim_selected(
    selected: dict[str, dict[str, Any]],
    max_messages: int,
    protected_keys: set[str],
) -> dict[str, dict[str, Any]]:
    protected = {key: message for key, message in selected.items() if key in protected_keys}
    remaining_budget = max(max_messages - len(protected), 0)
    candidates = {key: message for key, message in selected.items() if key not in protected_keys}
    ranked = sorted(candidates.items(), key=lambda item: (_priority_score(item[1]), str(item[1].get("sent_at") or "")), reverse=True)
    return {**dict(ranked[:remaining_budget]), **protected}


def _priority_score(message: dict[str, Any]) -> int:
    tags = {str(tag) for tag in message.get("tags", []) if isinstance(tag, str)}
    score = 0
    score += 5 * len(tags & {"formal_notice", "deadline", "correction", "conflict", "final", "latest"})
    score += 4 * len(tags & {"budget_rule", "requirement", "decision", "open_question", "bot_request"})
    score += 3 if message.get("attachments") else 0
    return score


def _message_key(message: dict[str, Any]) -> str:
    return str(message.get("message_id") or message.get("id") or id(message))


def _message_index(messages: list[dict[str, Any]], target: dict[str, Any]) -> int:
    target_key = _message_key(target)
    for index, message in enumerate(messages):
        if _message_key(message) == target_key:
            return index
    return len(messages)
