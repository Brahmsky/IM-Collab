from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest


TASK_ID = "task-contract-1"
SESSION_KEY = "feishu:oc_demo"
SESSION_TITLE = "答辩材料整理"

EXPECTED_TASK_SUMMARY = {
    "task_id": TASK_ID,
    "state": "running",
    "created_at": "2026-05-05T08:00:00+00:00",
    "updated_at": "2026-05-05T08:03:00+00:00",
    "summary": "已整理群聊并准备生成答辩材料。",
    "session_key": SESSION_KEY,
    "session_title": SESSION_TITLE,
    "chat_name": "项目答辩群",
    "chat_id": "oc_demo",
    "codex_thread_id": "thread_123",
    "artifact_outputs": [
        ["项目方案", "https://docs.example.com/doc_123"],
        ["答辩 PPT", "https://slides.example.com/slide_123"],
        ["流程白板", "https://docs.example.com/doc_123#whiteboard"],
    ],
}

EXPECTED_CHAT_MESSAGES = [
    {
        "timestamp": "2026-05-05T08:00:00+00:00",
        "role": "user",
        "text": "请根据群聊整理答辩材料并生成文档、PPT、白板。",
        "source": "request",
    },
    {
        "timestamp": "2026-05-05T08:02:00+00:00",
        "role": "assistant",
        "text": "收到，先整理答辩结构，再生成交付物。",
        "source": "artifacts",
    },
]

EXPECTED_CONTROL_COMMANDS = [
    {
        "timestamp": "2026-05-05T08:04:00+00:00",
        "type": "append_instruction",
        "operator": "gui",
        "payload": {
            "source": "gui",
            "kind": "operator_followup",
            "text": "补充竞品对比和预算风险。",
        },
    },
    {
        "timestamp": "2026-05-05T08:05:00+00:00",
        "type": "interrupt",
        "payload": {},
    },
]

EXPECTED_ARTIFACTS = {
    "task_id": TASK_ID,
    "summary": "已整理群聊并准备生成答辩材料。",
    "next_steps": ["确认最终页数", "补充预算表"],
    "items": [
        {
            "id": "proposal",
            "kind": "document",
            "title": "项目方案",
            "remote": {
                "provider": "feishu",
                "url": "https://docs.example.com/doc_123",
                "document_id": "doc_123",
            },
        },
        {
            "id": "deck",
            "kind": "slides",
            "title": "答辩 PPT",
            "remote": {
                "provider": "feishu",
                "url": "https://slides.example.com/slide_123",
                "xml_presentation_id": "slide_123",
            },
        },
        {
            "id": "board",
            "kind": "whiteboard",
            "title": "流程白板",
            "remote": {
                "provider": "feishu",
                "url": "https://docs.example.com/doc_123#whiteboard",
                "whiteboard_token": "wb_123",
            },
        },
    ],
}

EXPECTED_CURRENT_TURN_ARTIFACTS = [
    {
        "id": "proposal",
        "kind": "document",
        "title": "项目方案",
        "label": "项目方案",
        "path": None,
        "remote": {
            "provider": "feishu",
            "url": "https://docs.example.com/doc_123",
            "document_id": "doc_123",
        },
        "url": "https://docs.example.com/doc_123",
        "clickable": True,
        "source_task_id": TASK_ID,
    },
    {
        "id": "deck",
        "kind": "slides",
        "title": "答辩 PPT",
        "label": "答辩 PPT",
        "path": None,
        "remote": {
            "provider": "feishu",
            "url": "https://slides.example.com/slide_123",
            "xml_presentation_id": "slide_123",
        },
        "url": "https://slides.example.com/slide_123",
        "clickable": True,
        "source_task_id": TASK_ID,
    },
    {
        "id": "board",
        "kind": "whiteboard",
        "title": "流程白板",
        "label": "流程白板",
        "path": None,
        "remote": {
            "provider": "feishu",
            "url": "https://docs.example.com/doc_123#whiteboard",
            "whiteboard_token": "wb_123",
        },
        "url": "https://docs.example.com/doc_123#whiteboard",
        "clickable": True,
        "source_task_id": TASK_ID,
    },
]

EXPECTED_SESSION_ARTIFACTS = [
    *EXPECTED_CURRENT_TURN_ARTIFACTS,
    {
        "id": "meeting-notes",
        "kind": "document",
        "title": "会前纪要",
        "label": "会前纪要",
        "path": None,
        "remote": {
            "provider": "feishu",
            "url": "https://docs.example.com/doc_122",
            "document_id": "doc_122",
        },
        "url": "https://docs.example.com/doc_122",
        "clickable": True,
        "source_task_id": "task-contract-0",
    },
    {
        "id": "history-board",
        "kind": "whiteboard",
        "title": "历史流程白板",
        "label": "历史流程白板",
        "path": None,
        "remote": {
            "provider": "feishu",
            "label": "历史流程白板",
            "whiteboard_token": "wb_122",
        },
        "url": None,
        "clickable": False,
        "source_task_id": "task-contract-0",
    },
]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8")


def _json(response: Any) -> dict[str, Any]:
    data = response.get_json()
    if isinstance(data, dict):
        return data
    return json.loads(response.get_data(as_text=True))


def _load_test_client(
    tasks_root: Path,
    event_dir: Path,
    *,
    app_server_retry: Any | None = None,
    run_followup_in_background: bool = False,
) -> Any:
    try:
        module = importlib.import_module("bridge.server_app")
    except Exception as exc:  # pragma: no cover - intentional failure until T4 exists
        pytest.fail(
            "Implement `bridge.server_app.create_app(tasks_root, event_dir)` for the JSON API contract tests. "
            f"Original import error: {exc}",
            pytrace=False,
        )
    create_app = getattr(module, "create_app", None)
    if not callable(create_app):  # pragma: no cover - intentional failure until T4 exists
        pytest.fail("`bridge.server_app.create_app` must be callable.", pytrace=False)
    app = create_app(
        tasks_root=tasks_root,
        event_dir=event_dir,
        app_server_retry=app_server_retry,
        run_followup_in_background=run_followup_in_background,
    )
    test_client = getattr(app, "test_client", None)
    if not callable(test_client):  # pragma: no cover - intentional failure until T4 exists
        pytest.fail("`bridge.server_app.create_app()` must return an app with `.test_client()`.", pytrace=False)
    if hasattr(app, "config") and isinstance(app.config, dict):
        app.config["TESTING"] = True
    return test_client()


@pytest.fixture()
def contract_workspace(tmp_path: Path) -> dict[str, Any]:
    tasks_root = tmp_path / "tasks"
    event_dir = tmp_path / "events"
    task_dir = tasks_root / TASK_ID
    previous_task_dir = tasks_root / "task-contract-0"

    _write_json(
        task_dir / "status.json",
        {
            "task_id": TASK_ID,
            "state": "running",
            "created_at": "2026-05-05T08:00:00+00:00",
            "updated_at": "2026-05-05T08:03:00+00:00",
            "error": None,
        },
    )
    _write_json(task_dir / "artifacts.json", EXPECTED_ARTIFACTS)
    _write_json(
        previous_task_dir / "status.json",
        {
            "task_id": "task-contract-0",
            "state": "completed",
            "created_at": "2026-05-05T07:30:00+00:00",
            "updated_at": "2026-05-05T07:50:00+00:00",
            "error": None,
        },
    )
    _write_json(
        previous_task_dir / "artifacts.json",
        {
            "task_id": "task-contract-0",
            "summary": "已产出会前纪要和早期白板。",
            "next_steps": [],
            "items": [
                {
                    "id": "meeting-notes",
                    "kind": "document",
                    "title": "会前纪要",
                    "remote": {
                        "provider": "feishu",
                        "url": "https://docs.example.com/doc_122",
                        "document_id": "doc_122",
                    },
                },
                {
                    "id": "history-board",
                    "kind": "whiteboard",
                    "title": "历史流程白板",
                    "remote": {
                        "provider": "feishu",
                        "label": "历史流程白板",
                        "whiteboard_token": "wb_122",
                    },
                },
            ],
        },
    )
    _write_json(
        tasks_root / "task-other" / "status.json",
        {
            "task_id": "task-other",
            "state": "completed",
            "created_at": "2026-05-05T07:00:00+00:00",
            "updated_at": "2026-05-05T07:10:00+00:00",
            "error": None,
        },
    )
    _write_json(
        tasks_root / "task-other" / "artifacts.json",
        {
            "task_id": "task-other",
            "summary": "其他会话的材料。",
            "next_steps": [],
            "items": [
                {
                    "id": "other-doc",
                    "kind": "document",
                    "title": "其他会话文档",
                    "remote": {
                        "provider": "feishu",
                        "url": "https://docs.example.com/doc_other",
                        "document_id": "doc_other",
                    },
                }
            ],
        },
    )
    _write_jsonl(task_dir / "chat_messages.jsonl", EXPECTED_CHAT_MESSAGES)
    _write_jsonl(task_dir / "control.jsonl", EXPECTED_CONTROL_COMMANDS)
    _write_json(
        tasks_root / "task-bindings.json",
        {
            SESSION_KEY: {
                "session_key": SESSION_KEY,
                "session_title": SESSION_TITLE,
                "chat_name": "项目答辩群",
                "chat_id": "oc_demo",
                "codex_thread_id": "thread_123",
                "active_turn_id": "turn_456",
                "active_task_id": TASK_ID,
                "last_task_id": TASK_ID,
            },
            f"{SESSION_KEY}:history": {
                "session_key": SESSION_KEY,
                "session_title": SESSION_TITLE,
                "chat_name": "项目答辩群",
                "chat_id": "oc_demo",
                "codex_thread_id": "thread_122",
                "active_turn_id": None,
                "active_task_id": None,
                "last_task_id": "task-contract-0",
            },
            "feishu:oc_other": {
                "session_key": "feishu:oc_other",
                "session_title": "其他会话",
                "chat_name": "其他群聊",
                "chat_id": "oc_other",
                "codex_thread_id": "thread_other",
                "active_turn_id": None,
                "active_task_id": None,
                "last_task_id": "task-other",
            },
        },
    )
    _write_json(event_dir / "im.message.receive_v1_20260505_a.json", {"event": "a"})
    _write_json(event_dir / "im.message.receive_v1_20260505_b.json", {"event": "b"})

    return {
        "tasks_root": tasks_root,
        "event_dir": event_dir,
        "task_id": TASK_ID,
        "session_key": SESSION_KEY,
    }


@pytest.fixture()
def client(contract_workspace: dict[str, Any]) -> Any:
    return _load_test_client(
        contract_workspace["tasks_root"],
        contract_workspace["event_dir"],
        app_server_retry=lambda task_dir, publish=False: {"task_id": task_dir.name, "publish": publish},
    )


def test_get_tasks_returns_task_summaries_and_event_overview(client: Any) -> None:
    response = client.get("/api/tasks")

    assert response.status_code == 200
    payload = _json(response)
    assert payload == {
        "tasks": payload["tasks"],
        "events": {
            "total": 2,
            "latest_files": [
                "im.message.receive_v1_20260505_b.json",
                "im.message.receive_v1_20260505_a.json",
            ],
        },
    }
    assert [task["task_id"] for task in payload["tasks"]] == [TASK_ID, "task-contract-0", "task-other"]
    assert payload["tasks"][0] == EXPECTED_TASK_SUMMARY


def test_get_task_detail_returns_messages_controls_artifacts_and_pending_flag(client: Any) -> None:
    response = client.get(f"/api/tasks/{TASK_ID}")

    assert response.status_code == 200
    assert _json(response) == {
        "task": EXPECTED_TASK_SUMMARY,
        "chat_messages": EXPECTED_CHAT_MESSAGES,
        "control_commands": EXPECTED_CONTROL_COMMANDS,
        "artifacts": EXPECTED_ARTIFACTS,
        "current_turn_artifacts": EXPECTED_CURRENT_TURN_ARTIFACTS,
        "session_artifacts": EXPECTED_SESSION_ARTIFACTS,
        "pending_controls": True,
    }


def test_get_task_returns_404_for_missing_task(client: Any) -> None:
    response = client.get("/api/tasks/missing-task")

    assert response.status_code == 404
    assert _json(response) == {"ok": False, "error": "task not found"}


def test_post_append_returns_stream_url_for_followup_stream(client: Any) -> None:
    response = client.post(
        f"/api/tasks/{TASK_ID}/append",
        json={"text": "补充预算风险和答辩时长限制。"},
    )

    assert response.status_code == 200
    assert _json(response) == {
        "ok": True,
        "backend": "active_turn",
        "task_id": TASK_ID,
        "stream_url": f"/api/tasks/{TASK_ID}/stream",
    }


def test_post_append_triggers_app_server_retry_for_completed_followup(contract_workspace: dict[str, Any]) -> None:
    task_dir = contract_workspace["tasks_root"] / TASK_ID
    _write_json(
        task_dir / "status.json",
        {
            "task_id": TASK_ID,
            "state": "completed",
            "created_at": "2026-05-05T08:00:00+00:00",
            "updated_at": "2026-05-05T08:03:00+00:00",
            "error": None,
        },
    )
    seen: list[tuple[str, bool]] = []

    def fake_app_server_retry(task_dir_arg: Path, publish: bool = False) -> dict[str, Any]:
        seen.append((task_dir_arg.name, publish))
        return {"task_id": task_dir_arg.name}

    client = _load_test_client(
        contract_workspace["tasks_root"],
        contract_workspace["event_dir"],
        app_server_retry=fake_app_server_retry,
    )

    response = client.post(
        f"/api/tasks/{TASK_ID}/append",
        json={"text": "补充预算风险和答辩时长限制。"},
    )

    assert response.status_code == 200
    assert _json(response) == {
        "ok": True,
        "backend": "codex_app_server",
        "task_id": TASK_ID,
        "stream_url": f"/api/tasks/{TASK_ID}/stream",
    }
    assert seen == [(TASK_ID, False)]


def test_post_append_rejects_missing_task_id(client: Any) -> None:
    response = client.post(
        f"/api/tasks/{quote(' ', safe='')}/append",
        json={"text": "补充预算风险和答辩时长限制。"},
    )

    assert response.status_code == 400
    assert _json(response) == {"ok": False, "error": "missing task_id"}


def test_post_append_rejects_missing_text(client: Any) -> None:
    response = client.post(f"/api/tasks/{TASK_ID}/append", json={})

    assert response.status_code == 400
    assert _json(response) == {"ok": False, "error": "missing field: text"}


def test_post_interrupt_returns_ok(client: Any) -> None:
    response = client.post(f"/api/tasks/{TASK_ID}/interrupt", json={})

    assert response.status_code == 200
    assert _json(response) == {"ok": True}


def test_post_ack_returns_ok_and_accepts_optional_note(client: Any) -> None:
    response = client.post(f"/api/tasks/{TASK_ID}/ack", json={"note": "已人工确认，请继续执行。"})

    assert response.status_code == 200
    assert _json(response) == {"ok": True}


def test_post_retry_returns_generator_and_accepts_publish_flag(client: Any) -> None:
    response = client.post(f"/api/tasks/{TASK_ID}/retry", json={"publish": True})

    assert response.status_code == 200
    assert _json(response) == {"ok": True, "generator": "app-server", "backend": "codex_app_server"}


def test_post_session_rename_returns_ok_and_accepts_session_title(client: Any) -> None:
    response = client.post(
        f"/api/sessions/{quote(SESSION_KEY, safe='')}/rename",
        json={"session_title": "更新后的答辩材料整理"},
    )

    assert response.status_code == 200
    assert _json(response) == {"ok": True}


def test_delete_session_returns_ok(client: Any) -> None:
    response = client.delete(f"/api/sessions/{quote(SESSION_KEY, safe='')}")

    assert response.status_code == 200
    assert _json(response) == {"ok": True}
