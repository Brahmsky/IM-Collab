from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

Runner = Callable[[list[str]], str]


def build_create_doc_args(markdown_path: Path, title: str, dry_run: bool = False) -> list[str]:
    args = [
        "lark-cli",
        "docs",
        "+create",
        "--api-version",
        "v2",
        "--title",
        title,
        "--content",
        f"@{markdown_path.as_posix()}",
        "--doc-format",
        "markdown",
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def create_doc_from_markdown(
    markdown_path: Path,
    title: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    markdown_path = markdown_path.resolve()
    args = build_create_doc_args(Path(markdown_path.name), title, dry_run=dry_run)
    output = runner(args) if runner else _subprocess_runner(args, cwd=markdown_path.parent)
    return {"ok": True, "dry_run": dry_run, "response": _extract_json(output), "raw": output}


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
