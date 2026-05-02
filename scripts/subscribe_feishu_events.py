from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.lark_event import build_subscribe_args
from bridge.subprocess_utils import run as _sp_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Start lark-cli long-connection event subscription for IM messages.")
    parser.add_argument("--output-dir", type=Path, default=Path("events") / "im")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    command = build_subscribe_args(args.output_dir, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps({"command": command}, ensure_ascii=False, indent=2))
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    return _sp_run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
