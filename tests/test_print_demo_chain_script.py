from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_print_demo_chain_script_outputs_commands() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "print_demo_chain.py"

    completed = subprocess.run(
        [sys.executable, script.as_posix(), "--no-publish", "--no-execute"],
        check=True,
        text=True,
        capture_output=True,
    )

    result = json.loads(completed.stdout)
    assert "commands" in result
    assert result["commands"]["consumer"][0:2] == [".venv/bin/python", "scripts/run_event_consumer.py"]
    assert "--publish" not in result["commands"]["consumer"]
    assert "FEISHU_APP_ID" in result["required_env"]
