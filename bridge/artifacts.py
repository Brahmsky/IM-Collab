from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RESERVED_ARTIFACT_KEYS = {"task_id", "items", "summary", "next_steps"}
DISPLAYABLE_FAMILIES = {"document", "slides", "whiteboard", "sheet", "file"}


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


def artifact_family(item: dict[str, Any]) -> str:
    raw_values = [
        str(item.get("family") or "").lower(),
        str(item.get("kind") or "").lower(),
        str(item.get("type") or "").lower(),
        str(item.get("id") or "").lower(),
    ]
    for raw in raw_values:
        if raw in {"document", "doc", "docx"}:
            return "document"
        if raw in {"slides", "slide", "presentation", "ppt", "pptx"}:
            return "slides"
        if raw in {"whiteboard", "board", "canvas", "diagram", "mermaid"}:
            return "whiteboard"
        if raw in {"sheet", "spreadsheet", "xlsx", "excel"}:
            return "sheet"
        if raw in {"base", "bitable"}:
            return "file"
        if raw == "file":
            return "file"
    return "file"


def artifact_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    if title:
        return title
    display = item.get("display")
    if isinstance(display, dict):
        label = str(display.get("label") or "").strip()
        if label:
            return label
    remote = item.get("remote")
    if isinstance(remote, dict):
        for field in ("label", "title", "name"):
            value = str(remote.get(field) or "").strip()
            if value:
                return value
    return str(item.get("kind") or item.get("id") or "artifact")


def artifact_input(item: dict[str, Any]) -> dict[str, Any] | None:
    current = item.get("input")
    if isinstance(current, dict):
        return current

    path = item.get("path")
    item_type = str(item.get("type") or "").strip()
    if not path and not item_type:
        return None

    normalized: dict[str, Any] = {}
    if item_type:
        normalized["format"] = item_type
    if path:
        normalized["path"] = str(path)
    return normalized or None


def artifact_output(item: dict[str, Any]) -> dict[str, Any] | None:
    current = item.get("output")
    if isinstance(current, dict):
        return current

    remote = item.get("remote")
    if not isinstance(remote, dict):
        return None

    output = dict(remote)
    output.setdefault("provider", str(remote.get("provider") or ""))
    if not output.get("object_type"):
        output["object_type"] = artifact_family(item)
    return output


def remote_url(item: dict[str, Any]) -> str:
    output = artifact_output(item) or {}
    for field in ("url", "web_url", "permalink"):
        if output.get(field):
            return str(output[field])
    return ""


def remote_label(item: dict[str, Any]) -> str:
    display = artifact_display(item)
    if display.get("click_url"):
        return str(display["click_url"])
    if display.get("preview_value"):
        return str(display["preview_value"])
    return ""


def artifact_display(item: dict[str, Any]) -> dict[str, Any]:
    current = item.get("display")
    if isinstance(current, dict):
        return current

    family = artifact_family(item)
    click_url = remote_url(item) or None
    output = artifact_output(item) or {}
    preview_value = (
        click_url
        or str(item.get("path") or "").strip()
        or str(output.get("whiteboard_token") or output.get("token") or output.get("id") or "").strip()
        or None
    )
    return {
        "card_kind": family if family in DISPLAYABLE_FAMILIES else "file",
        "label": artifact_title(item),
        "click_url": click_url,
        "preview_value": preview_value,
        "clickable": bool(click_url),
    }


def artifact_delivery(item: dict[str, Any]) -> dict[str, Any]:
    current = item.get("delivery")
    if isinstance(current, dict):
        return current

    display = artifact_display(item)
    return {
        "feishu_card_mode": "link_button" if display.get("click_url") else "markdown_fallback",
    }


def artifact_card_payload(item: dict[str, Any], *, source_task_id: str | None = None) -> dict[str, Any]:
    family = artifact_family(item)
    display = artifact_display(item)
    return {
        "id": str(item.get("id") or item.get("kind") or ""),
        "family": family,
        "kind": family,
        "title": artifact_title(item),
        "input": artifact_input(item),
        "output": artifact_output(item),
        "display": display,
        "delivery": artifact_delivery(item),
        "label": display.get("label"),
        "path": str(item.get("path") or "") or None,
        "remote": item.get("remote") if isinstance(item.get("remote"), dict) else None,
        "url": display.get("click_url"),
        "clickable": bool(display.get("clickable")),
        "source_task_id": source_task_id,
    }


def artifact_fingerprint(item: dict[str, Any]) -> str:
    payload = {
        "id": str(item.get("id") or item.get("kind") or ""),
        "family": artifact_family(item),
        "input": artifact_input(item),
        "output": artifact_output(item),
        "display": artifact_display(item),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def artifact_baseline_snapshot(artifacts: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": str(item.get("id") or item.get("kind") or ""),
            "family": artifact_family(item),
            "fingerprint": artifact_fingerprint(item),
        }
        for item in artifact_items(artifacts)
    ]


def local_path(item: dict[str, Any]) -> Path | None:
    path = item.get("path")
    if not path:
        artifact_input_value = artifact_input(item)
        if isinstance(artifact_input_value, dict):
            path = artifact_input_value.get("path")
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
