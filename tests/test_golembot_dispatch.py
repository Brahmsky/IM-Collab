from __future__ import annotations

import json
from pathlib import Path

from bridge.golembot_dispatch import dispatch_event_via_golembot


def test_dispatch_event_via_golembot_forwards_and_replies(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": "继续刚才的任务",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_forwarder(
        payload: dict[str, object],
        gateway_url: str,
        token: str,
        publish: bool = False,
        generator: str = "codex",
    ) -> dict[str, object]:
        seen["publish"] = publish
        seen["generator"] = generator
        return {"session_key": "feishu:oc_456:ou_789", "response": {"finalText": "日志。任务 `gb-123` 已完成。"}}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["message_id"] = message_id
        seen["markdown"] = markdown
        seen["dry_run"] = dry_run
        return {"ok": True, "dry_run": dry_run}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=False,
        execute_reply=False,
        forwarder=fake_forwarder,
        replier=fake_replier,
    )

    assert seen["publish"] is False
    assert seen["generator"] == "app-server"
    assert seen["message_id"] == "om_123"
    assert seen["markdown"] == "日志。任务 `gb-123` 已完成。"
    assert seen["dry_run"] is True
    assert result["reply"]["ok"] is True


def test_dispatch_event_via_golembot_does_not_publish_by_reply_text_prefix(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
            "content": "继续刚才的任务",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_forwarder(
        payload: dict[str, object],
        gateway_url: str,
        token: str,
        publish: bool = False,
        generator: str = "codex",
    ) -> dict[str, object]:
        seen["forward_publish"] = publish
        return {"session_key": "feishu:oc_456:ou_789", "response": {"finalText": "任务 `gb-session` 已完成。"}}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        (published_task_dir / "delivery_card.json").write_text(
            json.dumps({"header": {"title": {"content": "办公材料已生成"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "gb-session",
            "artifacts": {
                "task_id": "gb-session",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["markdown_reply"] = True
        seen["markdown"] = markdown
        return {"ok": True}

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path, "dry_run": dry_run}
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=False,
        execute_reply=True,
        tasks_root=tasks_root,
        forwarder=fake_forwarder,
        publisher=fake_publisher,
        replier=fake_replier,
        card_replier=fake_card_replier,
    )

    assert seen["forward_publish"] is False
    assert "published_task_dir" not in seen
    assert seen["markdown"] == "任务 `gb-session` 已完成。"
    assert "card_reply" not in seen


def test_dispatch_event_runs_office_task_in_publish_mode_without_keyword_routing(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_123"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": "这是一条没有办公关键词的 @bot 请求",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_forwarder(*args, **kwargs) -> dict[str, object]:
        seen["forwarded"] = True
        return {"session_key": "feishu:oc_456:ou_789", "response": {"finalText": "收到。"}}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_123", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        (published_task_dir / "delivery_card.json").write_text(
            json.dumps({"header": {"title": {"content": "办公材料已生成"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "im-om_123",
            "artifacts": {
                "task_id": "im-om_123",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["markdown_reply"] = True
        seen["markdown"] = markdown
        return {"ok": True}

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path, "dry_run": dry_run}
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        forwarder=fake_forwarder,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        card_replier=fake_card_replier,
    )

    assert "forwarded" not in seen
    assert seen["office_kwargs"]["generator"] == "app-server"
    assert seen["office_kwargs"]["task_id"] == "im-om_123"
    assert seen["published_task_dir"] == task_dir
    assert "markdown_reply" not in seen
    assert seen["card_reply"]["message_id"] == "om_123"
    assert seen["card_reply"]["card_path"] == task_dir / "delivery_card.json"


def test_dispatch_group_office_task_passes_recent_group_context(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_trigger"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_trigger",
                "chat_id": "oc_group",
                "chat_name": "IM-Collab 群聊测试",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 根据刚才讨论生成项目方案和 PPT",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20):
        seen["context_chat_id"] = chat_id
        return [
            {"message_id": "om_1", "sender": {"id": "ou_a"}, "content": "我们要突出群聊入口。"},
            {"message_id": "om_trigger", "sender": {"id": "ou_requester"}, "content": "@飞书 CLI 根据刚才讨论生成项目方案和 PPT"},
        ]

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_trigger", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        return {
            "task_id": "im-om_trigger",
            "artifacts": {
                "task_id": "im-om_trigger",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    assert seen["context_chat_id"] == "oc_group"
    assert seen["office_kwargs"]["session_key"] == "feishu:oc_group"
    assert seen["office_kwargs"]["chat_name"] == "IM-Collab 群聊测试"
    assert seen["office_kwargs"]["conversation_context"] == [
        {"message_id": "om_1", "sender": {"id": "ou_a"}, "content": "我们要突出群聊入口。"}
    ]


def test_dispatch_group_message_without_bot_mention_is_ignored(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_ignore",
                "chat_id": "oc_group",
                "chat_name": "IM-Collab 群聊测试",
                "chat_type": "group",
                "message_type": "text",
                "content": "/new 5h 生成项目复盘",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
    )

    assert result["ignored"] is True
    assert not (tasks_root / "im-om_ignore").exists()


def test_dispatch_new_group_session_uses_boundary_context_and_langextract(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_new",
                "chat_id": "oc_group",
                "chat_name": "IM-Collab 群聊测试",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI /new 生成项目复盘",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20):
        seen["context_page_size"] = page_size
        return [
            {"message_id": "om_old", "content": "去年旧要求", "sent_at": "2025-01-01T10:00:00+08:00"},
            {"message_id": "om_prev_new", "content": "/new 三天前任务", "sent_at": "2026-05-03T10:00:00+08:00"},
            {"message_id": "om_after", "content": "昨天新增要求", "sent_at": "2026-05-05T10:00:00+08:00"},
            {"message_id": "om_new", "content": "@飞书 CLI /new 生成项目复盘", "sent_at": "2026-05-06T11:00:00+08:00"},
        ]

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_new", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        return {"task_id": "im-om_new", "artifacts": {"task_id": "im-om_new", "items": [], "summary": "ok", "next_steps": []}}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    assert seen["context_page_size"] == 80
    assert seen["office_kwargs"]["message"] == "生成项目复盘"
    assert seen["office_kwargs"]["task_id"] == "im-om_new"
    assert seen["office_kwargs"]["session_key"] == "feishu:oc_group:session:om_new"
    assert seen["office_kwargs"]["chat_name"] == "IM-Collab 群聊测试"
    assert seen["office_kwargs"]["brief_extractor"] == "langextract-deepseek"
    assert seen["office_kwargs"]["conversation_context"] == [
        {"message_id": "om_after", "content": "昨天新增要求", "sent_at": "2026-05-05T10:00:00+08:00"}
    ]


def test_dispatch_new_group_session_with_time_uses_time_window(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_new",
                "chat_id": "oc_group",
                "chat_name": "IM-Collab 群聊测试",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI /new 6h 只整理今天新增",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20):
        return [
            {"message_id": "om_prev_new", "content": "/new 三天前任务", "sent_at": "2026-05-03T10:00:00+08:00"},
            {"message_id": "om_yesterday", "content": "昨天要求", "sent_at": "2026-05-05T10:00:00+08:00"},
            {"message_id": "om_today", "content": "今天要求", "sent_at": "2026-05-06T10:00:00+08:00"},
            {"message_id": "om_new", "content": "@飞书 CLI /new 6h 只整理今天新增", "sent_at": "2026-05-06T11:00:00+08:00"},
        ]

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_new", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        return {"task_id": "im-om_new", "artifacts": {"task_id": "im-om_new", "items": [], "summary": "ok", "next_steps": []}}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    assert seen["office_kwargs"]["message"] == "只整理今天新增"
    assert seen["office_kwargs"]["conversation_context"] == [
        {"message_id": "om_today", "content": "今天要求", "sent_at": "2026-05-06T10:00:00+08:00"}
    ]


def test_dispatch_new_group_session_with_time_passes_cutoff_to_live_context_reader(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_new",
                "chat_id": "oc_group",
                "chat_name": "IM-Collab 群聊测试",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI /new 2d6h 整理最近上下文",
                "sender_id": "ou_requester",
                "create_time": "1778050800000",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20, cutoff_after=None):
        seen["cutoff_after"] = cutoff_after
        return [
            {"message_id": "om_context", "content": "最近上下文", "create_time": "1778040000000"},
            {"message_id": "om_new", "content": "@飞书 CLI /new 2d6h 整理最近上下文", "create_time": "1778050800000"},
        ]

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_new", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        return {"task_id": "im-om_new", "artifacts": {"task_id": "im-om_new", "items": [], "summary": "ok", "next_steps": []}}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    assert seen["cutoff_after"].isoformat() == "2026-05-04T01:00:00+00:00"


def test_dispatch_new_group_session_falls_back_to_empty_context_when_live_context_reader_is_unauthorized(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_new",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI /new 5h 生成项目复盘",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    def unauthorized_context_reader(chat_id: str, page_size: int = 20):
        raise RuntimeError("need_user_authorization")

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        replier=fake_replier,
        context_reader=unauthorized_context_reader,
    )

    status = json.loads((task_dir / "status.json").read_text(encoding="utf-8"))
    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert status["state"] == "failed"
    assert "need_user_authorization" in status["error"]
    assert bindings["feishu:oc_group:session:om_new"]["last_task_id"] == "im-om_new"
    assert result["task_id"] == "im-om_new"


def test_dispatch_group_office_task_replies_confirmation_when_brief_waits(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_trigger"
    task_dir.mkdir(parents=True)
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_trigger",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 根据刚才讨论生成项目方案和 PPT",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20):
        return [
            {"message_id": "om_1", "sender_id": "teacher", "content": "PPT 不超过 8 页。"},
            {"message_id": "om_2", "sender_id": "ou_a", "content": "PPT 可以 10 页？"},
        ]

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        (task_dir / "confirmation.md").write_text("请确认：PPT 页数出现多个版本。引用: om_1, om_2\n", encoding="utf-8")
        (task_dir / "confirmation_card.json").write_text(
            json.dumps({"header": {"title": {"content": "请确认群聊需求"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "im-om_trigger",
            "task_dir": task_dir.as_posix(),
            "state": "waiting_for_user",
            "reply_markdown": "请确认：PPT 页数出现多个版本。引用: om_1, om_2",
        }

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        return {}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["markdown_reply"] = True
        seen["reply"] = {"message_id": message_id, "markdown": markdown, "dry_run": dry_run}
        return {"ok": True}

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        card_replier=fake_card_replier,
        context_reader=fake_context_reader,
    )

    assert "published_task_dir" not in seen
    assert "markdown_reply" not in seen
    assert seen["card_reply"]["message_id"] == "om_trigger"
    assert seen["card_reply"]["card_path"] == task_dir / "confirmation_card.json"
    assert result["publish"] is None
    assert result["task"]["state"] == "waiting_for_user"


def test_dispatch_group_permission_error_falls_back_to_empty_context_and_continues(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_perm",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI /new 5h 帮忙生成这个ppt，然后返回到这里",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_context_reader(chat_id: str, page_size: int = 20):
        raise RuntimeError("Permission denied [230027]")

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["reply"] = {"message_id": message_id, "markdown": markdown, "dry_run": dry_run}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    task_dir = tasks_root / "im-om_perm"
    status = json.loads((task_dir / "status.json").read_text(encoding="utf-8"))
    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert status["state"] == "failed"
    assert "230027" in status["error"]
    assert bindings["feishu:oc_group:session:om_perm"]["last_task_id"] == "im-om_perm"
    assert seen["reply"]["message_id"] == "om_perm"
    assert "群聊历史读取权限" in str(seen["reply"]["markdown"])
    assert result["task_id"] == "im-om_perm"


def test_dispatch_group_message_appends_instruction_to_active_turn(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_active"
    task_dir.mkdir(parents=True)
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group": {
                    "session_key": "feishu:oc_group",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_active",
                    "last_task_id": None,
                    "codex_thread_id": "thread_live",
                    "active_turn_id": "turn_live",
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_followup",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 补充一下：最后要强调手机端也能发起任务",
                "sender_id": "ou_teammate",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_forwarder(*args, **kwargs) -> dict[str, object]:
        seen["forwarded"] = True
        return {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["reply"] = {
            "message_id": message_id,
            "markdown": markdown,
            "idempotency_key": idempotency_key,
            "dry_run": dry_run,
        }
        return {"ok": True, "dry_run": dry_run}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        forwarder=fake_forwarder,
        office_runner=fake_office_runner,
        replier=fake_replier,
    )

    assert "forwarded" not in seen
    assert "office_kwargs" not in seen
    assert seen["reply"]["message_id"] == "om_followup"
    assert "我会把这条补充进当前任务" in seen["reply"]["markdown"]
    assert result["task_id"] == "im-om_active"

    [command] = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command["type"] == "append_instruction"
    assert command["operator"] == "feishu"
    assert command["payload"]["text"] == "@飞书 CLI 补充一下：最后要强调手机端也能发起任务"
    assert command["payload"]["message_id"] == "om_followup"
    assert command["payload"]["session_key"] == "feishu:oc_group"
    assert command["payload"]["codex_thread_id"] == "thread_live"
    assert command["payload"]["active_turn_id"] == "turn_live"


def test_dispatch_group_followup_routes_to_latest_new_session_active_turn(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    new_task_dir = tasks_root / "im-om_new"
    new_task_dir.mkdir(parents=True)
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group:session:om_new": {
                    "session_key": "feishu:oc_group:session:om_new",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_new",
                    "last_task_id": None,
                    "codex_thread_id": "thread_new",
                    "active_turn_id": "turn_new",
                    "updated_at": "2026-05-06T01:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_followup",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 补充：封面要更正式",
                "sender_id": "ou_teammate",
            }
        ),
        encoding="utf-8",
    )

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True, "message_id": message_id, "markdown": markdown}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        replier=fake_replier,
    )

    assert result["session_key"] == "feishu:oc_group:session:om_new"
    assert result["task_id"] == "im-om_new"
    [command] = [
        json.loads(line)
        for line in (new_task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command["payload"]["session_key"] == "feishu:oc_group:session:om_new"
    assert command["payload"]["codex_thread_id"] == "thread_new"
    assert command["payload"]["active_turn_id"] == "turn_new"


def test_dispatch_group_followup_appends_delta_group_context_since_last_absorbed_boundary(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    task_dir.mkdir(parents=True)
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group:session:om_new": {
                    "session_key": "feishu:oc_group:session:om_new",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_new",
                    "last_task_id": None,
                    "codex_thread_id": "thread_new",
                    "active_turn_id": "turn_new",
                    "last_absorbed_message_id": "om_prev",
                    "updated_at": "2026-05-06T01:00:00+00:00",
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_followup",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 补充：封面要更正式",
                "sender_id": "ou_teammate",
            }
        ),
        encoding="utf-8",
    )

    def fake_context_reader(chat_id: str, page_size: int = 20):
        assert chat_id == "oc_group"
        return [
            {"message_id": "om_old", "content": "旧消息"},
            {"message_id": "om_prev", "content": "上次已经吸收过的边界消息"},
            {"message_id": "om_delta_1", "content": "昨天有人补充了答辩时间"},
            {"message_id": "om_delta_2", "content": "今天有人补充了封面风格"},
            {"message_id": "om_followup", "content": "@飞书 CLI 补充：封面要更正式"},
        ]

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True, "message_id": message_id, "markdown": markdown}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        replier=fake_replier,
        context_reader=fake_context_reader,
    )

    [command] = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [message["message_id"] for message in command["payload"]["group_context"]] == ["om_delta_1", "om_delta_2"]
    assert "昨天有人补充了答辩时间" in command["payload"]["codex_input_text"]
    assert "今天有人补充了封面风格" in command["payload"]["codex_input_text"]
    assert "补充：封面要更正式" in command["payload"]["codex_input_text"]


def test_dispatch_group_message_appends_natural_language_to_waiting_task(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_waiting"
    task_dir.mkdir(parents=True)
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_waiting",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group": {
                    "session_key": "feishu:oc_group",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_waiting",
                    "last_task_id": None,
                    "codex_thread_id": "thread_waiting",
                    "active_turn_id": None,
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_confirm",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 确认按 8 页 PPT 执行",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {}

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["markdown_reply"] = True
        seen["reply"] = {"message_id": message_id, "markdown": markdown}
        return {"ok": True}

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        replier=fake_replier,
    )

    assert "office_kwargs" not in seen
    assert "我会把这条补充进当前任务" in seen["reply"]["markdown"]
    assert result["task_id"] == "im-om_waiting"
    [command] = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command["type"] == "append_instruction"
    assert command["payload"]["text"] == "@飞书 CLI 确认按 8 页 PPT 执行"


def test_dispatch_group_start_message_does_not_semantically_resume_waiting_task(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_waiting"
    task_dir.mkdir(parents=True)
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_waiting",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group": {
                    "session_key": "feishu:oc_group",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_waiting",
                    "last_task_id": None,
                    "codex_thread_id": "thread_waiting",
                    "active_turn_id": None,
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_start",
                "chat_id": "oc_group",
                "chat_type": "group",
                "message_type": "text",
                "content": "@飞书 CLI 确认开始执行，按 8 页 PPT 做",
                "sender_id": "ou_requester",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {"task_id": "im-om_waiting", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        (published_task_dir / "delivery_card.json").write_text(
            json.dumps({"header": {"title": {"content": "办公材料已生成"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "im-om_waiting",
            "artifacts": {
                "task_id": "im-om_waiting",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["markdown_reply"] = True
        seen["reply"] = {"message_id": message_id, "markdown": markdown}
        return {"ok": True}

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
        card_replier=fake_card_replier,
    )

    assert "office_kwargs" not in seen
    assert "published_task_dir" not in seen
    assert "card_reply" not in seen
    assert seen["reply"]["message_id"] == "om_start"
    assert "我会把这条补充进当前任务" in seen["reply"]["markdown"]
    assert result["task_id"] == "im-om_waiting"
    commands = [
        json.loads(line)
        for line in (task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert commands[0]["type"] == "append_instruction"
    assert commands[0]["payload"]["text"] == "@飞书 CLI 确认开始执行，按 8 页 PPT 做"


def test_dispatch_event_routes_mojibake_office_request_outside_golembot(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_123"
    event_path.write_text(
        json.dumps(
            {
                "type": "im.message.receive_v1",
                "message_id": "om_123",
                "chat_id": "oc_456",
                "chat_type": "p2p",
                "message_type": "text",
                "content": "?? IM-Collab ?????????6 ???? ?????,???????",
                "sender_id": "ou_789",
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_forwarder(*args, **kwargs) -> dict[str, object]:
        seen["forwarded"] = True
        return {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        task_dir.mkdir(parents=True)
        return {"task_id": "im-om_123", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        return {
            "task_id": "im-om_123",
            "artifacts": {
                "task_id": "im-om_123",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        forwarder=fake_forwarder,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
    )

    assert "forwarded" not in seen
    assert seen["office_kwargs"]["task_id"] == "im-om_123"


def test_dispatch_card_start_action_runs_waiting_task_and_publishes(tmp_path: Path) -> None:
    event_path = tmp_path / "card-event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_waiting"
    task_dir.mkdir(parents=True)
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_waiting",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "card.action.trigger",
                "message_id": "om_card",
                "chat_id": "oc_group",
                "open_id": "ou_requester",
                "action": {"value": {"action": "start_task", "task_id": "im-om_waiting"}},
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {"task_id": "im-om_waiting", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        (published_task_dir / "delivery_card.json").write_text(
            json.dumps({"header": {"title": {"content": "办公材料已生成"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "im-om_waiting",
            "artifacts": {
                "task_id": "im-om_waiting",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        card_replier=fake_card_replier,
    )

    assert seen["office_kwargs"]["task_id"] == "im-om_waiting"
    assert seen["office_kwargs"]["message"] == "开始执行"
    assert seen["published_task_dir"] == task_dir
    assert seen["card_reply"]["card_path"] == task_dir / "delivery_card.json"
    assert result["task"]["task_id"] == "im-om_waiting"


def test_dispatch_card_start_action_preserves_new_session_key(tmp_path: Path) -> None:
    event_path = tmp_path / "card-event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_new"
    task_dir.mkdir(parents=True)
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_new",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_group:session:om_new": {
                    "session_key": "feishu:oc_group:session:om_new",
                    "channel_type": "feishu",
                    "chat_id": "oc_group",
                    "sender_id": "ou_requester",
                    "active_task_id": "im-om_new",
                    "last_task_id": None,
                    "codex_thread_id": "thread_new",
                    "active_turn_id": None,
                }
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "card.action.trigger",
                "message_id": "om_card",
                "chat_id": "oc_group",
                "open_id": "ou_requester",
                "action": {
                    "value": {
                        "action": "start_task",
                        "task_id": "im-om_new",
                        "session_key": "feishu:oc_group:session:om_new",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {"task_id": "im-om_new", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        return {
            "task_id": "im-om_new",
            "artifacts": {"task_id": "im-om_new", "items": [], "summary": "ok", "next_steps": []},
        }

    def fake_replier(message_id: str, markdown: str, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        replier=fake_replier,
    )

    assert seen["office_kwargs"]["session_key"] == "feishu:oc_group:session:om_new"
    assert result["session_key"] == "feishu:oc_group:session:om_new"
