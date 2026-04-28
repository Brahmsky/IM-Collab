from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.demo_chain import build_demo_chain_commands


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the IM-Collab demo chain startup commands.")
    parser.add_argument("--no-publish", action="store_true", help="Do not ask GolemBot to publish Feishu office artifacts.")
    parser.add_argument("--no-execute", action="store_true", help="Do not send real Feishu replies.")
    args = parser.parse_args()

    payload = {
        "required_env": ["FEISHU_APP_ID", "FEISHU_APP_SECRET"],
        "commands": build_demo_chain_commands(publish=not args.no_publish, execute=not args.no_execute),
        "user_flow": [
            "Start the GolemBot gateway command.",
            "Start the Feishu listener command.",
            "Start the consumer command.",
            "In Feishu, send a natural-language office task to the bot.",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
