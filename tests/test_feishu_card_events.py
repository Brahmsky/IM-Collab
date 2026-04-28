from __future__ import annotations

from bridge.feishu_events import parse_card_action_event


def test_parse_compact_card_action_event() -> None:
    payload = {
        "type": "card.action.trigger",
        "message_id": "om_card",
        "open_id": "ou_user",
        "chat_id": "oc_group",
        "action": {"value": {"action": "start_task", "task_id": "im-om_waiting"}},
    }

    parsed = parse_card_action_event(payload)

    assert parsed.message_id == "om_card"
    assert parsed.chat_id == "oc_group"
    assert parsed.sender_open_id == "ou_user"
    assert parsed.action == "start_task"
    assert parsed.task_id == "im-om_waiting"
    assert parsed.value == {"action": "start_task", "task_id": "im-om_waiting"}


def test_parse_lark_callback_card_action_event() -> None:
    payload = {
        "schema": "2.0",
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "operator": {"open_id": "ou_user"},
            "context": {"open_message_id": "om_card", "open_chat_id": "oc_group"},
            "action": {"value": {"action": "append_requirement", "task_id": "im-om_waiting"}},
        },
    }

    parsed = parse_card_action_event(payload)

    assert parsed.message_id == "om_card"
    assert parsed.chat_id == "oc_group"
    assert parsed.sender_open_id == "ou_user"
    assert parsed.action == "append_requirement"
    assert parsed.task_id == "im-om_waiting"
