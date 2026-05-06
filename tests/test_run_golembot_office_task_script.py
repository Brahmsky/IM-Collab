from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_golembot_office_task_script_outputs_reply_markdown(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_golembot_office_task.py"

    # app-server generator requires a running Codex instance —
    # the script will fail at the Codex call but should create the task
    # directory and status.json before attempting the Codex run.
    completed = subprocess.run(
        [
            sys.executable,
            script.as_posix(),
            "--message",
            "生成项目方案",
            "--session-key",
            "feishu:oc_123",
            "--chat-id",
            "oc_123",
            "--sender-id",
            "ou_456",
            "--tasks-root",
            tmp_path.as_posix(),
            "--task-id",
            "gb-cli-task",
            "--generator",
            "app-server",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    # Task directory should be created before the Codex call.
    task_dir = tmp_path / "gb-cli-task"
    assert task_dir.exists(), f"task directory should be created before Codex call, stdout={completed.stdout[:200]} stderr={completed.stderr[:200]}"
    assert (task_dir / "request.md").exists()
    assert (task_dir / "status.json").exists()


def test_run_golembot_office_task_script_accepts_app_server_generator() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_golembot_office_task.py"

    completed = subprocess.run(
        [sys.executable, script.as_posix(), "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "app-server" in completed.stdout
