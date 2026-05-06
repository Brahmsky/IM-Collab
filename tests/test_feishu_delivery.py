from __future__ import annotations

import json
from pathlib import Path

from bridge.feishu_delivery import _local_artifact_path, deliver_task_to_feishu, publish_task_artifacts_to_feishu
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


def _seed_local_publishable_artifacts(task_dir: Path) -> None:
    document = task_dir / "document.md"
    slides = task_dir / "slides.md"
    board = task_dir / "whiteboard.mmd"
    document.write_text("# 示例文档\n", encoding="utf-8")
    slides.write_text("# Deck\n\n## Slide 1: Cover\nIntro\n", encoding="utf-8")
    board.write_text("flowchart TD\nA-->B\n", encoding="utf-8")
    _write_task_artifacts(
        task_dir,
        [
            {"id": "document", "kind": "document", "type": "markdown", "path": document.as_posix()},
            {"id": "slides", "kind": "slides", "type": "markdown", "path": slides.as_posix()},
            {"id": "whiteboard", "kind": "whiteboard", "type": "mermaid", "path": board.as_posix()},
        ],
    )


def test_deliver_task_to_feishu_publishes_artifacts_and_replies(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate office artifacts.")
    _seed_local_publishable_artifacts(task_dir)
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        command = " ".join(args[:3])
        if command == "lark-cli docs +create":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "document_id": "doc_123",
                            "url": "https://example.feishu.cn/docx/doc_123",
                        },
                        "log_id": "log_doc",
                    },
                }
            )
        if command == "lark-cli slides +create":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "xml_presentation_id": "slides_123",
                        "url": "https://example.feishu.cn/slides/slides_123",
                        "slides_added": 8,
                    },
                }
            )
        if command == "lark-cli docs +update":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "new_blocks": [
                                {
                                    "block_id": "block_123",
                                    "block_token": "whiteboard_123",
                                    "block_type": "whiteboard",
                                }
                            ]
                        }
                    },
                }
            )
        if command == "lark-cli whiteboard +update":
            assert input_text and "flowchart TD" in input_text
            return json.dumps({"ok": True, "data": {"created_node_id": "t1:2"}})
        if command == "lark-cli im +messages-reply":
            return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/im/v1/messages/om_123/reply"}]})
        raise AssertionError(f"unexpected command: {args}")

    result = deliver_task_to_feishu(task_dir, message_id="om_123", runner=fake_run, dry_run_reply=True)

    artifacts = read_artifacts(task_dir)
    items = {item["kind"]: item for item in artifacts["items"]}
    assert result["task_id"] == "im-om_123"
    assert items["document"]["remote"]["url"] == "https://example.feishu.cn/docx/doc_123"
    assert items["slides"]["remote"]["slides_added"] == 8
    assert items["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_123"
    assert items["whiteboard"]["remote"]["created_node_id"] == "t1:2"
    reply_call = next(call for call in calls if call[:3] == ["lark-cli", "im", "+messages-reply"])
    assert reply_call[reply_call.index("--msg-type") + 1] == "interactive"
    assert "材料已生成" in reply_call[reply_call.index("--content") + 1]
    assert "--markdown" not in reply_call


def test_publish_task_artifacts_to_feishu_does_not_reply(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate office artifacts.")
    _seed_local_publishable_artifacts(task_dir)
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        command = " ".join(args[:3])
        if command == "lark-cli docs +create":
            return json.dumps({"ok": True, "data": {"document": {"document_id": "doc_123", "url": "doc_url"}}})
        if command == "lark-cli slides +create":
            return json.dumps(
                {"ok": True, "data": {"xml_presentation_id": "slides_123", "url": "slides_url", "slides_added": 8}}
            )
        if command == "lark-cli docs +update":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "new_blocks": [
                                {"block_id": "block_123", "block_token": "whiteboard_123", "block_type": "whiteboard"}
                            ]
                        }
                    },
                }
            )
        if command == "lark-cli whiteboard +update":
            return json.dumps({"ok": True, "data": {"created_node_id": "t1:2"}})
        raise AssertionError(f"unexpected command: {args}")

    result = publish_task_artifacts_to_feishu(task_dir, runner=fake_run)

    items = {item["kind"]: item for item in result["artifacts"]["items"]}
    assert items["document"]["remote"]["url"] == "doc_url"
    delivery_card = json.loads((task_dir / "delivery_card.json").read_text(encoding="utf-8"))
    assert delivery_card["header"]["title"]["content"] == "材料已生成"
    assert "doc_url" in str(delivery_card)
    assert not any(call[:3] == ["lark-cli", "im", "+messages-reply"] for call in calls)


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
                    "block_id": "block_existing",
                },
            },
        ],
    )

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        raise AssertionError(f"unexpected command: {args}, input={input_text!r}")

    result = publish_task_artifacts_to_feishu(task_dir, runner=fake_run)

    items = {item["kind"]: item for item in result["artifacts"]["items"]}
    assert items["document"]["remote"]["document_id"] == "doc_existing"
    assert items["slides"]["remote"]["xml_presentation_id"] == "slides_existing"
    assert items["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_existing"
    assert result["artifacts"]["summary"].endswith("Published to Feishu via lark-cli.")


def test_publish_task_artifacts_to_feishu_mixes_local_and_remote_items(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-mixed", "Publish local and remote artifacts together.")
    slides_path = task_dir / "slides.md"
    whiteboard_path = task_dir / "board.mmd"
    slides_path.write_text("# Slide deck\n\n## Slide 1\nReady\n", encoding="utf-8")
    whiteboard_path.write_text("flowchart TD\nA-->B\n", encoding="utf-8")
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
            {"id": "slides", "kind": "slides", "type": "markdown", "path": slides_path.as_posix()},
            {"id": "whiteboard", "kind": "whiteboard", "type": "mermaid", "path": whiteboard_path.as_posix()},
        ],
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        command = " ".join(args[:3])
        if command == "lark-cli slides +create":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "xml_presentation_id": "slides_123",
                        "url": "https://example.feishu.cn/slides/slides_123",
                        "slides_added": 1,
                    },
                }
            )
        if command == "lark-cli docs +update":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "new_blocks": [
                                {
                                    "block_id": "block_123",
                                    "block_token": "whiteboard_123",
                                    "block_type": "whiteboard",
                                }
                            ]
                        }
                    },
                }
            )
        if command == "lark-cli whiteboard +update":
            assert input_text == "flowchart TD\nA-->B\n"
            return json.dumps({"ok": True, "data": {"created_node_id": "t1:2"}})
        raise AssertionError(f"unexpected command: {args}")

    result = publish_task_artifacts_to_feishu(task_dir, runner=fake_run)

    items = {item["kind"]: item for item in result["artifacts"]["items"]}
    assert items["document"]["remote"]["document_id"] == "doc_existing"
    assert items["slides"]["remote"]["xml_presentation_id"] == "slides_123"
    assert items["whiteboard"]["remote"]["document_id"] == "doc_existing"
    assert items["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_123"
    assert not any(call[:3] == ["lark-cli", "docs", "+create"] for call in calls)


def test_publish_task_artifacts_to_feishu_continues_existing_whiteboard_remote(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-board-continue", "Continue an existing whiteboard.")
    whiteboard_path = task_dir / "board.mmd"
    whiteboard_path.write_text("flowchart TD\nStart-->End\n", encoding="utf-8")
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
                "id": "whiteboard",
                "kind": "whiteboard",
                "type": "mermaid",
                "path": whiteboard_path.as_posix(),
                "remote": {
                    "provider": "feishu",
                    "document_id": "doc_existing",
                    "whiteboard_token": "whiteboard_existing",
                    "block_id": "block_existing",
                },
            },
        ],
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        if args[:3] == ["lark-cli", "whiteboard", "+update"]:
            assert input_text == "flowchart TD\nStart-->End\n"
            return json.dumps({"ok": True, "data": {"created_node_id": "t1:9"}})
        raise AssertionError(f"unexpected command: {args}")

    result = publish_task_artifacts_to_feishu(task_dir, runner=fake_run)

    items = {item["kind"]: item for item in result["artifacts"]["items"]}
    assert items["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_existing"
    assert items["whiteboard"]["remote"]["created_node_id"] == "t1:9"
    assert not any(call[:3] == ["lark-cli", "docs", "+update"] for call in calls)


def test_local_artifact_path_accepts_repo_relative_task_path(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "task-1", "Generate a reply.")
    reply = task_dir / "reply.md"
    reply.write_text("ok\n", encoding="utf-8")

    resolved = _local_artifact_path(task_dir, {"kind": "message", "path": "tasks/task-1/reply.md"})

    assert resolved == reply
