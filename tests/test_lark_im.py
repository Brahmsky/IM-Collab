from __future__ import annotations

import json

from pathlib import Path

from bridge.lark_im import (
    build_delivery_markdown,
    build_delivery_card,
    build_list_messages_args,
    build_reply_args,
    build_reply_card_args,
    list_chat_messages,
    reply_card_to_message,
    reply_to_message,
)


def test_build_reply_args_uses_markdown_and_idempotency_key() -> None:
    args = build_reply_args(
        message_id="om_123",
        markdown="完成了",
        idempotency_key="task-123",
        dry_run=True,
    )

    assert args == [
        "lark-cli",
        "im",
        "+messages-reply",
        "--as",
        "bot",
        "--message-id",
        "om_123",
        "--markdown",
        "完成了",
        "--idempotency-key",
        "task-123",
        "--dry-run",
    ]


def test_build_reply_card_args_uses_card_file(tmp_path: Path) -> None:
    card_path = tmp_path / "confirmation_card.json"
    card_path.write_text('{"header":{"title":{"content":"请确认群聊需求"}}}', encoding="utf-8")

    args = build_reply_card_args(
        message_id="om_123",
        card_path=card_path,
        idempotency_key="task-123-card",
        dry_run=True,
    )

    assert args[:8] == ["lark-cli", "im", "+messages-reply", "--as", "bot", "--message-id", "om_123", "--msg-type"]
    assert args[8] == "interactive"
    assert args[args.index("--content") + 1] == '{"header":{"title":{"content":"请确认群聊需求"}}}'
    assert args[-3:] == ["--idempotency-key", "task-123-card", "--dry-run"]


def test_build_reply_args_hashes_long_idempotency_key() -> None:
    args = build_reply_args(
        message_id="om_123",
        markdown="完成了",
        idempotency_key="om_x100b5030b87f5888b35f599b35893a6-golembot-forwarded",
    )

    key_index = args.index("--idempotency-key")
    key = args[key_index + 1]
    assert key.startswith("imc-")
    assert len(key) <= 50
    assert key != "om_x100b5030b87f5888b35f599b35893a6-golembot-forwarded"


def test_reply_to_message_extracts_json_from_dry_run_output() -> None:
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/im/v1/messages/om_123/reply"}]})

    result = reply_to_message("om_123", "hello", idempotency_key="task-123", dry_run=True, runner=fake_run)

    assert seen_args[-1] == "--dry-run"
    assert result["ok"] is True
    assert result["response"]["api"][0]["url"].endswith("/reply")


def test_reply_card_to_message_uses_card_file_and_extracts_json(tmp_path: Path) -> None:
    card_path = tmp_path / "delivery_card.json"
    card_path.write_text('{"header":{"title":{"content":"办公材料已生成"}}}', encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/im/v1/messages/om_123/reply"}]})

    result = reply_card_to_message(
        "om_123",
        card_path,
        idempotency_key="task-123-delivery-card",
        dry_run=True,
        runner=fake_run,
    )

    assert "--msg-type" in seen_args
    assert seen_args[seen_args.index("--msg-type") + 1] == "interactive"
    assert "--content" in seen_args
    assert "delivery_card.json" not in seen_args
    assert seen_args[-1] == "--dry-run"
    assert result["ok"] is True
    assert result["response"]["api"][0]["url"].endswith("/reply")


def test_build_list_messages_args_reads_group_context_as_user() -> None:
    args = build_list_messages_args("oc_group", page_size=20)

    assert args == [
        "lark-cli",
        "im",
        "+chat-messages-list",
        "--as",
        "user",
        "--chat-id",
        "oc_group",
        "--page-size",
        "20",
        "--sort",
        "desc",
    ]


def test_build_list_messages_args_can_read_group_context_as_bot() -> None:
    args = build_list_messages_args("oc_group", page_size=20, identity="bot")

    assert args[args.index("--as") + 1] == "bot"


def test_list_chat_messages_returns_recent_messages_oldest_first() -> None:
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return json.dumps(
            {
                "ok": True,
                "data": {
                    "messages": [
                        {"message_id": "om_new", "sender": {"id": "ou_a"}, "content": "最新"},
                        {"message_id": "om_old", "sender": {"id": "ou_b"}, "content": "较早"},
                    ]
                },
            }
        )

    messages = list_chat_messages("oc_group", page_size=20, runner=fake_run)

    assert seen_args[:3] == ["lark-cli", "im", "+chat-messages-list"]
    assert [message["message_id"] for message in messages] == ["om_old", "om_new"]


def test_build_delivery_markdown_includes_artifact_links() -> None:
    markdown = build_delivery_markdown(
        {
            "task_id": "im-om_123",
            "document": {"remote": {"url": "https://example/doc"}},
            "slides": {"remote": {"url": "https://example/slides"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
            "summary": "已完成。",
            "next_steps": ["接入 webhook"],
        }
    )

    assert "https://example/doc" in markdown
    assert "https://example/slides" in markdown
    assert "wb_123" in markdown
    assert markdown.count("https://example/doc") == 1
    assert "[文档]" not in markdown


def test_build_delivery_markdown_uses_user_facing_assistant_voice() -> None:
    markdown = build_delivery_markdown(
        {
            "task_id": "im-om_123",
            "document": {"remote": {"url": "https://example/doc"}},
            "slides": {"remote": {"url": "https://example/slides"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
            "summary": "Codex generated artifacts. Published to Feishu via lark-cli.",
            "next_steps": [
                "由 Python delivery code 读取 artifacts.json 并执行发布。",
                "在 Bridge 中补充 artifacts schema 校验和发布结果回写。",
            ],
        }
    )

    assert markdown.startswith("你好，我是你的办公协作助手。")
    assert "相关材料已经整理好" in markdown
    assert "还需要我根据群里的消息" in markdown
    assert "Codex" not in markdown
    assert "lark-cli" not in markdown
    assert "Python delivery code" not in markdown
    assert "artifacts" not in markdown
    assert "Bridge" not in markdown
    assert "Published to Feishu" not in markdown


def test_build_delivery_card_contains_artifact_buttons() -> None:
    card = build_delivery_card(
        {
            "task_id": "im-om_123",
            "document": {"remote": {"url": "https://example/doc"}},
            "slides": {"remote": {"url": "https://example/slides"}},
            "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
            "summary": "已完成。",
            "next_steps": [],
        }
    )

    assert card["config"]["wide_screen_mode"] is True
    assert card["header"]["title"]["content"] == "材料已生成"
    assert {"tag": "button", "text": {"tag": "plain_text", "content": "打开document"}, "type": "primary", "url": "https://example/doc"} in card["elements"]
    assert {"tag": "button", "text": {"tag": "plain_text", "content": "打开slides"}, "type": "default", "url": "https://example/slides"} in card["elements"]
