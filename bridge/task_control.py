from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CONTROL_LOG = "control.jsonl"


def append_control_command(
    task_dir: Path,
    command_type: str,
    payload: dict[str, Any],
    operator: str = "bridge",
) -> dict[str, Any]:
    command = {
        "timestamp": datetime.now(UTC).isoformat(),
        "type": command_type,
        "operator": operator,
        "payload": payload,
    }
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / CONTROL_LOG).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(command, ensure_ascii=False) + "\n")
    return command


def read_control_commands(task_dir: Path) -> list[dict[str, Any]]:
    control_path = task_dir / CONTROL_LOG
    try:
        lines = control_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in lines if line.strip()]
