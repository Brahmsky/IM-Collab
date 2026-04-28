from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.task_control import append_control_command


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue a control command for an IM-Collab task.")
    parser.add_argument("--tasks-root", type=Path, default=Path("tasks"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser("append", help="Append an instruction to an active task.")
    append_parser.add_argument("task_id")
    append_parser.add_argument("--text", required=True)

    interrupt_parser = subparsers.add_parser("interrupt", help="Interrupt an active task.")
    interrupt_parser.add_argument("task_id")

    args = parser.parse_args()
    task_dir = args.tasks_root / args.task_id
    if args.command == "append":
        append_control_command(
            task_dir,
            "append_instruction",
            {"text": args.text},
            operator="operator",
        )
        print(f"append_instruction queued for {args.task_id}")
        return 0
    if args.command == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        print(f"interrupt queued for {args.task_id}")
        return 0
    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
