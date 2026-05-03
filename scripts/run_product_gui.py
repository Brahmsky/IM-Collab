from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.product_gui import create_product_gui_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Agent-Pilot product GUI.")
    parser.add_argument("--tasks-root", default="tasks")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    app = create_product_gui_app(Path(args.tasks_root))
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
