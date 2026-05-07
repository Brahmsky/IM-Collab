from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.artifacts import artifact_delivery, artifact_display, artifact_family, artifact_input, artifact_items, upsert_item
from bridge.lark_im import build_delivery_card, reply_card_to_message
from bridge.task_protocol import read_artifacts, write_artifacts

Runner = Callable[[list[str], str | None], str]


def deliver_task_to_feishu(
    task_dir: Path,
    message_id: str,
    runner: Runner | None = None,
    dry_run_reply: bool = True,
) -> dict[str, Any]:
    result = publish_task_artifacts_to_feishu(task_dir, runner=runner)
    artifacts = result["artifacts"]
    command_runner = _adapt_runner(runner)
    card_path = task_dir / "delivery_card.json"

    reply = reply_card_to_message(
        message_id,
        card_path,
        idempotency_key=f"{artifacts['task_id']}-delivery",
        dry_run=dry_run_reply,
        runner=command_runner,
    )

    return {"task_id": artifacts["task_id"], "artifacts": artifacts, "reply": reply}


def has_feishu_remote_artifacts(artifacts: dict[str, Any]) -> bool:
    for item in artifact_items(artifacts):
        remote = item.get("remote")
        if not isinstance(remote, dict):
            continue
        if remote.get("provider") != "feishu":
            continue
        if any(remote.get(field) for field in ("url", "web_url", "permalink", "document_id", "xml_presentation_id", "whiteboard_token", "token", "id")):
            return True
    return False


def has_unpublished_delivery_artifacts(artifacts: dict[str, Any]) -> bool:
    for item in artifact_items(artifacts):
        family = artifact_family(item)
        if family not in {"document", "slides", "whiteboard", "sheet", "file"}:
            continue
        remote = item.get("remote")
        if isinstance(remote, dict) and remote.get("provider") == "feishu" and any(
            remote.get(field) for field in ("url", "web_url", "permalink", "document_id", "xml_presentation_id", "whiteboard_token", "token", "id")
        ):
            continue
        if family == "file":
            continue
        return True
    return False


def publish_task_artifacts_to_feishu(
    task_dir: Path,
    runner: Runner | None = None,
) -> dict[str, Any]:
    artifacts = read_artifacts(task_dir)
    items = artifact_items(artifacts)
    published: dict[str, dict[str, Any]] = {}

    document_item = _first_item(items, "document")
    document_remote = _feishu_remote(document_item)
    if document_item is not None and document_remote is not None:
        published["document"] = upsert_item(
            artifacts,
            str(document_item.get("id") or document_item.get("kind") or "document"),
            _artifact_schema_update(document_item, document_remote),
        )

    slides_item = _first_item(items, "slides", "presentation")
    slides_remote = _feishu_remote(slides_item)
    if slides_item is not None and slides_remote is not None:
        published["slides"] = upsert_item(
            artifacts,
            str(slides_item.get("id") or slides_item.get("kind") or "slides"),
            _artifact_schema_update(slides_item, slides_remote),
        )

    whiteboard_item = _first_item(items, "whiteboard", "diagram", "mermaid")
    whiteboard_remote = _feishu_remote(whiteboard_item)
    if whiteboard_item is not None and whiteboard_remote is not None:
        whiteboard_url = _whiteboard_target_url({"remote": whiteboard_remote}, published.get("document"))
        published["whiteboard"] = upsert_item(
            artifacts,
            str(whiteboard_item.get("id") or whiteboard_item.get("kind") or "whiteboard"),
            _artifact_schema_update(
                whiteboard_item,
                {
                    **whiteboard_remote,
                    **({"url": whiteboard_url} if whiteboard_url and not whiteboard_remote.get("url") else {}),
                },
            ),
        )

    if not published:
        raise ValueError("no Feishu remote artifacts found; publish path requires Codex to create remote objects directly")

    artifacts["summary"] = _append_publish_summary(str(artifacts["summary"]))
    write_artifacts(task_dir, artifacts)
    (task_dir / "delivery_card.json").write_text(
        json.dumps(build_delivery_card(artifacts), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {"task_id": artifacts["task_id"], "artifacts": artifacts}


def _first_item(items: list[dict[str, Any]], *kinds: str) -> dict[str, Any] | None:
    wanted = {kind.lower() for kind in kinds}
    for item in items:
        values = {str(item.get("kind") or "").lower(), str(item.get("type") or "").lower(), str(item.get("id") or "").lower()}
        if values & wanted:
            return item
    return None


def _artifact_title(artifacts: dict[str, Any], item: dict[str, Any], fallback: str) -> str:
    return str(item.get("title") or f"IM-Collab {artifacts['task_id']} {fallback}")


def _adapt_runner(runner: Runner | None):
    if runner is None:
        return None

    def run_without_input(args: list[str]) -> str:
        return runner(args, None)

    return run_without_input


def _feishu_remote(item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is None:
        return None
    remote = item.get("remote")
    if isinstance(remote, dict) and remote.get("provider") == "feishu":
        return remote
    return None


def _append_publish_summary(summary: str) -> str:
    suffix = "Published to Feishu via lark-cli."
    if suffix in summary:
        return summary
    if not summary:
        return suffix
    return f"{summary} {suffix}"


def _artifact_schema_update(item: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    candidate = {
        **item,
        "family": artifact_family(item),
        "input": artifact_input(item),
        "remote": remote,
        "output": {**remote, "provider": str(remote.get("provider") or "feishu"), "object_type": artifact_family(item)},
    }
    candidate["display"] = artifact_display(candidate)
    candidate["delivery"] = artifact_delivery(candidate)
    return candidate


def _whiteboard_target_url(target_item: dict[str, Any], document_item: dict[str, Any] | None) -> str | None:
    target_remote = _feishu_remote(target_item)
    if target_remote and target_remote.get("url"):
        return str(target_remote["url"])
    document_remote = _feishu_remote(document_item)
    if document_remote and document_remote.get("url"):
        return str(document_remote["url"])
    return None
