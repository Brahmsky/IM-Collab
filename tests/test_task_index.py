from __future__ import annotations

import json
from pathlib import Path

from bridge.task_index import build_task_index, summarize_events


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_task_index_sorts_by_updated_at_and_extracts_remote_links(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "old" / "status.json",
        {
            "task_id": "old",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "old" / "artifacts.json",
            {
                "task_id": "old",
                "items": [
                    {"id": "brief", "kind": "brief", "remote": {"url": "https://example/doc-old"}},
                    {"id": "deck", "kind": "deck", "remote": {"url": "https://example/slides-old"}},
                    {"id": "board", "kind": "board", "remote": {"label": "历史白板", "whiteboard_token": "wb-old"}},
                ],
                "summary": "old summary",
                "next_steps": [],
            },
    )
    write_json(
        tasks_root / "new" / "status.json",
        {
            "task_id": "new",
            "state": "completed",
            "created_at": "2026-04-28T02:00:00+00:00",
            "updated_at": "2026-04-28T02:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "new" / "artifacts.json",
            {
                "task_id": "new",
                "items": [
                    {"id": "brief", "kind": "brief", "remote": {"url": "https://example/doc-new"}},
                    {"id": "deck", "kind": "deck", "remote": {"url": "https://example/slides-new"}},
                    {"id": "board", "kind": "board", "remote": {"url": "https://example/board-new", "whiteboard_token": "wb-new"}},
                ],
                "summary": "new summary",
                "next_steps": [],
            },
    )

    index = build_task_index(tasks_root)

    assert [task.task_id for task in index] == ["new", "old"]
    assert ("brief", "https://example/doc-new") in index[0].artifact_outputs
    assert ("deck", "https://example/slides-new") in index[0].artifact_outputs
    assert ("board", "https://example/board-new") in index[0].artifact_outputs
    assert index[0].summary == "new summary"


def test_build_task_index_uses_whiteboard_label_when_click_url_missing(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "label-only-board" / "status.json",
        {
            "task_id": "label-only-board",
            "state": "completed",
            "created_at": "2026-04-28T03:00:00+00:00",
            "updated_at": "2026-04-28T03:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        tasks_root / "label-only-board" / "artifacts.json",
        {
            "task_id": "label-only-board",
            "items": [
                {
                    "id": "board",
                    "kind": "whiteboard",
                    "title": "流程白板",
                    "remote": {"label": "可继续编辑的白板", "whiteboard_token": "wb-123"},
                }
            ],
            "summary": "label summary",
            "next_steps": [],
        },
    )

    [task] = build_task_index(tasks_root)

    assert task.artifact_outputs == (("流程白板", "可继续编辑的白板"),)


def test_build_task_index_includes_failed_task_error(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    write_json(
        tasks_root / "broken" / "status.json",
        {
            "task_id": "broken",
            "state": "failed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:05:00+00:00",
            "error": "Feishu permission denied",
        },
    )

    index = build_task_index(tasks_root)

    assert len(index) == 1
    assert index[0].state == "failed"
    assert index[0].error == "Feishu permission denied"
    assert index[0].artifact_outputs == ()


def test_task_index_shows_waiting_confirmation_controls(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    write_json(
        task_dir / "status.json",
        {
            "task_id": "task-1",
            "state": "waiting_for_user",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    (task_dir / "control.jsonl").write_text(
        json.dumps({"type": "card_action", "payload": {"action": "start_task"}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    [task] = build_task_index(tasks_root)

    assert task.pending_controls == 1
    assert task.control_count == 1
    assert task.last_control_type == "card_action"


def test_summarize_events_counts_latest_event_files(tmp_path: Path) -> None:
    event_dir = tmp_path / "events"
    (event_dir / "im.message.receive_v1_a.json").parent.mkdir(parents=True)
    (event_dir / "im.message.receive_v1_a.json").write_text("{}", encoding="utf-8")
    (event_dir / "im.message.receive_v1_b.json").write_text("{}", encoding="utf-8")

    summary = summarize_events(event_dir, limit=1)

    assert summary.total == 2
    assert summary.latest_files == ["im.message.receive_v1_b.json"]
