from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.golembot_office_loop import run_golembot_office_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one IM-Collab office task from a GolemBot/Codex session.")
    parser.add_argument("--message", required=True)
    parser.add_argument("--session-key", required=True)
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--sender-id", required=True)
    parser.add_argument("--tasks-root", type=Path, default=PROJECT_ROOT / "tasks")
    parser.add_argument("--task-id")
    parser.add_argument("--generator", choices=("local", "codex", "app-server"), default="local")
    parser.add_argument("--publish", action="store_true", help="Publish artifacts to Feishu office surfaces.")
    parser.add_argument("--brief-extractor", choices=("rules", "langextract-deepseek"), default="rules")
    parser.add_argument("--brief-api-key-env", default="DEEPSEEK_API_KEY")
    args = parser.parse_args()

    result = run_golembot_office_task(
        message=args.message,
        session_key=args.session_key,
        chat_id=args.chat_id,
        sender_id=args.sender_id,
        tasks_root=args.tasks_root,
        task_id=args.task_id,
        generator=args.generator,
        publish=args.publish,
        brief_extractor=args.brief_extractor,
        brief_api_key=None if args.brief_extractor == "rules" else __import__("os").environ.get(args.brief_api_key_env),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
