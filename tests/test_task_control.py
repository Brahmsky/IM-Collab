from __future__ import annotations

import json
from pathlib import Path

from bridge.task_control import append_control_command, read_control_commands


def test_append_control_command_writes_jsonl_record(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "task-123"

    command = append_control_command(
        task_dir,
        "append_instruction",
        {"text": "补充移动端同步说明"},
        operator="feishu",
    )

    assert command["type"] == "append_instruction"
    assert command["operator"] == "feishu"
    assert command["payload"] == {"text": "补充移动端同步说明"}

    records = read_control_commands(task_dir)
    assert records == [command]
    line = (task_dir / "control.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(line) == command
