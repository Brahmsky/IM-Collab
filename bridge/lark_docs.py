from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

Runner = Callable[[list[str]], str]


def build_create_doc_args(content: str, title: str, doc_format: str = "markdown", dry_run: bool = False) -> list[str]:
    args = [
        "lark-cli",
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--title",
        title,
        "--content",
        content,
        "--doc-format",
        doc_format,
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def create_doc(
    *,
    title: str,
    content: str | None = None,
    content_path: Path | None = None,
    doc_format: str = "markdown",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    if (content is None) == (content_path is None):
        raise ValueError("exactly one of content or content_path is required")

    cwd: Path | None = None
    if content_path is not None:
        resolved = content_path.resolve()
        args = build_create_doc_args(f"@{resolved.name}", title, doc_format=doc_format, dry_run=dry_run)
        cwd = resolved.parent
    else:
        args = build_create_doc_args(str(content), title, doc_format=doc_format, dry_run=dry_run)

    output = runner(args) if runner else _subprocess_runner(args, cwd=cwd)
    return {"ok": True, "dry_run": dry_run, "response": _extract_json(output), "raw": output}


def create_doc_from_markdown(
    markdown_path: Path,
    title: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    return create_doc(
        title=title,
        content_path=markdown_path,
        doc_format="markdown",
        dry_run=dry_run,
        runner=runner,
    )


def create_doc_from_docx_xml(
    xml_path: Path,
    title: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    return create_doc(
        title=title,
        content_path=xml_path,
        doc_format="xml",
        dry_run=dry_run,
        runner=runner,
    )


def _subprocess_runner(args: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(args, text=True, capture_output=True, cwd=cwd)
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli command failed\n"
            f"cwd: {cwd or Path.cwd()}\n"
            f"command: {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def _extract_json(output: str) -> dict[str, Any]:
    marker = "=== Dry Run ==="
    if marker in output:
        output = output.split(marker, 1)[1]
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("lark-cli output did not contain a JSON object")
    data = json.loads(output[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("lark-cli JSON root was not an object")
    return data
