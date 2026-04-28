from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_STATES = frozenset({"queued", "running", "waiting_for_user", "completed", "failed"})
REQUIRED_ARTIFACT_FIELDS = frozenset({"task_id", "document", "slides", "whiteboard", "summary", "next_steps"})


class ProtocolError(ValueError):
    """Raised when a task protocol file is invalid."""


def create_task(root: Path, task_id: str, request_markdown: str) -> Path:
    task_dir = root / task_id
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "request.md").write_text(_ensure_trailing_newline(request_markdown), encoding="utf-8")
    now = _now()
    _write_json(
        task_dir / "status.json",
        {
            "task_id": task_id,
            "state": "queued",
            "created_at": now,
            "updated_at": now,
            "error": None,
        },
    )
    return task_dir


def read_status(task_dir: Path) -> dict[str, Any]:
    status = _read_json(task_dir / "status.json")
    state = status.get("state")
    if state not in VALID_STATES:
        raise ProtocolError(f"invalid state: {state}")
    return status


def write_status(task_dir: Path, state: str, error: str | None = None) -> dict[str, Any]:
    if state not in VALID_STATES:
        raise ProtocolError(f"invalid state: {state}")

    current = read_status(task_dir)
    updated = {
        "task_id": current["task_id"],
        "state": state,
        "created_at": current["created_at"],
        "updated_at": _now(),
        "error": error,
    }
    _write_json(task_dir / "status.json", updated)
    return updated


def write_artifacts(task_dir: Path, artifacts: dict[str, Any]) -> dict[str, Any]:
    _validate_artifacts(artifacts)
    _write_json(task_dir / "artifacts.json", artifacts)
    return artifacts


def read_artifacts(task_dir: Path) -> dict[str, Any]:
    artifacts = _read_json(task_dir / "artifacts.json")
    _validate_artifacts(artifacts)
    return artifacts


def _validate_artifacts(artifacts: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_ARTIFACT_FIELDS - set(artifacts))
    if missing:
        raise ProtocolError(f"missing artifact fields: {', '.join(missing)}")
    for key in ("document", "slides", "whiteboard"):
        value = artifacts.get(key)
        if not isinstance(value, dict) or not value.get("path"):
            raise ProtocolError(f"artifact {key} must be an object with path")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProtocolError(f"missing protocol file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid json: {path}") from exc
    if not isinstance(data, dict):
        raise ProtocolError(f"json root must be an object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_trailing_newline(value: str) -> str:
    return value if value.endswith("\n") else value + "\n"
