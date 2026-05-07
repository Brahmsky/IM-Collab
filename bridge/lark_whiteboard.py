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
    input_format: str = "mermaid",
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
        input_format,
        "--idempotent-token",
        idempotency_token,
        "--overwrite",
        "--yes",
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def update_whiteboard_from_source(
    whiteboard_token: str,
    source_path: Path,
    idempotency_token: str,
    input_format: str = "mermaid",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    input_text = source_path.read_text(encoding="utf-8")
    output = _run(
        build_update_whiteboard_args(whiteboard_token, idempotency_token, input_format=input_format, dry_run=dry_run),
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


def update_whiteboard_from_mermaid(
    whiteboard_token: str,
    mermaid_path: Path,
    idempotency_token: str,
    input_format: str = "mermaid",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    return update_whiteboard_from_source(
        whiteboard_token,
        mermaid_path,
        idempotency_token=idempotency_token,
        input_format=input_format,
        dry_run=dry_run,
        runner=runner,
    )


def ensure_whiteboard_target(
    item: dict[str, Any],
    *,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    remote = _feishu_remote(item)
    if remote.get("whiteboard_token"):
        return {
            "document_id": _string_or_none(remote.get("document_id")),
            "whiteboard_token": str(remote["whiteboard_token"]),
            "block_id": _string_or_none(remote.get("block_id")),
        }

    document_ref = _string_or_none(remote.get("document_id")) or _string_or_none(remote.get("url"))
    if not document_ref:
        raise ValueError("whiteboard continuation requires a Feishu whiteboard or document remote")

    appended = append_whiteboard_to_doc(document_ref, dry_run=dry_run, runner=runner)
    return {
        "document_id": _string_or_none(remote.get("document_id")) or document_ref,
        "whiteboard_token": _string_or_none(appended.get("whiteboard_token")),
        "block_id": _string_or_none(appended.get("block_id")),
    }


def create_or_update_whiteboard_from_source(
    source_path: Path,
    *,
    idempotency_token: str,
    document_id_or_url: str | None = None,
    whiteboard_token: str | None = None,
    input_format: str = "mermaid",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    target: dict[str, Any]
    if whiteboard_token:
        target = {"document_id": document_id_or_url, "whiteboard_token": whiteboard_token, "block_id": None}
    elif document_id_or_url:
        target = ensure_whiteboard_target(
            {"remote": {"provider": "feishu", "document_id": document_id_or_url, "url": document_id_or_url}},
            dry_run=dry_run,
            runner=runner,
        )
    else:
        raise ValueError("either document_id_or_url or whiteboard_token is required")

    update = update_whiteboard_from_source(
        str(target["whiteboard_token"]),
        source_path,
        idempotency_token=idempotency_token,
        input_format=input_format,
        dry_run=dry_run,
        runner=runner,
    )
    return {**target, "created_node_id": update.get("created_node_id"), "response": update.get("response"), "raw": update.get("raw")}


def create_or_update_whiteboard_from_mermaid(
    mermaid_path: Path,
    *,
    idempotency_token: str,
    document_id_or_url: str | None = None,
    whiteboard_token: str | None = None,
    input_format: str = "mermaid",
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    return create_or_update_whiteboard_from_source(
        mermaid_path,
        idempotency_token=idempotency_token,
        document_id_or_url=document_id_or_url,
        whiteboard_token=whiteboard_token,
        input_format=input_format,
        dry_run=dry_run,
        runner=runner,
    )


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


def _feishu_remote(item: dict[str, Any]) -> dict[str, Any]:
    remote = item.get("remote")
    if not isinstance(remote, dict) or remote.get("provider") != "feishu":
        raise ValueError("whiteboard continuation requires remote.provider=feishu")
    return remote


def _string_or_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
