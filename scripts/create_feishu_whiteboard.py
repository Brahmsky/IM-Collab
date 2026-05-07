from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.lark_whiteboard import create_or_update_whiteboard_from_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or continue a Feishu whiteboard from a local source file.")
    parser.add_argument("source_path", type=Path)
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--document", help="Existing Feishu document id or URL to append a whiteboard into.")
    target_group.add_argument("--whiteboard-token", help="Existing Feishu whiteboard token to overwrite.")
    parser.add_argument("--idempotency-token", required=True)
    parser.add_argument("--input-format", choices=("auto", "mermaid", "plantuml", "raw"), default="auto")
    parser.add_argument("--execute", action="store_true", help="Execute the real whiteboard call. Defaults to dry-run.")
    args = parser.parse_args()

    input_format = args.input_format
    if input_format == "auto":
        suffix = args.source_path.suffix.lower()
        if suffix in {".puml", ".plantuml"}:
            input_format = "plantuml"
        elif suffix in {".mmd", ".mermaid"}:
            input_format = "mermaid"
        else:
            input_format = "raw"

    result = create_or_update_whiteboard_from_source(
        args.source_path,
        idempotency_token=args.idempotency_token,
        document_id_or_url=args.document,
        whiteboard_token=args.whiteboard_token,
        input_format=input_format,
        dry_run=not args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
