from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Callable

from bridge.artifacts import artifact_items, remote_label, remote_url
from bridge.lark_docs import _extract_json

Runner = Callable[[list[str]], str]


def build_reply_args(
    message_id: str,
    markdown: str,
    idempotency_key: str,
    dry_run: bool = False,
) -> list[str]:
    args = [
        "lark-cli",
        "im",
        "+messages-reply",
        "--as",
        "bot",
        "--message-id",
        message_id,
        "--markdown",
        markdown,
        "--idempotency-key",
        _safe_idempotency_key(idempotency_key),
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def build_reply_card_args(
    message_id: str,
    card_path: Path,
    idempotency_key: str,
    dry_run: bool = False,
) -> list[str]:
    card_content = card_path.read_text(encoding="utf-8")
    args = [
        "lark-cli",
        "im",
        "+messages-reply",
        "--as",
        "bot",
        "--message-id",
        message_id,
        "--msg-type",
        "interactive",
        "--content",
        card_content,
        "--idempotency-key",
        _safe_idempotency_key(idempotency_key),
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def reply_to_message(
    message_id: str,
    markdown: str,
    idempotency_key: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    args = build_reply_args(message_id, markdown, idempotency_key, dry_run=dry_run)
    output = runner(args) if runner else _subprocess_runner(args)
    return {"ok": True, "dry_run": dry_run, "response": _extract_json(output), "raw": output}


def reply_card_to_message(
    message_id: str,
    card_path: Path,
    idempotency_key: str,
    dry_run: bool = False,
    runner: Runner | None = None,
) -> dict[str, Any]:
    args = build_reply_card_args(message_id, card_path, idempotency_key, dry_run=dry_run)
    output = runner(args) if runner else _subprocess_runner(args)
    return {"ok": True, "dry_run": dry_run, "response": _extract_json(output), "raw": output}


def build_list_messages_args(chat_id: str, page_size: int = 20, identity: str = "user") -> list[str]:
    if identity not in {"user", "bot"}:
        raise ValueError("identity must be 'user' or 'bot'")
    return [
        "lark-cli",
        "im",
        "+chat-messages-list",
        "--as",
        identity,
        "--chat-id",
        chat_id,
        "--page-size",
        str(page_size),
        "--sort",
        "desc",
    ]


def list_chat_messages(
    chat_id: str,
    page_size: int = 20,
    identity: str = "user",
    runner: Runner | None = None,
) -> list[dict[str, Any]]:
    args = build_list_messages_args(chat_id, page_size=page_size, identity=identity)
    output = runner(args) if runner else _subprocess_runner(args)
    response = _extract_json(output)
    messages = response.get("data", {}).get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("lark-cli message list response did not contain data.messages")
    return [message for message in reversed(messages) if isinstance(message, dict)]


def build_delivery_markdown(artifacts: dict[str, Any]) -> str:
    lines = ["你好，我是你的办公协作助手。相关材料已经整理好：", ""]
    items = artifact_items(artifacts)
    if not items:
        lines.append(str(artifacts.get("summary") or "任务已完成。"))
    for item in items:
        label = str(item.get("title") or item.get("kind") or item.get("id") or "材料")
        value = remote_label(item) or "已生成"
        lines.extend([label, value, ""])
    lines.append("还需要我根据群里的消息补充背景、调整结构，或者继续整理成会议纪要/待办吗？")
    return "\n".join(lines).rstrip() + "\n"


def build_delivery_card(artifacts: dict[str, Any]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = [{"tag": "markdown", "content": "材料已经生成。可以直接打开查看，也可以继续在群里补充修改要求。"}]
    for index, item in enumerate(artifact_items(artifacts)):
        label = str(item.get("title") or item.get("kind") or item.get("id") or "材料")
        url = remote_url(item)
        if url:
            elements.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": f"打开{label}"},
                    "type": "primary" if index == 0 else "default",
                    "url": url,
                }
            )
        else:
            value = remote_label(item)
            if value:
                elements.append({"tag": "markdown", "content": f"{label}: {value}"})
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"tag": "plain_text", "content": "材料已生成"},
        },
        "elements": elements,
    }


def _subprocess_runner(args: list[str]) -> str:
    completed = subprocess.run(args, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "lark-cli IM command failed\n"
            f"command: {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout


def _safe_idempotency_key(idempotency_key: str) -> str:
    if len(idempotency_key) <= 50:
        return idempotency_key
    digest = hashlib.sha1(idempotency_key.encode("utf-8")).hexdigest()
    return f"imc-{digest}"
