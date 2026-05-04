from __future__ import annotations

import json
from pathlib import Path

from bridge.console_demo_seed import (
    DEMO_TASK_ID,
    ensure_local_smoke_demo_task,
    resolve_repo_relative_path,
)


def test_resolve_repo_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    assert resolve_repo_relative_path(Path("tasks"), root) == root / "tasks"
    assert resolve_repo_relative_path(root / "abs" / "tasks", root) == root / "abs" / "tasks"


def test_ensure_local_smoke_demo_task_creates_once(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    tr = tmp_path / "tasks"
    assert ensure_local_smoke_demo_task(tr, root) is True
    assert (tr / DEMO_TASK_ID / "status.json").is_file()
    assert ensure_local_smoke_demo_task(tr, root) is False
    st = json.loads((tr / DEMO_TASK_ID / "status.json").read_text(encoding="utf-8"))
    assert st.get("state") == "completed"
