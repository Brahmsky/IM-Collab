# Agent Pilot Control Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local Agent-Pilot control console around the existing `tasks/` and `events/` protocol.

**Architecture:** Add a GUI-independent task index module first, then expose it through a small console entry point. Textual is the preferred UI wheel, but the first pass must still provide a plain text fallback so the project remains runnable before GUI dependencies are installed.

**Tech Stack:** Python, pytest, existing task protocol JSON files, optional Textual/Rich dependency.

---

## File Structure

- Create `bridge/task_index.py`: scans task directories and event directories into display models.
- Create `tests/test_task_index.py`: unit tests for task sorting, artifact extraction, failed status extraction, and event summary.
- Create `scripts/task_console.py`: operator entry point; plain summary first, optional Textual app later.
- Create `tests/test_task_console_script.py`: script smoke test with fixture directories.
- Modify `requirements-dev.txt`: add `textual` after the fallback script is tested, if we implement the Textual view in this plan.
- Modify `README.md`: document the control console and its current read-only boundary.

### Task 1: Task Index Data Layer

**Files:**
- Create: `bridge/task_index.py`
- Create: `tests/test_task_index.py`

- [ ] **Step 1: Write failing tests for task summaries**

Create `tests/test_task_index.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

from bridge.task_index import build_task_index, summarize_events


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_task_index_sorts_by_updated_at_and_extracts_remote_links(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "old" / "status.json",
        {"task_id": "old", "state": "completed", "created_at": "2026-04-28T01:00:00+00:00", "updated_at": "2026-04-28T01:00:00+00:00", "error": None},
    )
    write_json(
        tasks_root / "old" / "artifacts.json",
        {
            "task_id": "old",
            "document": {"remote": {"url": "https://example/doc-old"}},
            "slides": {"remote": {"url": "https://example/slides-old"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb-old"}},
            "summary": "old summary",
            "next_steps": [],
        },
    )
    write_json(
        tasks_root / "new" / "status.json",
        {"task_id": "new", "state": "completed", "created_at": "2026-04-28T02:00:00+00:00", "updated_at": "2026-04-28T02:00:00+00:00", "error": None},
    )
    write_json(
        tasks_root / "new" / "artifacts.json",
        {
            "task_id": "new",
            "document": {"remote": {"url": "https://example/doc-new"}},
            "slides": {"remote": {"url": "https://example/slides-new"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb-new"}},
            "summary": "new summary",
            "next_steps": [],
        },
    )

    index = build_task_index(tasks_root)

    assert [task.task_id for task in index] == ["new", "old"]
    assert index[0].document_url == "https://example/doc-new"
    assert index[0].slides_url == "https://example/slides-new"
    assert index[0].whiteboard_token == "wb-new"
    assert index[0].summary == "new summary"


def test_build_task_index_includes_failed_task_error(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "broken" / "status.json",
        {"task_id": "broken", "state": "failed", "created_at": "2026-04-28T01:00:00+00:00", "updated_at": "2026-04-28T01:05:00+00:00", "error": "Feishu permission denied"},
    )

    index = build_task_index(tasks_root)

    assert len(index) == 1
    assert index[0].state == "failed"
    assert index[0].error == "Feishu permission denied"
    assert index[0].document_url == ""


def test_summarize_events_counts_latest_event_files(tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    (event_dir / "im.message.receive_v1_a.json").parent.mkdir(parents=True)
    (event_dir / "im.message.receive_v1_a.json").write_text("{}", encoding="utf-8")
    (event_dir / "im.message.receive_v1_b.json").write_text("{}", encoding="utf-8")

    summary = summarize_events(event_dir, limit=1)

    assert summary.total == 2
    assert summary.latest_files == ["im.message.receive_v1_b.json"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_index.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'bridge.task_index'`.

- [ ] **Step 3: Implement minimal task index**

Create `bridge/task_index.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskSummary:
    task_id: str
    state: str
    created_at: str
    updated_at: str
    error: str
    summary: str
    document_url: str
    slides_url: str
    whiteboard_token: str
    path: Path


@dataclass(frozen=True)
class EventSummary:
    total: int
    latest_files: list[str]


def build_task_index(tasks_root: Path = Path("tasks")) -> list[TaskSummary]:
    if not tasks_root.exists():
        return []
    summaries = [_read_task_summary(path) for path in tasks_root.iterdir() if path.is_dir()]
    return sorted((summary for summary in summaries if summary is not None), key=lambda item: item.updated_at, reverse=True)


def summarize_events(event_dir: Path = Path("events"), limit: int = 5) -> EventSummary:
    if not event_dir.exists():
        return EventSummary(total=0, latest_files=[])
    files = sorted((path for path in event_dir.rglob("*.json") if path.is_file()), key=lambda path: path.name)
    return EventSummary(total=len(files), latest_files=[path.name for path in files[-limit:]][::-1])


def _read_task_summary(task_dir: Path) -> TaskSummary | None:
    status_path = task_dir / "status.json"
    if not status_path.exists():
        return None
    status = _read_json(status_path)
    artifacts = _read_json(task_dir / "artifacts.json") if (task_dir / "artifacts.json").exists() else {}
    return TaskSummary(
        task_id=str(status.get("task_id") or task_dir.name),
        state=str(status.get("state") or "unknown"),
        created_at=str(status.get("created_at") or ""),
        updated_at=str(status.get("updated_at") or ""),
        error=str(status.get("error") or ""),
        summary=str(artifacts.get("summary") or ""),
        document_url=_remote_value(artifacts, "document", "url"),
        slides_url=_remote_value(artifacts, "slides", "url"),
        whiteboard_token=_remote_value(artifacts, "whiteboard", "whiteboard_token"),
        path=task_dir,
    )


def _remote_value(artifacts: dict[str, Any], key: str, field: str) -> str:
    value = artifacts.get(key, {})
    if not isinstance(value, dict):
        return ""
    remote = value.get("remote", {})
    if not isinstance(remote, dict):
        return ""
    return str(remote.get(field) or "")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data
```

- [ ] **Step 4: Run task index tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_index.py -q
```

Expected: all tests pass.

### Task 2: Plain Console Entry Point

**Files:**
- Create: `scripts/task_console.py`
- Create: `tests/test_task_console_script.py`

- [ ] **Step 1: Write failing script smoke test**

Create `tests/test_task_console_script.py`:

```python
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
        {"task_id": "im-1", "state": "completed", "created_at": "2026-04-28T01:00:00+00:00", "updated_at": "2026-04-28T01:00:00+00:00", "error": None},
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_console_script.py -q
```

Expected: fail because `scripts/task_console.py` does not exist.

- [ ] **Step 3: Implement plain console script**

Create `scripts/task_console.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.task_index import build_task_index, summarize_events


def render_plain(tasks_root: Path, event_dir: Path, limit: int) -> str:
    tasks = build_task_index(tasks_root)[:limit]
    events = summarize_events(event_dir)
    lines = ["IM-Collab Agent Console", f"events: {events.total}"]
    if events.latest_files:
        lines.append("latest events: " + ", ".join(events.latest_files))
    if not tasks:
        lines.append("tasks: none")
        return "\n".join(lines) + "\n"
    lines.append("tasks:")
    for task in tasks:
        lines.append(f"- {task.task_id} {task.state} updated={task.updated_at}")
        if task.error:
            lines.append(f"  error: {task.error}")
        if task.summary:
            lines.append(f"  summary: {task.summary}")
        if task.document_url:
            lines.append(f"  document: {task.document_url}")
        if task.slides_url:
            lines.append(f"  slides: {task.slides_url}")
        if task.whiteboard_token:
            lines.append(f"  whiteboard: {task.whiteboard_token}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show IM-Collab Agent-Pilot task console.")
    parser.add_argument("--tasks-root", type=Path, default=Path("tasks"))
    parser.add_argument("--event-dir", type=Path, default=Path("events"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--plain", action="store_true", help="Render a plain text snapshot and exit.")
    args = parser.parse_args()

    print(render_plain(args.tasks_root, args.event_dir, args.limit), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run console script test**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_console_script.py -q
```

Expected: pass.

### Task 3: README Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add console documentation**

Append a section after the deployment section:

```markdown
## 8. Agent 控制台

当前 GUI 定位是 Agent-Pilot 控制台，不替代飞书 IM、文档、演示稿或白板。

先用纯文本快照查看任务：

```bash
rtk .venv/bin/python scripts/task_console.py --plain
```

它读取：

- `tasks/<task_id>/status.json`
- `tasks/<task_id>/artifacts.json`
- `events/**/*.json`

当前控制台是只读的：用于查看任务状态、错误、产物链接和事件数量。后续需要通过 `control.jsonl` 这类显式控制协议再加入取消、重试、追加指令和人工确认。
```

- [ ] **Step 2: Run tests**

Run:

```bash
rtk .venv/bin/python -m pytest -q
```

Expected: all tests pass.

### Task 4: Optional Textual View Spike

**Files:**
- Modify: `requirements-dev.txt`
- Modify: `scripts/task_console.py`
- Create or modify: `tests/test_task_console_script.py`

- [ ] **Step 1: Decide whether to install Textual now**

If the plain console is enough for the next demo, stop before this task.

If a real TUI is needed now, add:

```text
textual
```

to `requirements-dev.txt`, install it, and keep `--plain` as the testable fallback.

- [ ] **Step 2: Add Textual only as optional runtime**

The script must still run without Textual when `--plain` is used. Import Textual inside a function so tests and basic usage do not require GUI dependencies.

Expected behavior:

```bash
rtk .venv/bin/python scripts/task_console.py --plain
```

still works with no Textual installed.

## Self-Review

- Spec coverage: this plan implements the read-mostly console and GUI-independent task data layer from the design spec.
- Placeholder scan: no task contains TBD/TODO or unspecified code.
- Type consistency: `TaskSummary`, `EventSummary`, `build_task_index`, `summarize_events`, and `render_plain` names are consistent across tests and implementation.
- Known deferred scope: write controls and full Textual TUI are intentionally deferred until the read-only task console is verified.

