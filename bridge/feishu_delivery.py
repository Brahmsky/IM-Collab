from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.artifacts import artifact_items, resolve_local_path, upsert_item
from bridge.lark_docs import create_doc_from_markdown
from bridge.lark_im import build_delivery_card, reply_card_to_message
from bridge.lark_slides import create_slides_from_markdown
from bridge.lark_whiteboard import ensure_whiteboard_target, update_whiteboard_from_mermaid
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


def publish_task_artifacts_to_feishu(
    task_dir: Path,
    runner: Runner | None = None,
) -> dict[str, Any]:
    artifacts = read_artifacts(task_dir)
    command_runner = _adapt_runner(runner)
    items = artifact_items(artifacts)
    published: dict[str, dict[str, Any]] = {}

    document_item = _first_item(items, "document")
    document_remote = _feishu_remote(document_item)
    document_path = _local_artifact_path(task_dir, document_item)
    if document_item is not None and document_remote is not None:
        published["document"] = upsert_item(
            artifacts,
            str(document_item.get("id") or document_item.get("kind") or "document"),
            {**document_item, "remote": document_remote},
        )
    elif document_item is not None and document_path is not None:
        doc_result = create_doc_from_markdown(
            document_path,
            title=_artifact_title(artifacts, document_item, "方案"),
            runner=command_runner,
        )
        document = doc_result["response"]["data"]["document"]
        published["document"] = upsert_item(
            artifacts,
            str(document_item.get("id") or document_item.get("kind") or "document"),
            {
                **document_item,
                "remote": {
                    "provider": "feishu",
                    "document_id": document["document_id"],
                    "url": document["url"],
                    "log_id": doc_result["response"].get("data", {}).get("log_id"),
                },
            },
        )

    slides_item = _first_item(items, "slides", "presentation")
    slides_remote = _feishu_remote(slides_item)
    slides_path = _local_artifact_path(task_dir, slides_item)
    if slides_item is not None and slides_remote is not None:
        published["slides"] = upsert_item(
            artifacts,
            str(slides_item.get("id") or slides_item.get("kind") or "slides"),
            {**slides_item, "remote": slides_remote},
        )
    elif slides_item is not None and slides_path is not None:
        slides_result = create_slides_from_markdown(
            slides_path,
            title=_artifact_title(artifacts, slides_item, "Deck"),
            runner=command_runner,
        )
        slides = slides_result["response"]["data"]
        published["slides"] = upsert_item(
            artifacts,
            str(slides_item.get("id") or slides_item.get("kind") or "slides"),
            {
                **slides_item,
                "remote": {
                    "provider": "feishu",
                    "xml_presentation_id": slides["xml_presentation_id"],
                    "url": slides["url"],
                    "slides_added": slides.get("slides_added"),
                },
            },
        )

    whiteboard_item = _first_item(items, "whiteboard", "diagram", "mermaid")
    whiteboard_path = _local_artifact_path(task_dir, whiteboard_item)
    whiteboard_remote = _feishu_remote(whiteboard_item)
    whiteboard_target = _whiteboard_target_item(whiteboard_item, whiteboard_remote, published.get("document"))
    if whiteboard_item is not None and whiteboard_remote is not None and whiteboard_path is None:
        whiteboard_url = _whiteboard_target_url({"remote": whiteboard_remote}, published.get("document"))
        published["whiteboard"] = upsert_item(
            artifacts,
            str(whiteboard_item.get("id") or whiteboard_item.get("kind") or "whiteboard"),
            {
                **whiteboard_item,
                "remote": {
                    **whiteboard_remote,
                    **({"url": whiteboard_url} if whiteboard_url and not whiteboard_remote.get("url") else {}),
                },
            },
        )
    elif whiteboard_item is not None and whiteboard_path is not None and whiteboard_target is not None:
        target = ensure_whiteboard_target(whiteboard_target, runner=runner)
        whiteboard_update = update_whiteboard_from_mermaid(
            str(target["whiteboard_token"]),
            whiteboard_path,
            idempotency_token=f"{artifacts['task_id']}-board",
            runner=runner,
        )
        published["whiteboard"] = upsert_item(
            artifacts,
            str(whiteboard_item.get("id") or whiteboard_item.get("kind") or "whiteboard"),
            {
                **whiteboard_item,
                "remote": {
                    "provider": "feishu",
                    "document_id": target.get("document_id"),
                    "url": _whiteboard_target_url(whiteboard_target, published.get("document")),
                    "block_id": target.get("block_id"),
                    "whiteboard_token": target["whiteboard_token"],
                    "created_node_id": whiteboard_update["created_node_id"],
                },
            },
        )

    if not published:
        raise ValueError("no publishable artifact items found")

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


def _local_artifact_path(task_dir: Path, item: dict[str, Any] | None) -> Path | None:
    if item is None:
        return None
    return resolve_local_path(item, task_dir=task_dir)


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


def _whiteboard_target_item(
    whiteboard_item: dict[str, Any] | None,
    whiteboard_remote: dict[str, Any] | None,
    document_item: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if whiteboard_item is None:
        return None
    if whiteboard_remote is not None:
        return {"remote": whiteboard_remote}
    document_remote = _feishu_remote(document_item)
    if document_remote is not None:
        return {"remote": document_remote}
    return None


def _append_publish_summary(summary: str) -> str:
    suffix = "Published to Feishu via lark-cli."
    if suffix in summary:
        return summary
    if not summary:
        return suffix
    return f"{summary} {suffix}"


def _whiteboard_target_url(target_item: dict[str, Any], document_item: dict[str, Any] | None) -> str | None:
    target_remote = _feishu_remote(target_item)
    if target_remote and target_remote.get("url"):
        return str(target_remote["url"])
    document_remote = _feishu_remote(document_item)
    if document_remote and document_remote.get("url"):
        return str(document_remote["url"])
    return None
