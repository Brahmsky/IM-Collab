from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest


TASK_ID = "stream-contract-1"

EXPECTED_ARTIFACTS = {
    "task_id": TASK_ID,
    "summary": "交付物已生成，可以回传群聊。",
    "next_steps": ["发送飞书卡片"],
    "items": [
        {
            "id": "proposal",
            "kind": "document",
            "title": "项目方案",
            "remote": {
                "provider": "feishu",
                "url": "https://docs.example.com/doc_456",
                "document_id": "doc_456",
            },
        }
    ],
}

EXPECTED_CURRENT_TURN_ARTIFACTS = [
    {
        "id": "proposal",
        "family": "document",
        "kind": "document",
        "title": "项目方案",
        "input": None,
        "output": {
            "provider": "feishu",
            "url": "https://docs.example.com/doc_456",
            "document_id": "doc_456",
            "object_type": "document",
        },
        "display": {
            "card_kind": "document",
            "label": "项目方案",
            "click_url": "https://docs.example.com/doc_456",
            "preview_value": "https://docs.example.com/doc_456",
            "clickable": True,
        },
        "delivery": {"feishu_card_mode": "link_button"},
        "label": "项目方案",
        "path": None,
        "remote": {
            "provider": "feishu",
            "url": "https://docs.example.com/doc_456",
            "document_id": "doc_456",
        },
        "url": "https://docs.example.com/doc_456",
        "clickable": True,
        "source_task_id": TASK_ID,
    }
]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(body, encoding="utf-8")


def _load_test_client(tasks_root: Path, event_dir: Path) -> Any:
    try:
        module = importlib.import_module("bridge.server_app")
    except Exception as exc:  # pragma: no cover - intentional failure until T4 exists
        pytest.fail(
            "Implement `bridge.server_app.create_app(tasks_root, event_dir)` for the SSE contract tests. "
            f"Original import error: {exc}",
            pytrace=False,
        )
    create_app = getattr(module, "create_app", None)
    if not callable(create_app):  # pragma: no cover - intentional failure until T4 exists
        pytest.fail("`bridge.server_app.create_app` must be callable.", pytrace=False)
    app = create_app(tasks_root=tasks_root, event_dir=event_dir)
    test_client = getattr(app, "test_client", None)
    if not callable(test_client):  # pragma: no cover - intentional failure until T4 exists
        pytest.fail("`bridge.server_app.create_app()` must return an app with `.test_client()`.", pytrace=False)
    if hasattr(app, "config") and isinstance(app.config, dict):
        app.config["TESTING"] = True
    return test_client()


def _parse_sse_events(response: Any) -> list[dict[str, Any]]:
    raw = response.get_data(as_text=True)
    chunks = [chunk.strip() for chunk in raw.split("\n\n") if chunk.strip()]
    events: list[dict[str, Any]] = []
    for chunk in chunks:
        data_lines = [line.removeprefix("data: ") for line in chunk.splitlines() if line.startswith("data: ")]
        assert data_lines, f"missing SSE data line in chunk: {chunk!r}"
        events.append(json.loads("\n".join(data_lines)))
    return events


@pytest.fixture()
def stream_workspace(tmp_path: Path) -> dict[str, Path]:
    tasks_root = tmp_path / "tasks"
    event_dir = tmp_path / "events"
    task_dir = tasks_root / TASK_ID

    _write_json(
        task_dir / "status.json",
        {
            "task_id": TASK_ID,
            "state": "completed",
            "created_at": "2026-05-05T08:00:00+00:00",
            "updated_at": "2026-05-05T08:10:00+00:00",
            "error": None,
        },
    )
    _write_json(task_dir / "artifacts.json", EXPECTED_ARTIFACTS)
    _write_jsonl(
        task_dir / "chat_messages.jsonl",
        [
            {
                "timestamp": "2026-05-05T08:00:00+00:00",
                "role": "assistant",
                "text": "交付物已生成，可以回传群聊。",
                "source": "artifacts",
            }
        ],
    )

    return {"tasks_root": tasks_root, "event_dir": event_dir}


@pytest.fixture()
def client(stream_workspace: dict[str, Path]) -> Any:
    return _load_test_client(stream_workspace["tasks_root"], stream_workspace["event_dir"])


def test_sse_headers(client: Any) -> None:
    response = client.get(f"/api/tasks/{TASK_ID}/stream")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["X-Accel-Buffering"] == "no"


def test_sse_payload_structure(client: Any) -> None:
    response = client.get(f"/api/tasks/{TASK_ID}/stream")

    events = _parse_sse_events(response)
    payload = events[0]

    assert set(payload) == {
        "ok",
        "done",
        "state",
        "pending_controls",
        "stream_texts",
        "artifacts",
        "current_turn_artifacts",
        "error",
    }
    assert payload["ok"] is True
    assert payload["done"] is True
    assert payload["state"] == "completed"
    assert payload["pending_controls"] is False
    assert isinstance(payload["stream_texts"], list)
    assert payload["stream_texts"]
    assert all(isinstance(text, str) for text in payload["stream_texts"])
    assert payload["artifacts"] == EXPECTED_ARTIFACTS
    assert payload["current_turn_artifacts"] == EXPECTED_CURRENT_TURN_ARTIFACTS
    assert payload["error"] is None


def test_sse_terminates_when_done(client: Any) -> None:
    response = client.get(f"/api/tasks/{TASK_ID}/stream")

    events = _parse_sse_events(response)

    assert events[-1]["done"] is True
    assert len(events) == 1


def test_sse_task_not_found(client: Any) -> None:
    response = client.get("/api/tasks/missing-task/stream")

    assert response.status_code == 200
    assert _parse_sse_events(response) == [
        {
            "ok": False,
            "done": True,
            "state": "failed",
            "pending_controls": False,
            "stream_texts": [],
            "artifacts": None,
            "current_turn_artifacts": [],
            "error": "task not found",
        }
    ]
