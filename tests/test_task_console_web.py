from __future__ import annotations

import json
from pathlib import Path

from bridge.cockpit_console_html import _relative_time_display
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
    (tasks_root / "task-1" / "request.md").write_text(
        "session_key: feishu:oc_group\n"
        "chat_id: oc_group\n"
        "sender_id: ou_user\n\n"
        "## User Message\n"
        "请根据项目群整理第二阶段材料，并生成 PPT 大纲。\n",
        encoding="utf-8",
    )
    (tasks_root / "task-1" / "control.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-04-29T01:00:00+00:00",
                "type": "append_instruction",
                "operator": "operator",
                "payload": {
                    "source": "gui",
                    "kind": "operator_followup",
                    "text": "补充团队分工说明。",
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_json(
        tasks_root / "task-2" / "status.json",
        {
            "task_id": "task-2",
            "state": "completed",
            "created_at": "2026-04-27T01:00:00+00:00",
            "updated_at": "2026-04-27T01:00:00+00:00",
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
            },
            "feishu:oc_group:review": {
                "session_key": "feishu:oc_group:review",
                "chat_id": "oc_group",
                "chat_name": "项目群",
                "session_title": "产品方案评审准备",
                "last_task_id": "task-2",
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
    assert ">group</span>" in html
    assert "border-l border-border" in html
    assert "session-time" in html
    assert "group-hover:hidden group-focus-within:hidden" in html
    assert '<h2 class="text-[16px] font-semibold text-text-primary truncate">第二阶段汇报材料</h2>' in html
    assert 'data-role="chat-message-user"' in html
    assert 'data-role="chat-message-assistant"' in html
    assert 'data-role="pending-reply-marker"' in html
    assert "请根据项目群整理第二阶段材料，并生成 PPT 大纲。" in html
    assert "补充团队分工说明。" in html
    assert "待回复" in html
    assert "已完成当前任务" not in html
    assert html.index("请根据项目群整理第二阶段材料，并生成 PPT 大纲。") < html.index("补充团队分工说明。")
    assert "smart_toy" in html
    assert "收到，正在为你梳理并生成相关材料" not in html
    assert '<select name="generator"' not in html
    assert "发布到飞书" not in html
    assert ">local</option>" not in html
    assert "打断" not in html
    assert "确认备注" not in html
    assert "执行补充" in html
    assert 'data-submit-on-enter="true"' in html
    assert 'data-async-append="true"' in html
    assert 'data-chat-scroll-container="true"' in html
    assert "fetch(form.action || window.location.href" in html
    assert "event.preventDefault()" in html
    assert "insertAdjacentHTML(\"beforeend\"" in html
    assert "chat.scrollTop = chat.scrollHeight" in html
    assert "new EventSource" in html
    assert "/api/task-stream?task=" in html
    assert "requestSubmit()" in html
    assert "event.shiftKey" in html
    assert "edit" in html
    assert "delete" in html
    assert "保存</button>" not in html
    assert "取消</label>" not in html
    assert "onblur=\"this.form.requestSubmit()\"" in html
    assert "bg-primary rounded-l-full" not in html


def test_render_console_html_searches_human_session_fields_and_artifacts(tmp_path: Path) -> None:
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
        tasks_root / "task-1" / "artifacts.json",
        {
            "task_id": "task-1",
            "summary": "生成经费申请材料",
            "next_steps": [],
            "items": [{"id": "budget", "kind": "document", "path": "tasks/task-1/budget.md", "title": "经费预算表"}],
        },
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_budget": {
                "session_key": "feishu:oc_budget",
                "chat_id": "oc_budget",
                "chat_name": "经费申请群",
                "session_title": "预算材料整理",
                "last_task_id": "task-1",
            }
        },
    )

    assert "预算材料整理" in render_console_html(tasks_root, tmp_path / "events", search_query="预算")
    assert "经费申请群" in render_console_html(tasks_root, tmp_path / "events", search_query="经费申请")
    assert "经费预算表" in render_console_html(tasks_root, tmp_path / "events", search_query="预算表")


def test_render_console_html_does_not_expose_clickable_fake_sidebar_links(tmp_path: Path) -> None:
    html = render_console_html(tmp_path / "tasks", tmp_path / "events")

    assert 'href="#"' not in html
    assert "MVP" not in html
    assert "demo" not in html.lower()
    assert "尚未接入" not in html
    assert "python scripts/" not in html


def test_handle_console_action_appends_interrupts_and_acks(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"

    assert handle_console_action(tasks_root, {"action": "append", "task_id": "task-1", "text": "补充"}) == ""
    assert handle_console_action(tasks_root, {"action": "interrupt", "task_id": "task-1"}) == ""
    assert handle_console_action(tasks_root, {"action": "ack", "task_id": "task-1", "note": "已确认"}) == ""

    commands = [
        json.loads(line)
        for line in (tasks_root / "task-1" / "control.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert commands[0]["type"] == "append_instruction"
    assert commands[0]["payload"]["text"] == "补充"
    assert commands[0]["payload"]["source"] == "gui"
    assert commands[0]["payload"]["kind"] == "operator_followup"
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

    assert message == ""
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
    ) == ""

    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert bindings["feishu:oc_group"]["session_title"] == "预算材料整理"

    assert handle_console_action(
        tasks_root,
        {"action": "delete_session", "task_id": "task-1", "session_key": "feishu:oc_group"},
    ) == ""

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

    assert message == ""
    bindings = json.loads((tasks_root / "task-bindings.json").read_text(encoding="utf-8"))
    assert bindings["local:task-1"]["last_task_id"] == "task-1"
    assert bindings["local:task-1"]["session_title"] == "本地整理任务"


def test_relative_time_display_has_only_four_user_facing_buckets() -> None:
    assert _relative_time_display("2026-05-04T11:59:40+08:00", now_iso="2026-05-04T12:00:00+08:00") == "刚刚"
    assert _relative_time_display("2026-05-04T11:30:00+08:00", now_iso="2026-05-04T12:00:00+08:00") == "30 分钟前"
    assert _relative_time_display("2026-05-04T09:00:00+08:00", now_iso="2026-05-04T12:00:00+08:00") == "3 小时前"
    assert _relative_time_display("2026-05-01T12:00:00+08:00", now_iso="2026-05-04T12:00:00+08:00") == "3 天前"
