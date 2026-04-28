from __future__ import annotations

from pathlib import Path

from bridge.feishu_events import create_task_from_event, parse_im_event
from bridge.task_protocol import read_status


def test_parse_im_event_extracts_text_message() -> None:
    event = {
        "schema": "2.0",
        "event": {
            "message": {
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "group",
                "message_type": "text",
                "content": "{\"text\":\"@Agent 生成项目方案\"}",
            },
            "sender": {"sender_id": {"open_id": "ou_789"}},
        },
    }

    parsed = parse_im_event(event)

    assert parsed.message_id == "om_123"
    assert parsed.chat_id == "oc_456"
    assert parsed.sender_open_id == "ou_789"
    assert parsed.text == "@Agent 生成项目方案"
    assert parsed.task_id == "im-om_123"


def test_parse_compact_event_from_lark_cli_subscribe() -> None:
    event = {
        "type": "im.message.receive_v1",
        "id": "om_123",
        "message_id": "om_123",
        "chat_id": "oc_456",
        "chat_type": "p2p",
        "message_type": "text",
        "content": "Hello from compact event",
        "sender_id": "ou_789",
        "timestamp": "1773491924409",
    }

    parsed = parse_im_event(event)

    assert parsed.message_id == "om_123"
    assert parsed.text == "Hello from compact event"
    assert parsed.sender_open_id == "ou_789"


def test_create_task_from_event_writes_request_markdown(tmp_path: Path) -> None:
    event = {
        "event": {
            "message": {
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "group",
                "message_type": "text",
                "content": "{\"text\":\"生成项目方案\"}",
            },
            "sender": {"sender_id": {"open_id": "ou_789"}},
        }
    }

    task_dir = create_task_from_event(event, tmp_path)

    assert task_dir == tmp_path / "im-om_123"
    assert read_status(task_dir)["state"] == "queued"
    request = (task_dir / "request.md").read_text(encoding="utf-8")
    assert "message_id: om_123" in request
    assert "chat_id: oc_456" in request
    assert "生成项目方案" in request
    assert "Codex + superpowers" in request
