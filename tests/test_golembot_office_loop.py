from __future__ import annotations

import json
from pathlib import Path

from bridge.golembot_office_loop import run_golembot_office_task
from bridge.codex_app_server import CodexTurn
from bridge.task_binding import get_task_binding
from bridge.task_protocol import read_artifacts, read_status
from tests.test_codex_task_runner import write_codex_outputs


def _fake_evidence(messages, **kwargs):
    return [
        {
            "kind": "document_requirement",
            "claim": str(messages[0].get("content") or "群聊上下文") if messages else "群聊上下文",
            "source_message_ids": [str(messages[0].get("message_id") or "om_1")] if messages else ["om_1"],
            "confidence": "high",
            "extractor": "fake-langextract",
        }
    ]


class _WriteOutputsAppServerBackend:
    def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
        write_codex_outputs(task_dir)
        return CodexTurn(thread_id=thread_id or "thread_test", turn_id="turn_test")

    def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
        return {"id": turn_id, "status": "completed"}

    def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
        return {}

    def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
        return {}


def test_run_golembot_office_task_creates_task_and_returns_reply(tmp_path: Path) -> None:
    result = run_golembot_office_task(
        message="根据群聊生成项目方案、PPT 和白板",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-test-task",
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
    )

    task_dir = tmp_path / "gb-test-task"
    assert read_status(task_dir)["state"] == "completed"
    assert read_artifacts(task_dir)["task_id"] == "gb-test-task"
    assert result["reply_markdown"].startswith("你好，我是你的办公协作助手。")
    assert "相关材料已经整理好" in result["reply_markdown"]
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
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
        conversation_context=[
            {"message_id": "om_1", "sender_id": "ou_a", "content": "我们主打飞书群聊入口。"},
            {"message_id": "om_2", "sender_id": "ou_b", "content": "PPT 要突出多端协同。"},
        ],
        evidence_extractor=_fake_evidence,
    )

    request = (tmp_path / "group-task" / "request.md").read_text(encoding="utf-8")
    assert "## Conversation Context" in request
    assert "我们主打飞书群聊入口。" in request
    assert "PPT 要突出多端协同。" in request


def test_run_golembot_office_task_persists_last_absorbed_group_message_boundary(tmp_path: Path) -> None:
    run_golembot_office_task(
        message="根据刚才讨论生成方案和 PPT",
        session_key="feishu:oc_group:session:om_new",
        chat_id="oc_group",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="group-boundary-task",
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
        conversation_context=[
            {"message_id": "om_1", "sender_id": "ou_a", "content": "我们主打飞书群聊入口。"},
            {"message_id": "om_2", "sender_id": "ou_b", "content": "PPT 要突出多端协同。"},
        ],
        absorbed_message_id="om_trigger",
        evidence_extractor=_fake_evidence,
    )

    binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_group:session:om_new")
    assert binding["last_absorbed_message_id"] == "om_trigger"


def test_run_golembot_office_task_writes_source_grounded_group_brief(tmp_path: Path) -> None:
    run_golembot_office_task(
        message="根据刚才讨论生成方案和 PPT",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="brief-task",
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
        conversation_context=[
            {
                "message_id": "om_1",
                "sender_id": "teacher",
                "sent_at": "2026-04-28T10:00:00+08:00",
                "content": "周五 18:00 前提交项目方案和 PPT。",
            },
            {"message_id": "om_2", "sender_id": "ou_a", "content": "PPT 控制在 8 页，文档用 Markdown。"},
        ],
        evidence_extractor=_fake_evidence,
    )

    task_dir = tmp_path / "brief-task"
    brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8"))
    brief_markdown = (task_dir / "brief.md").read_text(encoding="utf-8")
    request = (task_dir / "request.md").read_text(encoding="utf-8")

    assert brief["chat_id"] == "oc_group"
    assert brief["annotations"]
    assert all(annotation["evidence_message_ids"] for annotation in brief["annotations"])
    assert "[om_1]" in brief_markdown
    assert "brief.json" in request
    assert "brief.md" in request


def test_run_golembot_office_task_can_use_selected_langextract_brief_backend(tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_evidence_extractor(messages, **kwargs):
        seen["message_ids"] = [message["message_id"] for message in messages]
        seen["kwargs"] = kwargs
        return [
            {
                "kind": "deadline",
                "claim": "正式截止为 4 月 28 日 20:00",
                "source_message_ids": ["om_formal"],
                "confidence": "high",
                "extractor": "fake-langextract",
            }
        ]

    run_golembot_office_task(
        message="根据刚才讨论生成材料 brief",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="langextract-brief-task",
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
        conversation_context=[
            {"message_id": "om_noise", "sender_id": "ou_a", "content": "闲聊"},
            {"message_id": "om_formal", "sender_id": "teacher", "content": "正式通知：4 月 28 日 20:00 截止。", "tags": ["formal_notice", "deadline"]},
        ],
        brief_extractor="langextract-deepseek",
        brief_api_key="sk-test",
        evidence_extractor=fake_evidence_extractor,
    )

    task_dir = tmp_path / "langextract-brief-task"
    brief = json.loads((task_dir / "brief.json").read_text(encoding="utf-8"))
    evidence = json.loads((task_dir / "evidence.json").read_text(encoding="utf-8"))

    assert seen["message_ids"] == ["om_noise", "om_formal"]
    assert seen["kwargs"]["api_key"] == "sk-test"
    assert brief["annotations"][0]["annotation_id"] == "lx_001"
    assert brief["annotations"][0]["claim"] == "正式截止为 4 月 28 日 20:00"
    assert evidence["evidence"][0]["extractor"] == "fake-langextract"


def test_run_golembot_office_task_waits_for_user_when_external_brief_has_conflicts(tmp_path: Path) -> None:
    def fake_evidence_extractor(messages, **kwargs):
        return [
            {
                "kind": "conflict",
                "claim": "页数要求存在冲突，需要人工确认。",
                "source_message_ids": ["om_1", "om_2"],
                "confidence": "medium",
                "extractor": "fake-langextract",
            }
        ]

    result = run_golembot_office_task(
        message="根据刚才讨论生成方案和 PPT",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="waiting-brief-task",
        publish=False,
        conversation_context=[
            {"message_id": "om_1", "sender_id": "teacher", "content": "PPT 不超过 8 页。"},
            {"message_id": "om_2", "sender_id": "ou_a", "content": "我记得 PPT 可以 10 页？"},
        ],
        brief_extractor="langextract-deepseek",
        evidence_extractor=fake_evidence_extractor,
    )

    task_dir = tmp_path / "waiting-brief-task"
    status = read_status(task_dir)

    assert status["state"] == "waiting_for_user"
    assert "需要确认" in status["error"]
    assert not (task_dir / "artifacts.json").exists()
    assert (task_dir / "confirmation.md").exists()
    card = json.loads((task_dir / "confirmation_card.json").read_text(encoding="utf-8"))
    assert card["header"]["title"]["content"] == "请确认群聊需求"
    assert card["elements"][-2]["value"] == {
        "action": "start_task",
        "task_id": "waiting-brief-task",
        "session_key": "feishu:oc_group",
    }
    assert "页数要求存在冲突" in result["reply_markdown"]
    assert result["state"] == "waiting_for_user"


def test_run_golembot_office_task_publish_requires_direct_feishu_remote_artifacts(tmp_path: Path) -> None:
    try:
        run_golembot_office_task(
            message="生成项目方案",
            session_key="feishu:oc_123",
            chat_id="oc_123",
            sender_id="ou_456",
            tasks_root=tmp_path,
            task_id="gb-publish-task",
            generator="app-server",
            publish=True,
            codex_backend=_WriteOutputsAppServerBackend(),
        )
    except Exception as exc:
        assert "no Feishu remote artifacts found" in str(exc)
    else:
        raise AssertionError("expected publish path to reject local-only artifacts")


def test_run_golembot_office_task_fails_when_publish_requested_but_no_feishu_remote_artifacts_exist(tmp_path: Path) -> None:
    class FakeAppServerBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            (task_dir / "plan.json").write_text('{"task_id":"gb-publish-fail","steps":[]}\n', encoding="utf-8")
            (task_dir / "artifacts.json").write_text(
                json.dumps(
                    {
                        "task_id": "gb-publish-fail",
                        "items": [
                            {"id": "plan", "kind": "plan", "type": "json", "path": (task_dir / "plan.json").as_posix()}
                        ],
                        "summary": "只有本地文件。",
                        "next_steps": [],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            return CodexTurn(thread_id=thread_id or "thread_123", turn_id="turn_456")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            return {"id": turn_id, "status": "completed"}

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            return {}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            return {}

    try:
        run_golembot_office_task(
            message="生成项目方案",
            session_key="feishu:oc_123",
            chat_id="oc_123",
            sender_id="ou_456",
            tasks_root=tmp_path,
            task_id="gb-publish-fail",
            generator="app-server",
            publish=True,
            codex_backend=FakeAppServerBackend(),
            runner=lambda *_args, **_kwargs: json.dumps({"ok": True, "data": {}}),
        )
    except Exception as exc:
        assert "no publishable artifact items found" in str(exc) or "no Feishu remote artifacts" in str(exc)
    else:
        raise AssertionError("expected publish-time remote artifact validation to fail")


def test_run_golembot_office_task_can_use_app_server_generator(tmp_path: Path) -> None:
    class FakeAppServerBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            write_codex_outputs(task_dir)
            return CodexTurn(thread_id=thread_id or "thread_123", turn_id="turn_456")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            return {"id": turn_id, "status": "completed"}

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            seen["steered_text"] = text
            return {}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            return {}

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


def test_run_golembot_office_task_reuses_existing_app_server_thread(tmp_path: Path) -> None:
    seen: dict[str, str | None] = {}

    class FakeAppServerBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            seen["thread_id"] = thread_id
            write_codex_outputs(task_dir)
            return CodexTurn(thread_id=thread_id or "new_thread", turn_id="turn_followup")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            return {"id": turn_id, "status": "completed"}

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            seen["steered_text"] = text
            return {}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            return {}

    run_golembot_office_task(
        message="生成项目方案",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-initial-task",
        publish=False,
        codex_backend=FakeAppServerBackend(),
    )

    run_golembot_office_task(
        message="把刚才的 PPT 改成 5 分钟答辩版",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-followup-task",
        publish=False,
        codex_backend=FakeAppServerBackend(),
    )

    binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
    assert seen["thread_id"] == "new_thread"
    assert binding["codex_thread_id"] == "new_thread"


def test_run_golembot_office_task_clears_active_binding_after_failure(tmp_path: Path) -> None:
    class FailingBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            return CodexTurn(thread_id="thread_fail", turn_id="turn_fail")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            raise RuntimeError("boom")

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            return {}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            return {}

    try:
        run_golembot_office_task(
            message="生成项目方案",
            session_key="feishu:oc_123",
            chat_id="oc_123",
            sender_id="ou_456",
            tasks_root=tmp_path,
            task_id="gb-failed-task",
            generator="app-server",
            publish=False,
            codex_backend=FailingBackend(),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")

    binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
    assert binding["active_task_id"] is None
    assert binding["last_task_id"] == "gb-failed-task"
    assert read_status(tmp_path / "gb-failed-task")["state"] == "failed"


def test_completed_task_with_new_control_runs_codex_again_on_same_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "gb-followup-existing-task"
    task_dir.mkdir(parents=True)
    (task_dir / "request.md").write_text(
        "session_key: feishu:oc_123\nchat_id: oc_123\nsender_id: ou_456\n\n## User Message\n生成项目方案\n",
        encoding="utf-8",
    )
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": task_dir.name,
                "state": "completed",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": None,
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "artifacts.json").write_text(
        json.dumps(
            {
                "task_id": task_dir.name,
                "summary": "旧材料",
                "next_steps": [],
                "items": [{"id": "document", "kind": "document", "path": "document.md"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (task_dir / "document.md").write_text("旧材料\n", encoding="utf-8")
    (task_dir / "control.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-04-28T01:02:00+00:00",
                "type": "append_instruction",
                "operator": "gui",
                "payload": {"source": "gui", "kind": "operator_followup", "text": "补充团队分工。"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    seen: dict[str, str | None] = {}

    class FakeAppServerBackend:
        def start_task(self, task_dir_arg: Path, thread_id: str | None = None) -> CodexTurn:
            seen["task_dir"] = task_dir_arg.name
            seen["thread_id"] = thread_id
            write_codex_outputs(task_dir_arg)
            return CodexTurn(thread_id=thread_id or "thread_followup", turn_id="turn_followup")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            return {"id": turn_id, "status": "completed"}

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            seen["steered_text"] = text
            return {}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            return {}

    run_golembot_office_task(
        message="补充团队分工。",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id=task_dir.name,
        generator="app-server",
        publish=False,
        codex_backend=FakeAppServerBackend(),
    )

    assert seen["task_dir"] == task_dir.name
    assert "steered_text" not in seen
    assert read_status(task_dir)["state"] == "completed"


def test_run_golembot_office_task_exposes_active_turn_while_app_server_runs(tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    class FakeAppServerBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            return CodexTurn(thread_id="thread_live", turn_id="turn_live")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            observed["binding_during_wait"] = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
            write_codex_outputs(tmp_path / "gb-live-turn-task")
            return {"id": turn_id, "status": "completed"}

    run_golembot_office_task(
        message="生成项目方案",
        session_key="feishu:oc_123",
        chat_id="oc_123",
        sender_id="ou_456",
        tasks_root=tmp_path,
        task_id="gb-live-turn-task",
        generator="app-server",
        publish=False,
        codex_backend=FakeAppServerBackend(),
    )

    binding_during_wait = observed["binding_during_wait"]
    final_binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
    assert binding_during_wait["codex_thread_id"] == "thread_live"
    assert binding_during_wait["active_turn_id"] == "turn_live"
    assert final_binding["codex_thread_id"] == "thread_live"
    assert final_binding["active_turn_id"] is None


def test_run_golembot_office_task_clears_active_binding_when_app_server_fails(tmp_path: Path) -> None:
    class FakeAppServerBackend:
        def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            return CodexTurn(thread_id="thread_live", turn_id="turn_live")

        def wait_for_task(self, thread_id: str, turn_id: str) -> dict:
            raise RuntimeError("codex turn failed")

    try:
        run_golembot_office_task(
            message="生成项目方案",
            session_key="feishu:oc_123",
            chat_id="oc_123",
            sender_id="ou_456",
            tasks_root=tmp_path,
            task_id="gb-failed-turn-task",
            generator="app-server",
            publish=False,
            codex_backend=FakeAppServerBackend(),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected run_golembot_office_task to raise")

    binding = get_task_binding(tmp_path / "task-bindings.json", "feishu:oc_123")
    status = read_status(tmp_path / "gb-failed-turn-task")
    assert status["state"] == "failed"
    assert binding["active_task_id"] is None
    assert binding["active_turn_id"] is None
    assert binding["last_task_id"] == "gb-failed-turn-task"


def test_resumed_waiting_task_includes_natural_language_controls_in_request(tmp_path: Path) -> None:
    task_dir = tmp_path / "waiting-task"
    task_dir.mkdir(parents=True)
    (task_dir / "request.md").write_text("# Existing request\n", encoding="utf-8")
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "waiting-task",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "control.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-04-28T01:00:30+00:00",
                "type": "append_instruction",
                "operator": "feishu",
                "payload": {"text": "补充：PPT 按 8 页做，移动端同步也要写进验收。"},
            },
            ensure_ascii=False,
        )
        + "\n"
        +
        json.dumps(
            {
                "timestamp": "2026-04-28T01:01:00+00:00",
                "type": "card_action",
                "operator": "feishu_card",
                "payload": {"action": "start_task", "value": {"task_id": "waiting-task"}},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    run_golembot_office_task(
        message="开始执行",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_requester",
        tasks_root=tmp_path,
        task_id="waiting-task",
        generator="app-server",
        publish=False,
        codex_backend=_WriteOutputsAppServerBackend(),
    )

    request = (task_dir / "request.md").read_text(encoding="utf-8")
    assert "## Confirmation Controls" in request
    assert "append_instruction" in request
    assert "PPT 按 8 页做" in request
    assert "card_action" in request
    assert "start_task" in request
