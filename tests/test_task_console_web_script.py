from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_task_console_web_script_prints_startup_url() -> None:
    repo = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console_web.py"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--print-url",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert completed.stdout.startswith("http://127.0.0.1:")
