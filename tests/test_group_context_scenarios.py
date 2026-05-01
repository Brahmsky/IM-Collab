from __future__ import annotations

import json
from pathlib import Path

from bridge.group_context import build_standard_group_context, read_fixture_context

SCENARIO_ROOT = Path("examples") / "scenarios" / "group_briefing"


def test_standard_group_briefing_scenarios_are_loadable() -> None:
    scenario_paths = sorted(SCENARIO_ROOT.glob("*/context.json"))

    assert [path.parent.name for path in scenario_paths] == [
        "client_launch_review_long_context",
        "course_project_conflict",
        "grant_application_ultra_long_context",
    ]
    for scenario_path in scenario_paths:
        messages = build_standard_group_context(scenario_path)
        assert len(messages) >= 12
        assert all(message["message_id"] for message in messages)
        assert all(message["chat_id"] for message in messages)
        assert all(message["content"] for message in messages)
        assert all(message.get("sender_id") for message in messages)
        assert all(message.get("sender") for message in messages)


def test_course_project_conflict_expected_brief_references_existing_messages() -> None:
    scenario_dir = SCENARIO_ROOT / "course_project_conflict"
    messages = build_standard_group_context(scenario_dir / "context.json")
    expected = json.loads((scenario_dir / "expected_brief.json").read_text(encoding="utf-8"))
    message_ids = {message["message_id"] for message in messages}

    assert expected["scenario_id"] == "course_project_conflict"
    assert expected["conflicts"]
    assert expected["open_questions"]
    for item in expected["facts"] + expected["conflicts"] + expected["open_questions"]:
        assert set(item["source_message_ids"]) <= message_ids


def test_long_context_scenario_can_be_windowed_for_future_selection_tests() -> None:
    scenario_path = SCENARIO_ROOT / "client_launch_review_long_context" / "context.json"
    messages = build_standard_group_context(scenario_path)

    assert len(messages) >= 35
    latest = read_fixture_context(scenario_path, chat_id="oc_client_launch", page_size=12)

    assert len(latest) == 12
    assert latest[0]["message_id"] == messages[-12]["message_id"]
    assert latest[-1]["message_id"] == messages[-1]["message_id"]


def test_grant_application_ultra_long_context_has_rich_material_surface() -> None:
    scenario_dir = SCENARIO_ROOT / "grant_application_ultra_long_context"
    messages = build_standard_group_context(scenario_dir / "context.json")
    expected = json.loads((scenario_dir / "expected_brief.json").read_text(encoding="utf-8"))
    message_ids = {message["message_id"] for message in messages}
    attachments = [attachment for message in messages for attachment in message.get("attachments", [])]

    assert len(messages) >= 60
    assert len({message["sender_id"] for message in messages}) >= 8
    assert len(attachments) >= 8
    assert any(attachment.get("name", "").endswith(".pptx") for attachment in attachments)
    assert expected["scenario_id"] == "grant_application_ultra_long_context"
    assert len(expected["facts"]) >= 8
    assert len(expected["conflicts"]) >= 3
    assert len(expected["open_questions"]) >= 2
    for item in expected["facts"] + expected["conflicts"] + expected["open_questions"]:
        assert set(item["source_message_ids"]) <= message_ids
