from __future__ import annotations

import json
from pathlib import Path

import pytest

from bridge.feishu_delivery import (
    deliver_task_to_feishu,
    has_feishu_remote_artifacts,
    has_unpublished_delivery_artifacts,
    publish_task_artifacts_to_feishu,
)
from bridge.task_protocol import create_task, read_artifacts, write_artifacts


def _write_task_artifacts(task_dir: Path, items: list[dict[str, object]]) -> None:
    write_artifacts(
        task_dir,
        {
            "task_id": task_dir.name,
            "items": items,
            "summary": "Task artifacts ready.",
            "next_steps": [],
        },
    )


def test_publish_task_artifacts_to_feishu_requires_remote_feishu_artifacts(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-local-only", "Publish local artifacts.")
    local_file = task_dir / "deck.pptx"
    local_file.write_text("fake", encoding="utf-8")
    _write_task_artifacts(
        task_dir,
        [{"id": "slides", "kind": "slides", "type": "pptx", "path": local_file.as_posix()}],
    )

    with pytest.raises(ValueError, match="no Feishu remote artifacts found"):
        publish_task_artifacts_to_feishu(task_dir)


def test_publish_task_artifacts_to_feishu_reuses_remote_only_items(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-remote-only", "Reuse existing Feishu artifacts.")
    _write_task_artifacts(
        task_dir,
        [
            {
                "id": "document",
                "kind": "document",
                "remote": {
                    "provider": "feishu",
                    "document_id": "doc_existing",
                    "url": "https://example.feishu.cn/docx/doc_existing",
                },
            },
            {
                "id": "slides",
                "kind": "slides",
                "remote": {
                    "provider": "feishu",
                    "xml_presentation_id": "slides_existing",
                    "url": "https://example.feishu.cn/slides/slides_existing",
                },
            },
            {
                "id": "whiteboard",
                "kind": "whiteboard",
                "remote": {
                    "provider": "feishu",
                    "document_id": "doc_existing",
                    "whiteboard_token": "whiteboard_existing",
                    "url": "https://example.feishu.cn/docx/doc_existing#whiteboard",
                },
            },
        ],
    )

    result = publish_task_artifacts_to_feishu(task_dir)

    items = {item["kind"]: item for item in result["artifacts"]["items"]}
    assert items["document"]["remote"]["document_id"] == "doc_existing"
    assert items["slides"]["remote"]["xml_presentation_id"] == "slides_existing"
    assert items["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_existing"
    assert result["artifacts"]["summary"].endswith("Published to Feishu via lark-cli.")


def test_deliver_task_to_feishu_replies_with_delivery_card_from_remote_items(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Deliver existing remote artifacts.")
    _write_task_artifacts(
        task_dir,
        [
            {
                "id": "document",
                "kind": "document",
                "remote": {
                    "provider": "feishu",
                    "document_id": "doc_123",
                    "url": "https://example.feishu.cn/docx/doc_123",
                },
            }
        ],
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        if args[:3] == ["lark-cli", "im", "+messages-reply"]:
            return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/im/v1/messages/om_123/reply"}]})
        raise AssertionError(f"unexpected command: {args}")

    result = deliver_task_to_feishu(task_dir, message_id="om_123", runner=fake_run, dry_run_reply=True)

    artifacts = read_artifacts(task_dir)
    assert result["task_id"] == "im-om_123"
    assert artifacts["items"][0]["remote"]["document_id"] == "doc_123"
    reply_call = next(call for call in calls if call[:3] == ["lark-cli", "im", "+messages-reply"])
    assert reply_call[reply_call.index("--msg-type") + 1] == "interactive"


def test_has_feishu_remote_artifacts_requires_real_remote_metadata() -> None:
    assert has_feishu_remote_artifacts(
        {
            "task_id": "demo",
            "summary": "ok",
            "next_steps": [],
            "items": [
                {"id": "document", "kind": "document", "remote": {"provider": "feishu", "document_id": "doc_123"}}
            ],
        }
    )
    assert not has_feishu_remote_artifacts(
        {
            "task_id": "demo",
            "summary": "ok",
            "next_steps": [],
            "items": [{"id": "document", "kind": "document", "path": "document.md"}],
        }
    )


def test_has_unpublished_delivery_artifacts_flags_local_only_deliverables() -> None:
    assert has_unpublished_delivery_artifacts(
        {
            "task_id": "demo",
            "summary": "ok",
            "next_steps": [],
            "items": [{"id": "slides", "kind": "slides", "path": "deck.pptx"}],
        }
    )
    assert not has_unpublished_delivery_artifacts(
        {
            "task_id": "demo",
            "summary": "ok",
            "next_steps": [],
            "items": [
                {
                    "id": "slides",
                    "kind": "slides",
                    "remote": {
                        "provider": "feishu",
                        "xml_presentation_id": "slides_123",
                        "url": "https://example.feishu.cn/slides/slides_123",
                    },
                }
            ],
        }
    )
