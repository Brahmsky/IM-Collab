from __future__ import annotations

import json
import subprocess
from pathlib import Path

from bridge import lark_docs
from bridge.lark_docs import build_create_doc_args, create_doc, create_doc_from_docx_xml, create_doc_from_markdown


def test_build_create_doc_args_uses_v2_markdown_content() -> None:
    args = build_create_doc_args("@document.md", title="IM-Collab Smoke", dry_run=True)

    assert args == [
        "lark-cli",
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--title",
        "IM-Collab Smoke",
        "--content",
        "@document.md",
        "--doc-format",
        "markdown",
        "--dry-run",
    ]


def test_build_create_doc_args_supports_xml_inline_content() -> None:
    args = build_create_doc_args("<docx><p>Demo</p></docx>", title="XML Demo", doc_format="xml", dry_run=True)

    assert args == [
        "lark-cli",
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--title",
        "XML Demo",
        "--content",
        "<docx><p>Demo</p></docx>",
        "--doc-format",
        "xml",
        "--dry-run",
    ]


def test_create_doc_from_markdown_runs_cli_and_extracts_json(tmp_path: Path) -> None:
    document = tmp_path / "document.md"
    document.write_text("# Demo\n", encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "warning\n=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/docs_ai/v1/documents"}]})

    result = create_doc_from_markdown(document, title="Demo", dry_run=True, runner=fake_run)

    assert seen_args[-1] == "--dry-run"
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["response"]["api"][0]["url"] == "/open-apis/docs_ai/v1/documents"


def test_create_doc_from_markdown_passes_relative_content_path_to_cli(tmp_path: Path) -> None:
    document = tmp_path / "document.md"
    document.write_text("# Demo\n", encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return json.dumps({"ok": True})

    create_doc_from_markdown(document, title="Demo", runner=fake_run)

    content_index = seen_args.index("--content")
    assert seen_args[content_index + 1] == "@document.md"


def test_create_doc_supports_inline_xml_content() -> None:
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return json.dumps({"ok": True})

    create_doc(title="Inline XML", content="<docx><p>Hi</p></docx>", doc_format="xml", runner=fake_run)

    content_index = seen_args.index("--content")
    assert seen_args[content_index + 1] == "<docx><p>Hi</p></docx>"
    assert seen_args[seen_args.index("--doc-format") + 1] == "xml"


def test_create_doc_from_docx_xml_uses_xml_format(tmp_path: Path) -> None:
    document = tmp_path / "document.xml"
    document.write_text("<docx><p>Demo</p></docx>", encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return json.dumps({"ok": True})

    create_doc_from_docx_xml(document, title="XML Demo", runner=fake_run)

    assert seen_args[seen_args.index("--doc-format") + 1] == "xml"


def test_create_doc_from_markdown_runs_subprocess_from_file_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    document = tmp_path / "document.md"
    document.write_text("# Demo\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_subprocess_run(args, **kwargs):
        seen["args"] = args
        seen["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps({"ok": True}), stderr="")

    monkeypatch.setattr(lark_docs.subprocess, "run", fake_subprocess_run)

    create_doc_from_markdown(document, title="Demo")

    assert seen["cwd"] == tmp_path
    assert "--content" in seen["args"]
    content_index = seen["args"].index("--content")
    assert seen["args"][content_index + 1] == "@document.md"
