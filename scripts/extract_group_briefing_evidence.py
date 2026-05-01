from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.group_briefing_extractors.langextract_deepseek import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ID,
    build_source_text,
    extract_evidence,
)
from bridge.group_context import build_standard_group_context
from bridge.group_context_selector import select_briefing_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract source-grounded evidence from a group-chat fixture.")
    parser.add_argument("--context-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chat-id")
    parser.add_argument("--render-source", action="store_true", help="Only render LangExtract input text and spans.")
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--max-char-buffer", type=int, default=3000)
    parser.add_argument("--extraction-passes", type=int, default=1)
    parser.add_argument("--select-context", action="store_true", help="Select a bounded briefing context before extraction.")
    parser.add_argument("--max-context-messages", type=int, default=60)
    parser.add_argument("--recent-tail", type=int, default=16)
    args = parser.parse_args()

    messages = build_standard_group_context(args.context_fixture, chat_id=args.chat_id)
    original_message_count = len(messages)
    if args.select_context:
        messages = select_briefing_context(messages, max_messages=args.max_context_messages, recent_tail=args.recent_tail)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.render_source:
        text, spans = build_source_text(messages)
        payload = {"text": text, "spans": spans}
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"source_messages={len(messages)} original_messages={original_message_count} output={args.output}")
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing API key env var: {args.api_key_env}")
    evidence = extract_evidence(
        messages,
        api_key=api_key,
        base_url=args.base_url,
        model_id=args.model,
        max_char_buffer=args.max_char_buffer,
        extraction_passes=args.extraction_passes,
    )
    payload = {
        "extractor": "langextract-deepseek",
        "model": args.model,
        "source_message_count": len(messages),
        "original_source_message_count": original_message_count,
        "context_selected": args.select_context,
        "evidence": evidence,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"evidence={len(evidence)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
