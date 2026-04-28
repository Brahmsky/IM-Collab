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
        return {
            "session_key": "feishu:oc_456:ou_789",
            "response": {"finalText": "日志。任务 `gb-123` 已完成。\n\n**文档**: doc"},
        }

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
    assert seen["markdown"].startswith("任务 `gb-123` 已完成")
    assert seen["dry_run"] is True
    assert result["reply"]["ok"] is True


def test_dispatch_event_via_golembot_publishes_after_codex_outside_golembot(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "gb-session"
    task_dir.mkdir(parents=True)
    (tasks_root / "task-bindings.json").write_text(
        json.dumps(
            {
                "feishu:oc_456:ou_789": {
                    "session_key": "feishu:oc_456:ou_789",
                    "active_task_id": "gb-session",
                }
            }
        ),
        encoding="utf-8",
    )
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
        return {
            "session_key": "feishu:oc_456:ou_789",
            "response": {"finalText": "任务 `gb-session` 已完成。\n\n**文档**: local"},
        }

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
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
        seen["markdown"] = markdown
        return {"ok": True}

    dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        forwarder=fake_forwarder,
        publisher=fake_publisher,
        replier=fake_replier,
    )

    assert seen["forward_publish"] is False
    assert seen["published_task_dir"] == task_dir
    assert "https://feishu/doc" in seen["markdown"]


def test_dispatch_event_runs_office_task_outside_golembot_runtime(tmp_path: Path) -> None:
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
                "content": "生成复盘文档、6 页演示稿和白板流程",
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
        seen["published_task_dir"] = published_task_dir
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
        seen["markdown"] = markdown
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
    assert seen["office_kwargs"]["generator"] == "app-server"
    assert seen["office_kwargs"]["task_id"] == "im-om_123"
    assert seen["published_task_dir"] == task_dir
    assert "你好，我是你的办公协作助手。" in seen["markdown"]


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
                "chat_type": "group",
                "message_type": "text",
                "content": "@助手 根据刚才讨论生成项目方案和 PPT",
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
            {"message_id": "om_trigger", "sender": {"id": "ou_requester"}, "content": "@助手 根据刚才讨论生成项目方案和 PPT"},
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
    assert seen["office_kwargs"]["conversation_context"] == [
        {"message_id": "om_1", "sender": {"id": "ou_a"}, "content": "我们要突出群聊入口。"}
    ]


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
                "content": "补充一下：最后要强调手机端也能发起任务",
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
    assert command["payload"]["text"] == "补充一下：最后要强调手机端也能发起任务"
    assert command["payload"]["message_id"] == "om_followup"
    assert command["payload"]["session_key"] == "feishu:oc_group"
    assert command["payload"]["codex_thread_id"] == "thread_live"
    assert command["payload"]["active_turn_id"] == "turn_live"


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
