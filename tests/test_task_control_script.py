from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_task_control_script_appends_instruction(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    task_dir = tmp_path / "tasks" / "task-123"

    result = subprocess.run(
        [
            str(repo / ".venv" / "bin" / "python"),
            str(repo / "scripts" / "task_control.py"),
            "--tasks-root",
            str(tmp_path / "tasks"),
            "append",
            "task-123",
            "--text",
            "补充移动端入口",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "append_instruction queued for task-123" in result.stdout
    [command] = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command["type"] == "append_instruction"
    assert command["payload"]["text"] == "补充移动端入口"
    assert command["operator"] == "operator"


def test_task_control_script_queues_interrupt(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    task_dir = tmp_path / "tasks" / "task-123"

    result = subprocess.run(
        [
            str(repo / ".venv" / "bin" / "python"),
            str(repo / "scripts" / "task_control.py"),
            "--tasks-root",
            str(tmp_path / "tasks"),
            "interrupt",
            "task-123",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "interrupt queued for task-123" in result.stdout
    [command] = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command["type"] == "interrupt"
    assert command["payload"] == {}
    assert command["operator"] == "operator"
