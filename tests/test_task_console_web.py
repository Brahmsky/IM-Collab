from __future__ import annotations

import json
from pathlib import Path

from bridge.task_console_web import handle_console_action, render_console_html


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_render_console_html_lists_tasks_and_controls(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "task-1" / "status.json",
        {
            "task_id": "task-1",
            "state": "running",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_group": {
                "session_key": "feishu:oc_group",
                "active_task_id": "task-1",
                "codex_thread_id": "thread_123",
                "active_turn_id": "turn_456",
            }
        },
    )
    (tasks_root / "task-1" / "control.jsonl").write_text(
        json.dumps({"type": "card_action", "payload": {"action": "start_task"}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    html = render_console_html(tasks_root, tmp_path / "events")

    assert "Agent-Pilot 办公助手" in html
    assert "task-1" in html
    assert "running" in html
    assert "tailwindcss.com" in html
    assert "thread_123" in html
    assert "turn_456" in html
    assert "最新操作" in html
    assert "card_action" in html
    assert 'name="action" value="append"' in html
    assert 'name="action" value="interrupt"' in html
    assert 'name="action" value="ack"' in html
    assert 'name="action" value="retry"' in html


def test_render_console_html_has_collapsible_session_groups_and_session_menu(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "task-1" / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_group": {
                "session_key": "feishu:oc_group",
                "chat_id": "oc_group",
                "chat_name": "项目群",
                "session_title": "第二阶段汇报材料",
                "last_task_id": "task-1",
            }
        },
    )

    html = render_console_html(tasks_root, tmp_path / "events")

    assert "<details" in html
    assert "<summary" in html
    assert "项目群" in html
    assert "第二阶段汇报材料" in html
    assert 'name="action" value="rename_session"' in html
    assert 'name="action" value="delete_session"' in html
    assert "more_vert" in html
    assert "session-rename-toggle" in html
    assert "session-rename-inline" in html
    assert 'data-session-group="项目群"' in html
    assert "im-collab-cockpit-open-groups" in html
    assert ">任务</div>" in html
    assert "groups" in html
    assert "edit" in html
    assert "delete" in html
    assert "保存</button>" not in html
    assert "取消</label>" not in html
    assert "onblur=\"this.form.requestSubmit()\"" in html
    assert "bg-primary rounded-l-full" not in html


def test_handle_console_action_appends_interrupts_and_acks(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"

    assert handle_console_action(tasks_root, {"action": "append", "task_id": "task-1", "text": "补充"}) == (
        "已为任务 task-1 追加指令"
    )
    assert handle_console_action(tasks_root, {"action": "interrupt", "task_id": "task-1"}) == (
        "已向任务 task-1 发送打断指令"
    )
    assert handle_console_action(tasks_root, {"action": "ack", "task_id": "task-1", "note": "已确认"}) == (
        "已确认任务 task-1"
    )

    commands = [
        json.loads(line)
        for line in (tasks_root / "task-1" / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert commands[0]["type"] == "append_instruction"
    assert commands[0]["payload"]["text"] == "补充"
    assert commands[1]["type"] == "interrupt"
    assert "已确认" in (tasks_root / "task-1" / "ack.json").read_text(encoding="utf-8")


def test_handle_console_action_retries_task(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    task_dir.mkdir(parents=True)
    seen: dict[str, object] = {}

    def fake_retry(task_dir_arg: Path, generator: str = "app-server", publish: bool = False):
        seen["task_dir"] = task_dir_arg
        seen["generator"] = generator
        seen["publish"] = publish
        return {"task_id": task_dir_arg.name}

    message = handle_console_action(
        tasks_root,
        {"action": "retry", "task_id": "task-1", "generator": "local", "publish": "1"},
        retry=fake_retry,
    )

    assert message == "已重新启动任务 task-1"
    assert seen == {"task_dir": task_dir, "generator": "local", "publish": True}


def test_handle_console_action_renames_and_archives_session(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "task-1" / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_group": {
                "session_key": "feishu:oc_group",
                "chat_id": "oc_group",
                "chat_name": "项目群",
                "last_task_id": "task-1",
            }
        },
    )

    assert handle_console_action(
        tasks_root,
        {
            "action": "rename_session",
            "task_id": "task-1",
            "session_key": "feishu:oc_group",
            "session_title": "预算材料整理",
        },
    ) == "已重命名会话 预算材料整理"

    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert bindings["feishu:oc_group"]["session_title"] == "预算材料整理"

    assert handle_console_action(
        tasks_root,
        {"action": "delete_session", "task_id": "task-1", "session_key": "feishu:oc_group"},
    ) == "已归档会话 task-1"

    assert not (tasks_root / "task-1").exists()
    assert (tasks_root / ".archived" / "task-1" / "status.json").exists()
    assert json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8")) == {}


def test_handle_console_action_renames_unbound_task_by_creating_local_session(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "task-1" / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )

    message = handle_console_action(
        tasks_root,
        {"action": "rename_session", "task_id": "task-1", "session_title": "本地整理任务"},
    )

    assert message == "已重命名会话 本地整理任务"
    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert bindings["local:task-1"]["last_task_id"] == "task-1"
    assert bindings["local:task-1"]["session_title"] == "本地整理任务"
