"""Seed a minimal local task so the web cockpit has data to show (no Feishu required)."""

from __future__ import annotations

import json
from pathlib import Path

from bridge.task_protocol import create_task, write_artifacts, write_status

DEMO_TASK_ID = "demo-local-smoke"


def ensure_local_smoke_demo_task(tasks_root: Path, project_root: Path) -> bool:
    """Create ``demo-local-smoke`` if missing. Returns True if a new task directory was created."""
    tasks_root.mkdir(parents=True, exist_ok=True)
    task_dir = tasks_root / DEMO_TASK_ID
    if (task_dir / "status.json").exists():
        return False

    req_path = project_root / "examples" / "demo_request.md"
    request = (
        req_path.read_text(encoding="utf-8")
        if req_path.is_file()
        else "# Demo\n\n用于本地 Web 控制台预览的占位请求。\n"
    )
    create_task(tasks_root, DEMO_TASK_ID, request)
    doc_path = task_dir / "document.md"
    doc_path.write_text("# 示例交付\n\n控制台预览用 Markdown。\n", encoding="utf-8")
    write_artifacts(
        task_dir,
        {
            "task_id": DEMO_TASK_ID,
            "summary": "本地示例任务：用于 cockpit 界面预览（非飞书真实链路）。",
            "next_steps": ["运行飞书 consumer 或 run_golembot_office_task 体验完整链路。"],
            "items": [
                {
                    "id": "document",
                    "kind": "document",
                    "type": "markdown",
                    "title": "示例文档",
                    "path": str(doc_path),
                },
            ],
        },
    )
    write_status(task_dir, "completed", None)

    bindings_path = tasks_root / "task-bindings.json"
    if not bindings_path.exists():
        bindings_path.write_text(
            json.dumps(
                {
                    "feishu:答辩演示群": {
                        "session_key": "feishu:答辩演示群",
                        "active_task_id": DEMO_TASK_ID,
                        "codex_thread_id": "thread_console_demo",
                        "active_turn_id": "turn_console_demo",
                    }
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return True


def resolve_repo_relative_path(path: Path, project_root: Path) -> Path:
    """Resolve CLI paths relative to the repo root when not absolute (fixes cwd=scripts/)."""
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (project_root / expanded).resolve()
