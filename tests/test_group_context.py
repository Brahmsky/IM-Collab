from __future__ import annotations

import json
from pathlib import Path

from bridge.group_context import (
    build_context_reader,
    build_standard_group_context,
    normalize_feishu_message,
    read_fixture_context,
    select_latest_context,
)


def test_normalize_feishu_message_from_lark_event() -> None:
    payload = {
        "schema": "2.0",
        "event": {
            "sender": {"sender_id": {"open_id": "ou_lead"}},
            "message": {
                "message_id": "om_notice",
                "chat_id": "oc_course",
                "chat_type": "group",
                "message_type": "text",
                "create_time": "1777395600000",
                "content": "{\"text\":\"本周五 18:00 前提交文档和 PPT\"}",
            },
        },
    }

    message = normalize_feishu_message(payload)

    assert message == {
        "message_id": "om_notice",
        "chat_id": "oc_course",
        "chat_type": "group",
        "sender_id": "ou_lead",
        "sender": "ou_lead",
        "sent_at": "1777395600000",
        "message_type": "text",
        "content": "本周五 18:00 前提交文档和 PPT",
        "attachments": [],
        "raw": payload,
    }


def test_read_fixture_context_accepts_raw_event_directory(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "raw_feishu_events"
    fixture_dir.mkdir()
    (fixture_dir / "001.json").write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_1",
                "chat_id": "oc_course",
                "chat_type": "group",
                "message_type": "text",
                "sender_id": "ou_a",
                "timestamp": "1777395600000",
                "content": "正式通知：周五 18:00 前提交。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    messages = read_fixture_context(fixture_dir, chat_id="oc_course", page_size=20)

    assert len(messages) == 1
    assert messages[0]["message_id"] == "om_1"
    assert messages[0]["content"] == "正式通知：周五 18:00 前提交。"


def test_build_standard_group_context_filters_chat_and_keeps_attachments(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "raw_feishu_events"
    fixture_dir.mkdir()
    (fixture_dir / "001.json").write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_notice",
                "chat_id": "oc_target",
                "chat_type": "group",
                "message_type": "file",
                "sender_id": "ou_teacher",
                "timestamp": "1777395600000",
                "content": "正式通知见附件。",
                "attachments": [{"type": "file", "name": "课程要求.docx", "file_key": "file_1"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (fixture_dir / "002.json").write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_other",
                "chat_id": "oc_other",
                "chat_type": "group",
                "message_type": "text",
                "sender_id": "ou_other",
                "timestamp": "1777395700000",
                "content": "另一个群的消息。",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    messages = build_standard_group_context(fixture_dir, chat_id="oc_target")

    assert [message["message_id"] for message in messages] == ["om_notice"]
    assert messages[0]["attachments"] == [{"type": "file", "name": "课程要求.docx", "file_key": "file_1"}]


def test_build_context_reader_defaults_to_real_reader_when_no_fixture() -> None:
    seen: dict[str, object] = {}

    def real_reader(chat_id: str, page_size: int = 20):
        seen["chat_id"] = chat_id
        seen["page_size"] = page_size
        return [{"message_id": "om_real"}]

    reader = build_context_reader(None, real_reader=real_reader)

    assert reader("oc_real", page_size=7) == [{"message_id": "om_real"}]
    assert seen == {"chat_id": "oc_real", "page_size": 7}


def test_build_context_reader_accepts_selector_hook_for_long_context(tmp_path: Path) -> None:
    fixture_path = tmp_path / "messages.json"
    fixture_path.write_text(
        json.dumps(
            [
                {"message_id": "om_old_decision", "chat_id": "oc_long", "content": "旧决策：保留"},
                {"message_id": "om_noise", "chat_id": "oc_long", "content": "闲聊"},
                {"message_id": "om_recent_change", "chat_id": "oc_long", "content": "新更正：周五交"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def select_decisions(messages, page_size):
        return [message for message in messages if "决策" in message["content"] or "更正" in message["content"]][:page_size]

    reader = build_context_reader(fixture_path, real_reader=lambda *_args, **_kwargs: [], selector=select_decisions)

    assert [message["message_id"] for message in reader("oc_long", page_size=20)] == [
        "om_old_decision",
        "om_recent_change",
    ]


def test_select_latest_context_keeps_latest_messages() -> None:
    messages = [{"message_id": f"om_{index}", "content": str(index)} for index in range(5)]

    assert [message["message_id"] for message in select_latest_context(messages, page_size=2)] == ["om_3", "om_4"]
