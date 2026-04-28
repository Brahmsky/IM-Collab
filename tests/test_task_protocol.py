from __future__ import annotations

import json
from pathlib import Path

import pytest

from bridge.task_protocol import (
    VALID_STATES,
    ProtocolError,
    create_task,
    read_artifacts,
    read_status,
    write_artifacts,
    write_status,
)


def test_create_task_writes_request_and_queued_status(tmp_path: Path) -> None:
    task_dir = create_task(
        root=tmp_path,
        task_id="demo-task",
        request_markdown="# Request\n\nGenerate a project plan.",
    )

    assert task_dir == tmp_path / "demo-task"
    assert (task_dir / "request.md").read_text(encoding="utf-8") == "# Request\n\nGenerate a project plan.\n"

    status = read_status(task_dir)
    assert status["task_id"] == "demo-task"
    assert status["state"] == "queued"
    assert status["created_at"]
    assert status["updated_at"]
    assert status["error"] is None


def test_write_status_rejects_invalid_state(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "hello")

    with pytest.raises(ProtocolError, match="invalid state"):
        write_status(task_dir, "done")

    status = read_status(task_dir)
    assert status["state"] == "queued"
    assert "completed" in VALID_STATES


def test_write_status_preserves_created_at(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "hello")
    original = read_status(task_dir)

    write_status(task_dir, "running")
    updated = read_status(task_dir)

    assert updated["task_id"] == "demo-task"
    assert updated["state"] == "running"
    assert updated["created_at"] == original["created_at"]
    assert updated["updated_at"] >= original["updated_at"]


def test_write_artifacts_requires_delivery_fields(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "hello")

    with pytest.raises(ProtocolError, match="missing artifact fields"):
        write_artifacts(task_dir, {"summary": "partial"})

    assert not (task_dir / "artifacts.json").exists()


def test_write_and_read_artifacts(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "hello")
    artifacts = {
        "task_id": "demo-task",
        "document": {"type": "markdown", "path": "tasks/demo-task/document.md"},
        "slides": {"type": "markdown", "path": "tasks/demo-task/slides.md"},
        "whiteboard": {"type": "mermaid", "path": "tasks/demo-task/whiteboard.mmd"},
        "summary": "Generated local office artifacts.",
        "next_steps": ["Connect Feishu webhook."],
    }

    write_artifacts(task_dir, artifacts)

    assert read_artifacts(task_dir) == artifacts
    raw = json.loads((task_dir / "artifacts.json").read_text(encoding="utf-8"))
    assert raw["summary"] == "Generated local office artifacts."


def test_read_artifacts_rejects_string_artifact_paths(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "demo-task", "hello")
    (task_dir / "artifacts.json").write_text(
        json.dumps(
            {
                "task_id": "demo-task",
                "document": "document.md",
                "slides": "slides.md",
                "whiteboard": "whiteboard.mmd",
                "summary": "Generated local office artifacts.",
                "next_steps": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProtocolError, match="artifact document must be an object with path"):
        read_artifacts(task_dir)
