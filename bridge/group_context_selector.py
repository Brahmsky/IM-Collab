from __future__ import annotations

from typing import Any

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
        if _has_real_runtime_signal(message):
            selected[_message_key(message)] = message

    for message in messages[-max(recent_tail, 0) :]:
        selected[_message_key(message)] = message
        protected_keys.add(_message_key(message))

    if len(selected) > max_messages:
        selected = _trim_selected(selected, max_messages, protected_keys)
    return sorted(selected.values(), key=lambda message: _message_index(messages, message))


def _has_real_runtime_signal(message: dict[str, Any]) -> bool:
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
    ranked = sorted(candidates.items(), key=lambda item: str(item[1].get("sent_at") or ""), reverse=True)
    return {**dict(ranked[:remaining_budget]), **protected}


def _message_key(message: dict[str, Any]) -> str:
    return str(message.get("message_id") or message.get("id") or id(message))


def _message_index(messages: list[dict[str, Any]], target: dict[str, Any]) -> int:
    target_key = _message_key(target)
    for index, message in enumerate(messages):
        if _message_key(message) == target_key:
            return index
    return len(messages)
