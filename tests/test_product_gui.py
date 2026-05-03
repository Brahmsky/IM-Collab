from __future__ import annotations

import json
from pathlib import Path

from bridge.product_gui import build_selected_session_view, build_workspace_view, create_product_gui_app


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_task(
    tasks_root: Path,
    task_id: str,
    state: str,
    summary: str,
    updated_at: str,
    items: list[dict],
) -> None:
    task_dir = tasks_root / task_id
    write_json(
        task_dir / "status.json",
        {
            "task_id": task_id,
            "state": state,
            "created_at": "2026-05-03T10:20:00+08:00",
            "updated_at": updated_at,
            "error": None,
        },
    )
    write_json(
        task_dir / "artifacts.json",
        {
            "task_id": task_id,
            "items": items,
            "summary": summary,
            "next_steps": [],
        },
    )
    (task_dir / "request.md").write_text(
        f"""# Request

session_key: feishu:oc_project:{task_id}
chat_id: oc_project
sender_id: ou_demo

## User Message
根据项目群聊整理第二周周报，并生成 PPT 大纲和回传消息。
""",
        encoding="utf-8",
    )


def test_workspace_view_groups_feishu_sessions_and_artifacts(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    make_task(
        tasks_root,
        "task-report",
        "running",
        "正在整理第二周周报材料",
        "2026-05-03T10:25:00+08:00",
        [
            {
                "id": "brief",
                "kind": "document",
                "title": "简报草稿",
                "path": "brief.md",
                "remote": {"url": "https://example.feishu/doc"},
            },
            {"id": "deck", "kind": "slides", "title": "PPT 大纲", "path": "deck.md"},
        ],
    )
    make_task(
        tasks_root,
        "task-review",
        "completed",
        "产品方案评审准备完成",
        "2026-05-02T18:00:00+08:00",
        [{"id": "reply", "kind": "text", "title": "回传消息草稿", "path": "reply.txt"}],
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_project:session-report": {
                "session_key": "feishu:oc_project:session-report",
                "chat_id": "oc_project",
                "chat_name": "项目答辩群",
                "session_title": "第二阶段汇报材料",
                "active_task_id": "task-report",
                "last_task_id": "task-report",
                "codex_thread_id": "thread_report",
                "active_turn_id": "turn_report",
            },
            "feishu:oc_project:session-review": {
                "session_key": "feishu:oc_project:session-review",
                "chat_id": "oc_project",
                "chat_name": "项目答辩群",
                "session_title": "产品方案评审准备",
                "active_task_id": None,
                "last_task_id": "task-review",
                "codex_thread_id": "thread_review",
                "active_turn_id": None,
            },
        },
    )

    view = build_workspace_view(tasks_root)

    assert view["groups"][0]["group_name"] == "项目答辩群"
    assert [session["title"] for session in view["groups"][0]["sessions"]] == [
        "第二阶段汇报材料",
        "产品方案评审准备",
    ]
    active = view["groups"][0]["sessions"][0]
    assert active["state"] == "running"
    assert active["artifact_count"] == 2
    assert view["selected_session_id"] == "feishu:oc_project:session-report"


def test_selected_session_view_and_gui_append_endpoint(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    make_task(
        tasks_root,
        "task-report",
        "running",
        "正在整理第二周周报材料",
        "2026-05-03T10:25:00+08:00",
        [{"id": "brief", "kind": "document", "title": "简报草稿", "path": "brief.md"}],
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_project:session-report": {
                "session_key": "feishu:oc_project:session-report",
                "chat_id": "oc_project",
                "chat_name": "项目答辩群",
                "session_title": "第二阶段汇报材料",
                "active_task_id": "task-report",
                "last_task_id": "task-report",
            }
        },
    )

    selected = build_selected_session_view(tasks_root, "feishu:oc_project:session-report")

    assert selected["title"] == "第二阶段汇报材料"
    assert selected["task_detail"]["task_id"] == "task-report"
    assert selected["user_request"].startswith("根据项目群聊整理第二周周报")
    assert selected["artifacts"][0]["title"] == "简报草稿"
    assert selected["execution_steps"][0]["label"].startswith("读取项目群聊上下文")

    app = create_product_gui_app(tasks_root)
    client = app.test_client()

    response = client.post(
        "/api/sessions/feishu%3Aoc_project%3Asession-report/messages",
        json={"text": "补充团队分工，并把 PPT 改成 5 分钟答辩版"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["command"]["type"] == "append_instruction"
    assert payload["command"]["payload"] == {
        "source": "gui",
        "kind": "operator_followup",
        "session_id": "feishu:oc_project:session-report",
        "text": "补充团队分工，并把 PPT 改成 5 分钟答辩版",
    }
