from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_task_console_prints_task_and_artifact_links(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    tasks_root = tmp_path / "tasks"
    events_root = tmp_path / "events"
    write_json(
        tasks_root / "im-1" / "status.json",
        {
            "task_id": "im-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "im-1" / "artifacts.json",
        {
            "task_id": "im-1",
            "document": {"remote": {"url": "https://example/doc"}},
            "slides": {"remote": {"url": "https://example/slides"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb-token"}},
            "summary": "demo summary",
            "next_steps": [],
        },
    )
    write_json(events_root / "im.message.receive_v1_demo.json", {"message_id": "om_demo"})

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console.py"),
            "--tasks-root",
            str(tasks_root),
            "--event-dir",
            str(events_root),
            "--plain",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "IM-Collab Agent Console" in completed.stdout
    assert "im-1 completed" in completed.stdout
    assert "https://example/doc" in completed.stdout
    assert "https://example/slides" in completed.stdout
    assert "events: 1" in completed.stdout


def test_task_console_filters_state_and_truncates_long_error(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    tasks_root = tmp_path / "tasks"
    long_error = "first line\n" + ("very noisy stderr " * 20)
    write_json(
        tasks_root / "failed-1" / "status.json",
        {
            "task_id": "failed-1",
            "state": "failed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": long_error,
        },
    )
    write_json(
        tasks_root / "done-1" / "status.json",
        {
            "task_id": "done-1",
            "state": "completed",
            "created_at": "2026-04-28T02:00:00+00:00",
            "updated_at": "2026-04-28T02:00:00+00:00",
            "error": None,
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console.py"),
            "--tasks-root",
            str(tasks_root),
            "--event-dir",
            str(tmp_path / "events"),
            "--plain",
            "--state",
            "failed",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "failed-1 failed" in completed.stdout
    assert "done-1" not in completed.stdout
    assert "first line" in completed.stdout
    assert len(completed.stdout.split("error: ", 1)[1].splitlines()[0]) <= 123
    assert "..." in completed.stdout


def test_task_console_prints_active_turn_and_control_queue(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "active-1" / "status.json",
        {
            "task_id": "active-1",
            "state": "running",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    (tasks_root / "active-1" / "control.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "append_instruction", "payload": {"text": "补充 A"}}, ensure_ascii=False),
                json.dumps({"type": "interrupt", "payload": {}}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_group": {
                "session_key": "feishu:oc_group",
                "active_task_id": "active-1",
                "codex_thread_id": "thread_123",
                "active_turn_id": "turn_456",
            }
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console.py"),
            "--tasks-root",
            str(tasks_root),
            "--event-dir",
            str(tmp_path / "events"),
            "--plain",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "session: feishu:oc_group" in completed.stdout
    assert "thread: thread_123" in completed.stdout
    assert "turn: turn_456" in completed.stdout
    assert "control: 2 queued" in completed.stdout


def test_task_console_append_and_interrupt_queue_control_commands(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    tasks_root = tmp_path / "tasks"

    append_result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console.py"),
            "--tasks-root",
            str(tasks_root),
            "append",
            "active-1",
            "--text",
            "补充移动端入口",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    interrupt_result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console.py"),
            "--tasks-root",
            str(tasks_root),
            "interrupt",
            "active-1",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "append_instruction queued for active-1" in append_result.stdout
    assert "interrupt queued for active-1" in interrupt_result.stdout
    commands = [
        json.loads(line)
        for line in (tasks_root / "active-1" / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert commands[0]["type"] == "append_instruction"
    assert commands[0]["payload"]["text"] == "补充移动端入口"
    assert commands[1]["type"] == "interrupt"
