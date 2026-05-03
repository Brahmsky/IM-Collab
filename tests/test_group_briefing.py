from __future__ import annotations

from bridge.group_briefing import (
    build_confirmation_card,
    build_group_brief,
    build_group_brief_from_evidence,
    render_group_brief_markdown,
    validate_group_brief,
)


def test_build_group_brief_creates_source_grounded_source_notes_without_semantic_rules() -> None:
    brief = build_group_brief(
        chat_id="oc_group",
        messages=[
            {
                "message_id": "om_1",
                "sender_id": "teacher",
                "sent_at": "2026-04-28T10:00:00+08:00",
                "content": "周五 18:00 前提交项目方案和 PPT。",
            },
            {
                "message_id": "om_2",
                "sender_id": "ou_a",
                "sent_at": "2026-04-28T10:03:00+08:00",
                "content": "PPT 控制在 8 页，文档用 Markdown。",
            },
            {
                "message_id": "om_3",
                "sender_id": "ou_b",
                "sent_at": "2026-04-28T10:05:00+08:00",
                "content": "我负责白板流程，阿明负责演示稿。",
            },
        ],
    )

    validate_group_brief(brief)
    annotations = brief["annotations"]
    assert [item["type"] for item in annotations] == ["source_note", "source_note", "source_note"]
    assert all(item["evidence_message_ids"] for item in annotations)
    assert brief["source_messages"][0]["content"] == "周五 18:00 前提交项目方案和 PPT。"
    assert brief["summary"]["deadlines"] == []
    assert brief["summary"]["format_requirements"] == []


def test_build_group_brief_does_not_infer_conflicts_with_regex_or_keywords() -> None:
    brief = build_group_brief(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender": "老师", "content": "PPT 不超过 8 页。"},
            {"message_id": "om_2", "sender": "同学", "content": "我记得 PPT 可以 10 页。"},
        ],
    )

    assert [item["type"] for item in brief["annotations"]] == ["source_note", "source_note"]
    assert brief["summary"]["risks"] == []


def test_group_brief_records_confidence_and_source_counts() -> None:
    brief = build_group_brief(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender_id": "teacher", "content": "周五 18:00 前提交方案。"},
            {"message_id": "om_2", "sender_id": "student", "content": "PPT 做 8 页。"},
        ],
    )

    assert all("confidence" in annotation for annotation in brief["annotations"])
    assert brief["summary"]["source_message_count"] == 2
    assert brief["summary"]["annotation_count"] == len(brief["annotations"])


def test_render_group_brief_markdown_keeps_message_ids_visible() -> None:
    brief = build_group_brief(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender": "老师", "content": "周五 18:00 前提交。"},
            {"message_id": "om_2", "sender": "同学", "content": "PPT 8 页。"},
        ],
    )

    markdown = render_group_brief_markdown(brief)

    assert "## 原始群聊记录" in markdown
    assert "[om_1]" in markdown
    assert "## 旁批标注" in markdown
    assert "source_note" in markdown
    assert "引用: om_1" in markdown
    assert "## 总汇总区" in markdown


def test_build_confirmation_card_contains_start_action_and_message_refs_from_external_evidence() -> None:
    brief = build_group_brief_from_evidence(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender": "老师", "content": "PPT 不超过 8 页。"},
            {"message_id": "om_2", "sender": "同学", "content": "PPT 可以 10 页？"},
        ],
        evidence_items=[
            {
                "kind": "conflict",
                "claim": "页数要求存在冲突，需要人工确认。",
                "source_message_ids": ["om_1", "om_2"],
                "confidence": "medium",
            }
        ],
    )

    card = build_confirmation_card(brief, task_id="im-om_123")

    assert card["config"]["wide_screen_mode"] is True
    assert card["header"]["title"]["content"] == "请确认群聊需求"
    assert "页数要求存在冲突" in str(card)
    assert "om_1" in str(card)
    assert "om_2" in str(card)
    assert {"tag": "button", "text": {"tag": "plain_text", "content": "开始执行"}, "type": "primary", "value": {"action": "start_task", "task_id": "im-om_123"}} in card["elements"]


def test_build_group_brief_from_evidence_uses_external_extractor_without_rule_merging() -> None:
    brief = build_group_brief_from_evidence(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender": "老师", "content": "周五 18:00 前提交。"},
            {"message_id": "om_2", "sender": "同学", "content": "项目名称还没定。"},
        ],
        evidence_items=[
            {
                "kind": "deadline",
                "claim": "正式提交截止为周五 18:00",
                "source_message_ids": ["om_1"],
                "confidence": "high",
                "extractor": "langextract-deepseek-v4-flash",
            },
            {
                "kind": "open_question",
                "claim": "项目名称仍需确认",
                "source_message_ids": ["om_2"],
                "confidence": "medium",
                "extractor": "langextract-deepseek-v4-flash",
            },
        ],
    )

    validate_group_brief(brief)
    assert [annotation["type"] for annotation in brief["annotations"]] == ["deadline", "open_question"]
    assert brief["annotations"][0]["annotation_id"] == "lx_001"
    assert brief["annotations"][1]["needs_confirmation"] is True
    assert brief["summary"]["deadlines"][0]["claim"] == "正式提交截止为周五 18:00"
