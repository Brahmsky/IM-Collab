from __future__ import annotations

import hashlib
import subprocess
from typing import Any, Callable

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
    document = _remote_value(artifacts, "document", "url")
    slides = _remote_value(artifacts, "slides", "url")
    whiteboard = _remote_value(artifacts, "whiteboard", "whiteboard_token")
    return f"""你好，我是你的办公协作助手。文档生成完成，相关材料已经整理好：

**文档**：{document}
**演示稿**：{slides}
**白板**：{whiteboard}

还需要我根据群里的消息补充背景、调整 PPT 结构，或者继续把这份内容整理成会议纪要/待办吗？
"""


def _remote_value(artifacts: dict[str, Any], key: str, field: str) -> str:
    value = artifacts.get(key, {})
    if isinstance(value, dict):
        remote = value.get("remote", {})
        if isinstance(remote, dict) and remote.get(field):
            return str(remote[field])
        if value.get("path"):
            return str(value["path"])
    return "未生成"


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
