from __future__ import annotations

import json
from pathlib import Path

from bridge.golembot_office_loop import run_golembot_office_task
from bridge.codex_app_server import CodexTurn
from bridge.task_binding import get_task_binding
from bridge.task_protocol import read_artifacts, read_status
from tests.test_codex_task_runner import write_codex_outputs


def test_run_golembot_office_task_creates_task_and_returns_reply(tmp_path: Path) -> None:
    result = run_golembot_office_task(
        message="根据群聊生成项目方案、PPT 和白板",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-test-task",
        generator="local",
        publish=False,
    )

    task_dir = tmp_path / "gb-test-task"
    assert read_status(task_dir)["state"] == "completed"
    assert read_artifacts(task_dir)["task_id"] == "gb-test-task"
    assert result["reply_markdown"].startswith("你好，我是你的办公协作助手。")
    assert "文档生成完成" in result["reply_markdown"]
    assert get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")["last_task_id"] == "gb-test-task"
    assert get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")["active_task_id"] is None


def test_run_golembot_office_task_writes_group_context_to_request(tmp_path: Path) -> None:
    run_golembot_office_task(
        message="根据刚才讨论生成方案和 PPT",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="group-task",
        generator="local",
        publish=False,
        conversation_context=[
            {"message_id": "om_1", "sender_id": "ou_a", "content": "我们主打飞书群聊入口。"},
            {"message_id": "om_2", "sender_id": "ou_b", "content": "PPT 要突出多端协同。"},
        ],
    )

    request = (tmp_path / "group-task" / "request.md").read_text(encoding="utf-8")
    assert "## Conversation Context" in request
    assert "我们主打飞书群聊入口。" in request
    assert "PPT 要突出多端协同。" in request


def test_run_golembot_office_task_can_publish_without_im_reply(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], input_text: str | None = None) -> str:
        calls.append(args)
        command = " ".join(args[:3])
        if command == "lark-cli docs +create":
            return json.dumps({"ok": True, "data": {"document": {"document_id": "doc_123", "url": "doc_url"}}})
        if command == "lark-cli slides +create":
            return json.dumps(
                {"ok": True, "data": {"xml_presentation_id": "slides_123", "url": "slides_url", "slides_added": 8}}
            )
        if command == "lark-cli docs +update":
            return json.dumps(
                {
                    "ok": True,
                    "data": {
                        "document": {
                            "new_blocks": [
                                {"block_id": "block_123", "block_token": "whiteboard_123", "block_type": "whiteboard"}
                            ]
                        }
                    },
                }
            )
        if command == "lark-cli whiteboard +update":
            return json.dumps({"ok": True, "data": {"created_node_id": "t1:2"}})
        raise AssertionError(args)

    result = run_golembot_office_task(
        message="生成项目方案",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-publish-task",
        generator="local",
        publish=True,
        runner=fake_run,
    )

    artifacts = read_artifacts(tmp_path / "gb-publish-task")
    assert artifacts["document"]["remote"]["url"] == "doc_url"
    assert "doc_url" in result["reply_markdown"]
    assert not any(call[:3] == ["lark-cli", "im", "+messages-reply"] for call in calls)


def test_run_golembot_office_task_can_use_app_server_generator(tmp_path: Path) -> None:
    class FakeAppServerBackend:
        def start_task(self, task_dir: Path) -> CodexTurn:
            write_codex_outputs(task_dir)
            return CodexTurn(thread_id="thread_123", turn_id="turn_456")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            return {"id": turn_id, "status": "completed"}

    result = run_golembot_office_task(
        message="生成项目方案",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-app-server-task",
        generator="app-server",
        publish=False,
        codex_backend=FakeAppServerBackend(),
    )

    binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
    assert result["task_id"] == "gb-app-server-task"
    assert read_status(tmp_path / "gb-app-server-task")["state"] == "completed"
    assert binding["codex_thread_id"] == "thread_123"
    assert binding["active_turn_id"] is None
