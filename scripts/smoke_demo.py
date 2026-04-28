from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.local_codex_smoke import run_local_smoke
from bridge.task_protocol import create_task


def main() -> int:
    task_id = "demo-local-smoke"
    task_root = PROJECT_ROOT / "tasks"
    task_dir = task_root / task_id
    request = (PROJECT_ROOT / "examples" / "demo_request.md").read_text(encoding="utf-8")

    if task_dir.exists():
        shutil.rmtree(task_dir)

    task_dir = create_task(task_root, task_id, request)
    artifacts = run_local_smoke(task_dir)
    print(json.dumps({"task_dir": task_dir.as_posix(), "artifacts": artifacts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
