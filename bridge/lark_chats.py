from __future__ import annotations

from typing import Any, Callable

from bridge.lark_docs import _extract_json
from bridge.lark_im import _subprocess_runner

Runner = Callable[[list[str]], str]


def build_get_chat_args(chat_id: str, identity: str = "user") -> list[str]:
    if identity not in {"user", "bot", "auto"}:
        raise ValueError("identity must be 'user', 'bot', or 'auto'")
    return [
        "lark-cli",
        "im",
        "chats",
        "get",
        "--as",
        identity,
        "--params",
        f'{{"chat_id":"{chat_id}"}}',
    ]


def get_chat_name(chat_id: str, identity: str = "user", runner: Runner | None = None) -> str:
    args = build_get_chat_args(chat_id, identity=identity)
    output = runner(args) if runner else _subprocess_runner(args)
    data = _extract_json(output)
    payload = data.get("data") if isinstance(data.get("data"), dict) else {}
    return str(payload.get("name") or "").strip()
