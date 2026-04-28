from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.codex_runner import build_codex_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Codex task prompt for an IM-Collab task directory.")
    parser.add_argument("task_dir", type=Path)
    args = parser.parse_args()

    print(build_codex_prompt(args.task_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
