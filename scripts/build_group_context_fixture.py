from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.group_context import build_standard_group_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a normalized backend group-chat context fixture.")
    parser.add_argument("--input", type=Path, required=True, help="Raw Feishu event JSON/JSONL file or directory.")
    parser.add_argument("--output", type=Path, required=True, help="Destination normalized JSON fixture.")
    parser.add_argument("--chat-id", help="Keep only messages from this chat id.")
    parser.add_argument("--limit", type=int, help="Keep only the latest N messages after filtering.")
    args = parser.parse_args()

    messages = build_standard_group_context(args.input, chat_id=args.chat_id, page_size=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"messages={len(messages)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
