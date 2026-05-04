from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bridge.artifacts import artifact_items, remote_label


@dataclass(frozen=True)
class TaskSummary:
    task_id: str
    state: str
    created_at: str
    updated_at: str
    error: str
    summary: str
    artifact_outputs: tuple[tuple[str, str], ...]
    session_key: str
    session_title: str
    chat_name: str
    chat_id: str
    codex_thread_id: str
    active_turn_id: str
    control_count: int
    pending_controls: int
    last_control_type: str
    ack_operator: str
    ack_note: str
    path: Path


@dataclass(frozen=True)
class EventSummary:
    total: int
    latest_files: list[str]


def build_task_index(tasks_root: Path = Path("tasks")) -> list[TaskSummary]:
    if not tasks_root.exists():
        return []
    bindings = _read_bindings(tasks_root / "task-bindings.json")
    summaries = [_read_task_summary(path, bindings) for path in tasks_root.iterdir() if path.is_dir()]
    return sorted(
        (summary for summary in summaries if summary is not None),
        key=lambda item: item.updated_at,
        reverse=True,
    )


def summarize_events(event_dir: Path = Path("events"), limit: int = 5) -> EventSummary:
    if not event_dir.exists():
        return EventSummary(total=0, latest_files=[])
    files = sorted((path for path in event_dir.rglob("*.json") if path.is_file()), key=lambda path: path.name)
    return EventSummary(total=len(files), latest_files=[path.name for path in files[-limit:]][::-1])


def _read_task_summary(task_dir: Path, bindings: dict[str, dict[str, Any]]) -> TaskSummary | None:
    status_path = task_dir / "status.json"
    if not status_path.exists():
        return None
    status = _read_json(status_path)
    artifacts = _read_json(task_dir / "artifacts.json") if (task_dir / "artifacts.json").exists() else {}
    task_id = str(status.get("task_id") or task_dir.name)
    binding = _binding_for_task(bindings, task_id)
    controls = _read_control_commands(task_dir)
    control_count = len(controls)
    return TaskSummary(
        task_id=task_id,
        state=str(status.get("state") or "unknown"),
        created_at=str(status.get("created_at") or ""),
        updated_at=str(status.get("updated_at") or ""),
        error=str(status.get("error") or ""),
        summary=str(artifacts.get("summary") or ""),
        artifact_outputs=tuple(_artifact_outputs(artifacts)),
        session_key=str(binding.get("session_key") or ""),
        session_title=str(binding.get("session_title") or ""),
        chat_name=str(binding.get("chat_name") or ""),
        chat_id=str(binding.get("chat_id") or ""),
        codex_thread_id=str(binding.get("codex_thread_id") or ""),
        active_turn_id=str(binding.get("active_turn_id") or ""),
        control_count=control_count,
        pending_controls=control_count,
        last_control_type=str(controls[-1].get("type") or "") if controls else "",
        ack_operator=_ack_value(task_dir, "operator"),
        ack_note=_ack_value(task_dir, "note"),
        path=task_dir,
    )


def _artifact_outputs(artifacts: dict[str, Any]) -> list[tuple[str, str]]:
    outputs = []
    for item in artifact_items(artifacts):
        label = str(item.get("title") or item.get("kind") or item.get("id") or "artifact")
        value = remote_label(item)
        if value:
            outputs.append((label, value))
    return outputs


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def _read_bindings(index_path: Path) -> dict[str, dict[str, Any]]:
    if not index_path.exists():
        return {}
    return _read_json(index_path)


def _binding_for_task(bindings: dict[str, dict[str, Any]], task_id: str) -> dict[str, Any]:
    for session_key, binding in bindings.items():
        if binding.get("active_task_id") == task_id or binding.get("last_task_id") == task_id:
            return {"session_key": session_key, **binding}
    return {}


def _read_control_commands(task_dir: Path) -> list[dict[str, Any]]:
    control_path = task_dir / "control.jsonl"
    if not control_path.exists():
        return []
    commands = []
    for line in control_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            command = json.loads(line)
            if isinstance(command, dict):
                commands.append(command)
    return commands


def _ack_value(task_dir: Path, key: str) -> str:
    ack_path = task_dir / "ack.json"
    if not ack_path.exists():
        return ""
    return str(_read_json(ack_path).get(key) or "")
