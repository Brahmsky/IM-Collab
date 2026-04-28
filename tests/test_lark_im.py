from __future__ import annotations

import json

from bridge.lark_im import build_delivery_markdown, build_list_messages_args, list_chat_messages, build_reply_args, reply_to_message


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
    assert "文档生成完成" in markdown
    assert "还需要我根据群里的消息" in markdown
    assert "Codex" not in markdown
    assert "lark-cli" not in markdown
    assert "Python delivery code" not in markdown
    assert "artifacts" not in markdown
    assert "Bridge" not in markdown
    assert "Published to Feishu" not in markdown
