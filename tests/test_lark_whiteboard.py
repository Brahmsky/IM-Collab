from __future__ import annotations

import json
from pathlib import Path

from bridge.lark_whiteboard import (
    append_whiteboard_to_doc,
    build_append_whiteboard_args,
    build_update_whiteboard_args,
    update_whiteboard_from_mermaid,
)


def test_build_append_whiteboard_args_uses_existing_docs_update_command() -> None:
    args = build_append_whiteboard_args("doc_123", dry_run=True)

    assert args == [
        "lark-cli",
        "docs",
        "+update",
        "--api-version",
        "v2",
        "--as",
        "user",
        "--doc",
        "doc_123",
        "--command",
        "append",
        "--content",
        '<whiteboard type="blank"></whiteboard>',
        "--doc-format",
        "xml",
        "--dry-run",
    ]


def test_append_whiteboard_to_doc_extracts_block_metadata() -> None:
    def fake_run(args: list[str], input_text: str | None = None) -> str:
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

    result = append_whiteboard_to_doc("doc_123", runner=fake_run)

    assert result["whiteboard_token"] == "whiteboard_123"
    assert result["block_id"] == "block_123"


def test_build_update_whiteboard_args_uses_mermaid_stdin() -> None:
    args = build_update_whiteboard_args("whiteboard_123", idempotency_token="task-board", dry_run=True)

    assert args == [
        "lark-cli",
        "whiteboard",
        "+update",
        "--as",
        "user",
        "--whiteboard-token",
        "whiteboard_123",
        "--source",
        "-",
        "--input_format",
        "mermaid",
        "--idempotent-token",
        "task-board",
        "--overwrite",
        "--yes",
        "--dry-run",
    ]


def test_update_whiteboard_from_mermaid_sends_file_content(tmp_path: Path) -> None:
    mermaid = tmp_path / "whiteboard.mmd"
    mermaid.write_text("flowchart TD\nA-->B\n", encoding="utf-8")
    seen_input = ""

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        nonlocal seen_input
        seen_input = input_text or ""
        return json.dumps({"ok": True, "data": {"created_node_id": "t1:2"}})

    result = update_whiteboard_from_mermaid(
        "whiteboard_123",
        mermaid,
        idempotency_token="task-board",
        runner=fake_run,
    )

    assert seen_input == "flowchart TD\nA-->B\n"
    assert result["created_node_id"] == "t1:2"
