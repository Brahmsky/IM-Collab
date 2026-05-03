from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_golembot_office_task_script_outputs_reply_markdown(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_golembot_office_task.py"

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
            "local",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert result["task_id"] == "gb-cli-task"
    assert result["reply_markdown"].startswith("你好，我是你的办公协作助手。")
    assert "相关材料已经整理好" in result["reply_markdown"]
    assert (tmp_path / "gb-cli-task" / "artifacts.json").exists()


def test_run_golembot_office_task_script_accepts_app_server_generator() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_golembot_office_task.py"

    completed = subprocess.run(
        [sys.executable, script.as_posix(), "--help"],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "app-server" in completed.stdout
