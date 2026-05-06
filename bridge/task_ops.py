from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from bridge.golembot_office_loop import run_golembot_office_task

OfficeRunner = Callable[..., dict[str, Any]]


def ack_task(task_dir: Path, operator: str = "operator", note: str = "") -> dict[str, Any]:
    ack = {
        "acknowledged_at": datetime.now(UTC).isoformat(),
        "operator": operator,
        "note": note,
    }
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "ack.json").write_text(json.dumps(ack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ack


def parse_golembot_request(task_dir: Path) -> dict[str, str]:
    request = (task_dir / "request.md").read_text(encoding="utf-8")
    data = {
        "session_key": _field(request, "session_key"),
        "chat_id": _field(request, "chat_id"),
        "sender_id": _field(request, "sender_id"),
        "message": _section(request, "## User Message"),
    }
    missing = [key for key, value in data.items() if not value]
    if missing:
        raise ValueError(f"request.md missing retry fields: {', '.join(missing)}")
    return data


def retry_golembot_task(
    task_dir: Path,
    generator: str = "app-server",
    publish: bool = False,
    runner: OfficeRunner = run_golembot_office_task,
    codex_backend: Any | None = None,
) -> dict[str, Any]:
    request = parse_golembot_request(task_dir)
    return runner(
        message=request["message"],
        session_key=request["session_key"],
        chat_id=request["chat_id"],
        sender_id=request["sender_id"],
        tasks_root=task_dir.parent,
        task_id=task_dir.name,
        generator=generator,
        publish=publish,
        codex_backend=codex_backend,
    )


def _field(markdown: str, name: str) -> str:
    prefix = f"{name}:"
    for line in markdown.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()
