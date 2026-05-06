from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.feishu_events import create_task_from_event, parse_im_event
from bridge.feishu_delivery import deliver_task_to_feishu
from bridge.lark_im import reply_to_message
from bridge.local_codex_smoke import run_local_smoke
from bridge.codex_task_runner import run_codex_task
from bridge.task_protocol import read_artifacts, write_status
from bridge.task_binding import bind_active_task, build_golembot_session_key, clear_active_task


def process_event_file(
    event_path: Path,
    tasks_root: Path,
    dry_run_reply: bool = True,
    run_delivery: bool = False,
    runner: Callable[[list[str], str | None], str] | None = None,
    generator: str = "codex",
    codex_generator: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    parsed = parse_im_event(payload)
    task_dir = tasks_root / parsed.task_id
    if not task_dir.exists():
        task_dir = create_task_from_event(payload, tasks_root)
    session_key = build_golembot_session_key(
        channel_type="feishu",
        chat_id=parsed.chat_id,
        sender_id=parsed.sender_open_id,
        chat_type=parsed.chat_type,
    )
    bindings_path = tasks_root / "task-bindings.json"
    bind_active_task(
        bindings_path,
        session_key=session_key,
        task_id=parsed.task_id,
        chat_id=parsed.chat_id,
        channel_type="feishu",
        sender_id=parsed.sender_open_id,
        chat_name=parsed.chat_name or None,
    )
    delivery = None
    if run_delivery:
        if not (task_dir / "artifacts.json").exists():
            _generate_task_artifacts(task_dir, generator=generator, codex_generator=codex_generator)
        delivery = deliver_task_to_feishu(
            task_dir,
            parsed.message_id,
            runner=runner,
            dry_run_reply=dry_run_reply,
        )
        clear_active_task(bindings_path, session_key)
    reply = None
    if not run_delivery:
        reply = reply_to_message(
            parsed.message_id,
            f"已创建任务 `{parsed.task_id}`，正在处理。任务目录：`{task_dir.as_posix()}`",
            idempotency_key=f"{parsed.task_id}-accepted",
            dry_run=dry_run_reply,
            runner=_adapt_runner(runner),
        )
    return {
        "task_id": parsed.task_id,
        "task_dir": task_dir.as_posix(),
        "message_id": parsed.message_id,
        "session_key": session_key,
        "reply": reply,
        "delivery": delivery,
    }


def _generate_task_artifacts(
    task_dir: Path,
    generator: str,
    codex_generator: Callable[[Path], None] | None = None,
) -> None:
    if generator == "local":
        run_local_smoke(task_dir)
        return
    if generator == "codex":
        if codex_generator:
            try:
                write_status(task_dir, "running")
                codex_generator(task_dir)
                read_artifacts(task_dir)
            except Exception as exc:
                write_status(task_dir, "failed", error=f"Codex generator failed: {exc}")
                raise
            write_status(task_dir, "completed")
            return
        run_codex_task(task_dir, project_root=PROJECT_ROOT)
        return
    raise ValueError(f"unsupported generator: {generator}")


def _adapt_runner(runner: Callable[[list[str], str | None], str] | None):
    if runner is None:
        return None

    def run_without_input(args: list[str]) -> str:
        try:
            return runner(args, None)
        except TypeError:
            return runner(args)  # type: ignore[misc]

    return run_without_input


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one Feishu IM event JSON file emitted by lark-cli event +subscribe.")
    parser.add_argument("event_path", type=Path)
    parser.add_argument("--tasks-root", type=Path, default=PROJECT_ROOT / "tasks")
    parser.add_argument("--execute-reply", action="store_true", help="Send the real Feishu reply. Defaults to dry-run.")
    parser.add_argument("--run-delivery", action="store_true", help="Generate and publish office artifacts before replying.")
    parser.add_argument(
        "--generator",
        choices=("local", "codex"),
        default="codex",
        help="Artifact generator to use before delivery.",
    )
    args = parser.parse_args()

    result = process_event_file(
        args.event_path,
        args.tasks_root,
        dry_run_reply=not args.execute_reply,
        run_delivery=args.run_delivery,
        generator=args.generator,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
