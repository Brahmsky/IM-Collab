from __future__ import annotations

import json
from pathlib import Path

from bridge.feishu_delivery import deliver_task_to_feishu, publish_task_artifacts_to_feishu
from bridge.local_codex_smoke import run_local_smoke
from bridge.task_protocol import create_task, read_artifacts


def test_deliver_task_to_feishu_publishes_artifacts_and_replies(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate office artifacts.")
    run_local_smoke(task_dir)
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
    assert result["task_id"] == "im-om_123"
    assert artifacts["document"]["remote"]["url"] == "https://example.feishu.cn/docx/doc_123"
    assert artifacts["slides"]["remote"]["slides_added"] == 8
    assert artifacts["whiteboard"]["remote"]["whiteboard_token"] == "whiteboard_123"
    assert artifacts["whiteboard"]["remote"]["created_node_id"] == "t1:2"
    reply_call = next(call for call in calls if call[:3] == ["lark-cli", "im", "+messages-reply"])
    assert reply_call[reply_call.index("--msg-type") + 1] == "interactive"
    assert "办公材料已生成" in reply_call[reply_call.index("--content") + 1]
    assert "--markdown" not in reply_call


def test_publish_task_artifacts_to_feishu_does_not_reply(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate office artifacts.")
    run_local_smoke(task_dir)
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

    assert result["artifacts"]["document"]["remote"]["url"] == "doc_url"
    delivery_card = json.loads((task_dir / "delivery_card.json").read_text(encoding="utf-8"))
    assert delivery_card["header"]["title"]["content"] == "办公材料已生成"
    assert "doc_url" in str(delivery_card)
    assert not any(call[:3] == ["lark-cli", "im", "+messages-reply"] for call in calls)
