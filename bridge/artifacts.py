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
        for field in ("url", "web_url", "permalink", "whiteboard_token", "token", "id"):
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
