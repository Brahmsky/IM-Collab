from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from bridge.lark_whiteboard import (
    append_whiteboard_to_doc,
    build_append_whiteboard_args,
    build_update_whiteboard_args,
    ensure_whiteboard_target,
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


def test_build_update_whiteboard_args_supports_other_input_formats() -> None:
    args = build_update_whiteboard_args(
        "whiteboard_123",
        idempotency_token="task-board",
        input_format="plantuml",
        dry_run=True,
    )

    assert args[args.index("--input_format") + 1] == "plantuml"


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
        input_format="mermaid",
        runner=fake_run,
    )

    assert seen_input == "flowchart TD\nA-->B\n"
    assert result["created_node_id"] == "t1:2"


def test_create_feishu_whiteboard_script_updates_existing_board(tmp_path: Path, monkeypatch, capsys) -> None:
    mermaid = tmp_path / "whiteboard.mmd"
    mermaid.write_text("flowchart TD\nA-->B\n", encoding="utf-8")
    repo = Path(__file__).resolve().parents[1]
    script_path = repo / "scripts" / "create_feishu_whiteboard.py"
    spec = importlib.util.spec_from_file_location("create_feishu_whiteboard", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fake_create_or_update(
        mermaid_path: Path,
        *,
        idempotency_token: str,
        document_id_or_url: str | None = None,
        whiteboard_token: str | None = None,
        input_format: str = "mermaid",
        dry_run: bool = False,
        runner=None,
    ) -> dict[str, object]:
        assert whiteboard_token == "wb_123"
        assert mermaid_path == mermaid
        assert idempotency_token == "task-board"
        assert document_id_or_url is None
        assert input_format == "mermaid"
        assert dry_run is True
        return {"ok": True, "created_node_id": "t1:2"}

    monkeypatch.setattr(module, "create_or_update_whiteboard_from_source", fake_create_or_update)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_feishu_whiteboard.py",
            str(mermaid),
            "--whiteboard-token",
            "wb_123",
            "--idempotency-token",
            "task-board",
        ],
    )

    assert module.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["created_node_id"] == "t1:2"


def test_ensure_whiteboard_target_reuses_existing_whiteboard_remote() -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        raise AssertionError(f"unexpected command: {args}")

    result = ensure_whiteboard_target(
        {"remote": {"provider": "feishu", "document_id": "doc_123", "whiteboard_token": "whiteboard_123", "block_id": "block_123"}},
        runner=fake_run,
    )

    assert result == {"document_id": "doc_123", "whiteboard_token": "whiteboard_123", "block_id": "block_123"}
    assert calls == []


def test_ensure_whiteboard_target_appends_when_only_document_remote_exists() -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
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

    result = ensure_whiteboard_target({"remote": {"provider": "feishu", "document_id": "doc_123"}}, runner=fake_run)

    assert result == {"document_id": "doc_123", "whiteboard_token": "whiteboard_123", "block_id": "block_123"}
    assert calls == [build_append_whiteboard_args("doc_123", dry_run=False)]
