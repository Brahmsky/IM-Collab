from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.event_consumer import EventConsumer, EventConsumerConfig
from bridge.golembot_dispatch import dispatch_event_via_golembot
from scripts.process_feishu_event import process_event_file


def build_config(
    event_dir: Path = Path("events") / "im",
    tasks_root: Path = Path("tasks"),
    state_path: Path | None = None,
    bot_open_ids: tuple[str, ...] = (),
    poll_interval_seconds: float = 1.0,
) -> EventConsumerConfig:
    return EventConsumerConfig(
        event_dir=event_dir,
        tasks_root=tasks_root,
        state_path=state_path or event_dir / ".consumer-state.json",
        bot_open_ids=frozenset(bot_open_ids),
        poll_interval_seconds=poll_interval_seconds,
    )


def build_handler(args: argparse.Namespace, config: EventConsumerConfig):
    def handle(event_path: Path) -> None:
        if args.dispatch == "golembot":
            dispatch_event_via_golembot(
                event_path,
                gateway_url=args.golembot_url,
                token=args.golembot_token,
                publish=args.publish,
                generator=args.generator,
                execute_reply=args.execute,
                tasks_root=config.tasks_root,
            )
        else:
            process_event_file(
                event_path,
                config.tasks_root,
                dry_run_reply=not args.execute,
                run_delivery=args.execute,
            )

    return handle


def main() -> int:
    parser = argparse.ArgumentParser(description="Consume lark-cli event files and dispatch IM-Collab tasks.")
    parser.add_argument("--event-dir", type=Path, default=Path("events") / "im")
    parser.add_argument("--tasks-root", type=Path, default=Path("tasks"))
    parser.add_argument("--state-path", type=Path)
    parser.add_argument("--bot-open-id", action="append", default=[])
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--once", action="store_true", help="Process current event files once and exit.")
    parser.add_argument("--execute", action="store_true", help="Run full delivery and send real Feishu replies.")
    parser.add_argument("--dispatch", choices=("local", "golembot"), default="local")
    parser.add_argument("--golembot-url", default="http://127.0.0.1:3199")
    parser.add_argument("--golembot-token", default="local-golembot-spike")
    parser.add_argument("--publish", action="store_true", help="Ask GolemBot task runner to publish real Feishu artifacts.")
    parser.add_argument("--generator", choices=("codex", "local", "app-server"), default="app-server")
    args = parser.parse_args()

    config = build_config(
        event_dir=args.event_dir,
        tasks_root=args.tasks_root,
        state_path=args.state_path,
        bot_open_ids=tuple(args.bot_open_id),
        poll_interval_seconds=args.poll_interval,
    )

    consumer = EventConsumer(config, build_handler(args, config))
    if args.once:
        count = consumer.process_once()
        print(f"processed={count}")
        return 0

    consumer.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
