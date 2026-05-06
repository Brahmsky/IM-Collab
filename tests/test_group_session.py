from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bridge.group_session import collect_new_session_context, parse_new_session_command


def test_parse_new_session_command_accepts_instruction_only() -> None:
    command = parse_new_session_command("/new 生成项目复盘")

    assert command is not None
    assert command.instruction == "生成项目复盘"
    assert command.lookback is None


def test_parse_new_session_command_accepts_compound_time() -> None:
    command = parse_new_session_command("/new 2d6h 整理最近新增需求")

    assert command is not None
    assert command.instruction == "整理最近新增需求"
    assert command.lookback == timedelta(days=2, hours=6)


def test_parse_new_session_command_can_ignore_bot_mention_prefix() -> None:
    command = parse_new_session_command("@飞书 CLI /new 5h 帮忙生成这个ppt，然后返回到这里")

    assert command is not None
    assert command.instruction == "帮忙生成这个ppt，然后返回到这里"
    assert command.lookback == timedelta(hours=5)


def test_collect_new_session_context_without_time_stops_at_previous_new_boundary() -> None:
    messages = [
        {"message_id": "om_old", "content": "去年旧需求", "sent_at": "2025-01-01T10:00:00+08:00"},
        {"message_id": "om_prev_new", "content": "/new 三天前的新任务", "sent_at": "2026-05-03T10:00:00+08:00"},
        {"message_id": "om_after_1", "content": "昨天新增要求", "sent_at": "2026-05-05T10:00:00+08:00"},
        {"message_id": "om_after_2", "content": "今天新增要求", "sent_at": "2026-05-06T10:00:00+08:00"},
        {"message_id": "om_trigger", "content": "/new 生成方案", "sent_at": "2026-05-06T11:00:00+08:00"},
    ]

    selected = collect_new_session_context(
        messages,
        trigger_message_id="om_trigger",
        command=parse_new_session_command("/new 生成方案"),
        now=datetime(2026, 5, 6, 11, 0, tzinfo=UTC),
        max_messages=80,
    )

    assert [message["message_id"] for message in selected] == ["om_after_1", "om_after_2"]


def test_collect_new_session_context_with_time_uses_time_cutoff_not_previous_new() -> None:
    messages = [
        {"message_id": "om_prev_new", "content": "/new 之前的新任务", "sent_at": "2026-05-03T10:00:00+08:00"},
        {"message_id": "om_yesterday", "content": "昨天要求", "sent_at": "2026-05-05T10:00:00+08:00"},
        {"message_id": "om_today", "content": "今天要求", "sent_at": "2026-05-06T10:00:00+08:00"},
        {"message_id": "om_trigger", "content": "/new 6h 只整理今天", "sent_at": "2026-05-06T11:00:00+08:00"},
    ]

    selected = collect_new_session_context(
        messages,
        trigger_message_id="om_trigger",
        command=parse_new_session_command("/new 6h 只整理今天"),
        max_messages=80,
    )

    assert [message["message_id"] for message in selected] == ["om_today"]
