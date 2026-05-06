from __future__ import annotations

from pathlib import Path
from typing import Any


RESERVED_ARTIFACT_KEYS = {"task_id", "items", "summary", "next_steps"}


def artifact_items(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    items = artifacts.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]

    converted: list[dict[str, Any]] = []
    for key, value in artifacts.items():
        if key in RESERVED_ARTIFACT_KEYS or not isinstance(value, dict):
            continue
        if not any(field in value for field in ("path", "remote", "type", "kind")):
            continue
        converted.append({"id": key, "kind": str(value.get("kind") or key), **value})
    return converted


def local_path(item: dict[str, Any]) -> Path | None:
    path = item.get("path")
    return Path(str(path)) if path else None


def resolve_local_path(
    item: dict[str, Any],
    *,
    task_dir: Path | None = None,
    project_root: Path | None = None,
) -> Path | None:
    path = local_path(item)
    if path is None:
        return None
    if path.is_absolute():
        return path

    candidates: list[Path] = []
    if task_dir is not None and len(path.parts) >= 2 and path.parts[0] == "tasks" and path.parts[1] == task_dir.name:
        candidates.append(task_dir.joinpath(*path.parts[2:]))
    if task_dir is not None:
        candidates.append(task_dir / path)

    roots: list[Path] = []
    if project_root is not None:
        roots.append(project_root)
    if task_dir is not None and task_dir.parent.name == "tasks":
        roots.append(task_dir.parent.parent)
    roots.append(Path.cwd())

    for root in roots:
        candidate = root / path
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else path


def remote_url(item: dict[str, Any]) -> str:
    remote = item.get("remote")
    if isinstance(remote, dict):
        for field in ("url", "web_url", "permalink"):
            if remote.get(field):
                return str(remote[field])
    return ""


def remote_label(item: dict[str, Any]) -> str:
    remote = item.get("remote")
    if isinstance(remote, dict):
        for field in ("url", "web_url", "permalink"):
            if remote.get(field):
                return str(remote[field])
        for field in ("label", "title", "name"):
            if remote.get(field):
                return str(remote[field])
        for field in ("whiteboard_token", "token", "id"):
            if remote.get(field):
                return str(remote[field])
    path = item.get("path")
    return str(path) if path else ""


def upsert_item(artifacts: dict[str, Any], item_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    items = artifact_items(artifacts)
    for item in items:
        if str(item.get("id") or item.get("kind") or "") == item_id:
            item.update(updates)
            artifacts["items"] = items
            return item
    item = {"id": item_id, "kind": item_id, **updates}
    items.append(item)
    artifacts["items"] = items
    return item
