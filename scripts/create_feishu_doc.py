from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.lark_docs import create_doc_from_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Feishu document from a local Markdown file.")
    parser.add_argument("markdown_path", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--execute", action="store_true", help="Execute the real create call. Defaults to dry-run.")
    args = parser.parse_args()

    result = create_doc_from_markdown(args.markdown_path, args.title, dry_run=not args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
