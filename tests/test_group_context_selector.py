from __future__ import annotations

from pathlib import Path

from bridge.group_context import build_standard_group_context
from bridge.group_context_selector import select_briefing_context


def test_select_briefing_context_uses_backend_tags_attachments_and_recent_tail() -> None:
    messages = [
        {"message_id": "om_1", "content": "闲聊", "tags": ["noise"]},
        {"message_id": "om_2", "content": "正式通知：4 月 28 日截止", "tags": ["formal_notice", "deadline"]},
        {"message_id": "om_3", "content": "旧预算 29000", "tags": ["budget"]},
        {"message_id": "om_4", "content": "更正：预算 28000", "tags": ["correction"]},
        {"message_id": "om_5", "content": "最终版申请书", "tags": ["final"], "attachments": [{"name": "final.docx"}]},
        {"message_id": "om_6", "content": "这个合同要不要？", "tags": ["open_question"]},
        {"message_id": "om_7", "content": "@飞书 CLI 整理", "tags": ["bot_request"]},
    ]

    selected = select_briefing_context(messages, max_messages=5, recent_tail=1)

    assert [message["message_id"] for message in selected] == ["om_2", "om_4", "om_5", "om_6", "om_7"]


def test_select_briefing_context_does_not_keyword_scan_untagged_messages() -> None:
    messages = [
        {"message_id": "om_1", "content": "正式通知：这句话包含很多看似重要的词，但是没有后端 tag。"},
        {"message_id": "om_2", "content": "普通消息"},
        {"message_id": "om_3", "content": "最近消息"},
    ]

    selected = select_briefing_context(messages, max_messages=1, recent_tail=1)

    assert [message["message_id"] for message in selected] == ["om_3"]


def test_select_briefing_context_keeps_recent_tail_when_priority_messages_fill_budget() -> None:
    messages = [
        {"message_id": f"om_{index}", "content": f"消息 {index}", "tags": ["formal_notice"] if index == 1 else []}
        for index in range(1, 12)
    ]

    selected = select_briefing_context(messages, max_messages=4, recent_tail=3)

    assert [message["message_id"] for message in selected] == ["om_1", "om_9", "om_10", "om_11"]


def test_grant_selector_reduces_context_but_keeps_oracle_evidence_surface() -> None:
    messages = build_standard_group_context(
        Path("examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json")
    )

    selected = select_briefing_context(messages, max_messages=45, recent_tail=12)
    selected_ids = {message["message_id"] for message in selected}

    assert len(selected) <= 45
    assert len(selected) < len(messages)
    assert {
        "om_grant_030",
        "om_grant_031",
        "om_grant_049",
        "om_grant_055",
        "om_grant_056",
        "om_grant_062",
        "om_grant_064",
        "om_grant_066",
    } <= selected_ids
