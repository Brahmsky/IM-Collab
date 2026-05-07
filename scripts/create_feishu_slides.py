from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.lark_slides import create_slides_from_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Feishu Slides presentation from Markdown or slide XML JSON.")
    parser.add_argument("content_path", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--input-format", choices=("auto", "markdown_outline", "slides_xml"), default="auto")
    parser.add_argument("--execute", action="store_true", help="Execute the real create call. Defaults to dry-run.")
    args = parser.parse_args()

    input_format = args.input_format
    if input_format == "auto":
        input_format = "slides_xml" if args.content_path.suffix.lower() == ".json" else "markdown_outline"
    result = create_slides_from_path(
        args.content_path,
        args.title,
        input_format=input_format,
        dry_run=not args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
