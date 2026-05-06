from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.golembot_forwarder import build_golembot_prompt, forward_event_to_golembot
from bridge.feishu_events import parse_im_event
from bridge.lark_im import reply_to_message
from bridge.task_binding import build_golembot_session_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward one lark-cli Feishu event JSON file to GolemBot /chat.")
    parser.add_argument("event_path", type=Path)
    parser.add_argument("--gateway-url", default="http://127.0.0.1:3199")
    parser.add_argument("--token", default="local-golembot-spike")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Ask GolemBot to publish real Feishu office artifacts.")
    parser.add_argument("--generator", choices=("codex", "app-server"), default="app-server")
    parser.add_argument("--execute-reply", action="store_true", help="Reply to the source Feishu message.")
    parser.add_argument("--dry-run-reply", action="store_true", help="Build a dry-run Feishu reply from GolemBot output.")
    parser.add_argument("--reply-from-response", type=Path, help="Use a saved forwarder response JSON instead of calling GolemBot.")
    args = parser.parse_args()

    payload = json.loads(args.event_path.read_text(encoding="utf-8"))
    if args.dry_run:
        event = parse_im_event(payload)
        session_key = build_golembot_session_key(
            channel_type="feishu",
            chat_id=event.chat_id,
            sender_id=event.sender_open_id,
            chat_type=event.chat_type,
        )
        result = {
            "session_key": session_key,
            "message": build_golembot_prompt(payload, publish=args.publish, generator=args.generator),
        }
    elif args.reply_from_response:
        event = parse_im_event(payload)
        forwarded = json.loads(args.reply_from_response.read_text(encoding="utf-8"))
        result = _reply_from_forwarded_response(event.message_id, forwarded, dry_run=not args.execute_reply)
    else:
        result = forward_event_to_golembot(
            payload,
            gateway_url=args.gateway_url,
            token=args.token,
            publish=args.publish,
            generator=args.generator,
        )
        if args.execute_reply or args.dry_run_reply:
            event = parse_im_event(payload)
            result = _reply_from_forwarded_response(event.message_id, result, dry_run=not args.execute_reply)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _reply_from_forwarded_response(message_id: str, forwarded: dict[str, object], dry_run: bool) -> dict[str, object]:
    response = forwarded.get("response", {})
    final_text = response.get("finalText", "") if isinstance(response, dict) else ""
    reply_markdown = str(final_text).strip()
    reply = reply_to_message(
        message_id,
        reply_markdown,
        idempotency_key=f"{message_id}-golembot-forwarded",
        dry_run=dry_run,
    )
    return {**forwarded, "reply_markdown": reply_markdown, "reply": reply}


if __name__ == "__main__":
    raise SystemExit(main())
