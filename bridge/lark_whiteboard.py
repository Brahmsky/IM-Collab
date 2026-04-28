from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from bridge.lark_docs import _extract_json

Runner = Callable[[list[str], str | None], str]


def build_append_whiteboard_args(document_id_or_url: str, dry_run: bool = False) -> list[str]:
    args = [
        "lark-cli",
        "docs",
        "+update",
        "--api-version",
        "v2",
        "--as",
        "user",
        "--doc",
        document_id_or_url,
        "--command",
        "append",
        "--content",
        '<whiteboard type="blank"></whiteboard>',
        "--doc-format",
        "xml",
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def append_whiteboard_to_doc(
    document_id_or_url: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    output = _run(build_append_whiteboard_args(document_id_or_url, dry_run=dry_run), None, runner)
    response = _extract_json(output)
    block = _first_whiteboard_block(response)
    return {
        "ok": True,
        "dry_run": dry_run,
        "response": response,
        "block_id": block.get("block_id"),
        "whiteboard_token": block.get("block_token"),
        "raw": output,
    }


def build_update_whiteboard_args(
    whiteboard_token: str,
    idempotency_token: str,
    dry_run: bool = False,
) -> list[str]:
    args = [
        "lark-cli",
        "whiteboard",
        "+update",
        "--as",
        "user",
        "--whiteboard-token",
        whiteboard_token,
        "--source",
        "-",
        "--input_format",
        "mermaid",
        "--idempotent-token",
        idempotency_token,
        "--overwrite",
        "--yes",
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def update_whiteboard_from_mermaid(
    whiteboard_token: str,
    mermaid_path: Path,
    idempotency_token: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    input_text = mermaid_path.read_text(encoding="utf-8")
    output = _run(
        build_update_whiteboard_args(whiteboard_token, idempotency_token, dry_run=dry_run),
        input_text,
        runner,
    )
    response = _extract_json(output)
    return {
        "ok": True,
        "dry_run": dry_run,
        "response": response,
        "created_node_id": response.get("data", {}).get("created_node_id"),
        "raw": output,
    }


def _run(args: list[str], input_text: str | None, runner: Runner | None) -> str:
    if runner:
        return runner(args, input_text)
    completed = subprocess.run(args, input=input_text, check=True, text=True, capture_output=True)
    return completed.stdout


def _first_whiteboard_block(response: dict[str, Any]) -> dict[str, Any]:
    blocks = response.get("data", {}).get("document", {}).get("new_blocks", [])
    for block in blocks:
        if block.get("block_type") == "whiteboard":
            return block
    raise ValueError("lark-cli response did not contain a new whiteboard block")
