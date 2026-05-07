from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.lark_docs import create_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Feishu document from Markdown or DocxXML input.")
    parser.add_argument("content_path", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--doc-format", choices=("auto", "markdown", "xml"), default="auto")
    parser.add_argument("--inline-content", help="Pass inline content directly instead of reading a local file.")
    parser.add_argument("--execute", action="store_true", help="Execute the real create call. Defaults to dry-run.")
    args = parser.parse_args()

    doc_format = args.doc_format
    if doc_format == "auto":
        doc_format = "xml" if args.content_path.suffix.lower() == ".xml" else "markdown"

    if args.inline_content is not None:
        result = create_doc(
            title=args.title,
            content=args.inline_content,
            doc_format=doc_format,
            dry_run=not args.execute,
        )
    else:
        result = create_doc(
            title=args.title,
            content_path=args.content_path,
            doc_format=doc_format,
            dry_run=not args.execute,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
