from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from bridge.lark_docs import create_doc_from_markdown
from bridge.lark_im import build_delivery_markdown, reply_to_message
from bridge.lark_slides import create_slides_from_markdown
from bridge.lark_whiteboard import append_whiteboard_to_doc, update_whiteboard_from_mermaid
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

    reply = reply_to_message(
        message_id,
        build_delivery_markdown(artifacts),
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

    doc_result = create_doc_from_markdown(
        Path(artifacts["document"]["path"]),
        title=f"IM-Collab {artifacts['task_id']} 方案",
        runner=command_runner,
    )
    document = doc_result["response"]["data"]["document"]

    slides_result = create_slides_from_markdown(
        Path(artifacts["slides"]["path"]),
        title=f"IM-Collab {artifacts['task_id']} Deck",
        runner=command_runner,
    )
    slides = slides_result["response"]["data"]

    whiteboard_block = append_whiteboard_to_doc(document["document_id"], runner=runner)
    whiteboard_update = update_whiteboard_from_mermaid(
        whiteboard_block["whiteboard_token"],
        Path(artifacts["whiteboard"]["path"]),
        idempotency_token=f"{artifacts['task_id']}-board",
        runner=runner,
    )

    artifacts["document"]["remote"] = {
        "provider": "feishu",
        "document_id": document["document_id"],
        "url": document["url"],
        "log_id": doc_result["response"].get("data", {}).get("log_id"),
    }
    artifacts["slides"]["remote"] = {
        "provider": "feishu",
        "xml_presentation_id": slides["xml_presentation_id"],
        "url": slides["url"],
        "slides_added": slides.get("slides_added"),
    }
    artifacts["whiteboard"]["remote"] = {
        "provider": "feishu",
        "document_id": document["document_id"],
        "whiteboard_token": whiteboard_block["whiteboard_token"],
        "block_id": whiteboard_block["block_id"],
        "created_node_id": whiteboard_update["created_node_id"],
    }
    artifacts["summary"] = (
        f"{artifacts['summary']} Published to Feishu document, slides, and whiteboard via lark-cli."
    )
    write_artifacts(task_dir, artifacts)

    return {"task_id": artifacts["task_id"], "artifacts": artifacts}


def _adapt_runner(runner: Runner | None):
    if runner is None:
        return None

    def run_without_input(args: list[str]) -> str:
        return runner(args, None)

    return run_without_input
