from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.task_control import append_control_command
from bridge.task_index import TaskSummary, build_task_index, summarize_events


def render_plain(tasks_root: Path, event_dir: Path, limit: int, state: str | None = None) -> str:
    tasks = _filter_tasks(build_task_index(tasks_root), state)[:limit]
    events = summarize_events(event_dir)
    state_label = state if state else "all"
    lines = ["IM-Collab Agent Console", f"events: {events.total}", f"state: {state_label}"]
    if events.latest_files:
        lines.append("latest events:")
        lines.extend(f"  - {name}" for name in events.latest_files)
    if not tasks:
        lines.append("tasks: none")
        return "\n".join(lines) + "\n"

    lines.append("tasks:")
    for task in tasks:
        lines.append(f"- {task.task_id} {task.state} updated={task.updated_at}")
        if task.session_key:
            lines.append(f"  session: {task.session_key}")
        if task.codex_thread_id:
            lines.append(f"  thread: {task.codex_thread_id}")
        if task.active_turn_id:
            lines.append(f"  turn: {task.active_turn_id}")
        if task.control_count:
            lines.append(f"  control: {task.control_count} queued")
        if task.error:
            lines.append(f"  error: {_clip(task.error)}")
        if task.summary:
            lines.append(f"  summary: {_clip(task.summary)}")
        if task.document_url:
            lines.append(f"  document: {task.document_url}")
        if task.slides_url:
            lines.append(f"  slides: {task.slides_url}")
        if task.whiteboard_token:
            lines.append(f"  whiteboard: {task.whiteboard_token}")
    return "\n".join(lines) + "\n"


def _filter_tasks(tasks: list[TaskSummary], state: str | None) -> list[TaskSummary]:
    if not state:
        return tasks
    return [task for task in tasks if task.state == state]


def _clip(value: str, max_chars: int = 120) -> str:
    one_line = " ".join(value.split())
    if len(one_line) <= max_chars:
        return one_line
    return one_line[: max_chars - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description="Show IM-Collab Agent-Pilot task console.")
    parser.add_argument("--tasks-root", type=Path, default=Path("tasks"))
    parser.add_argument("--event-dir", type=Path, default=Path("events"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--state", choices=("queued", "running", "waiting_for_user", "completed", "failed"))
    parser.add_argument("--plain", action="store_true", help="Render a plain text snapshot and exit.")
    subparsers = parser.add_subparsers(dest="command")
    append_parser = subparsers.add_parser("append", help="Append an instruction to a running task.")
    append_parser.add_argument("task_id")
    append_parser.add_argument("--text", required=True)

    interrupt_parser = subparsers.add_parser("interrupt", help="Interrupt a running task.")
    interrupt_parser.add_argument("task_id")
    args = parser.parse_args()

    if args.command == "append":
        append_control_command(
            args.tasks_root / args.task_id,
            "append_instruction",
            {"text": args.text},
            operator="operator",
        )
        print(f"append_instruction queued for {args.task_id}")
        return 0
    if args.command == "interrupt":
        append_control_command(args.tasks_root / args.task_id, "interrupt", {}, operator="operator")
        print(f"interrupt queued for {args.task_id}")
        return 0

    print(render_plain(args.tasks_root, args.event_dir, args.limit, state=args.state), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
