from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

from bridge.artifacts import artifact_items, remote_label
from bridge.chat_messages import read_chat_messages
from bridge.task_console_web import handle_console_action, handle_console_action_result, make_codex_app_server_retry
from bridge.task_control import read_control_commands
from bridge.task_index import TaskSummary, build_task_index, summarize_events
from bridge.task_ops import retry_golembot_task
from bridge.task_protocol import ProtocolError, read_artifacts, read_status

RetryFunc = Callable[..., dict[str, Any]]
AppServerRetryFunc = Callable[[Path, bool], dict[str, Any]]


def create_app(
    tasks_root: Path,
    event_dir: Path,
    *,
    retry: RetryFunc = retry_golembot_task,
    app_server_retry: AppServerRetryFunc | None = None,
    run_followup_in_background: bool = True,
    project_root: Path | None = None,
) -> Flask:
    app = Flask(__name__)
    CORS(app)

    tasks_root = Path(tasks_root)
    event_dir = Path(event_dir)
    project_root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[1]
    app_server_retry = app_server_retry or make_codex_app_server_retry(project_root, retry=retry)

    @app.get("/api/tasks")
    def get_tasks() -> Response:
        tasks = [_task_summary_payload(task) for task in build_task_index(tasks_root)]
        events = summarize_events(event_dir)
        return jsonify(
            {
                "tasks": tasks,
                "events": {
                    "total": events.total,
                    "latest_files": events.latest_files,
                },
            }
        )

    @app.get("/api/tasks/<task_id>")
    def get_task(task_id: str) -> Response:
        selected = _find_task_summary(tasks_root, task_id)
        if selected is None:
            return jsonify({"ok": False, "error": "task not found"}), 404
        task_dir = selected.path
        controls = read_control_commands(task_dir)
        return jsonify(
            {
                "task": _task_summary_payload(selected),
                "chat_messages": read_chat_messages(task_dir),
                "control_commands": controls,
                "artifacts": read_artifacts(task_dir),
                "current_turn_artifacts": _current_turn_artifacts(task_dir),
                "session_artifacts": _session_artifacts(tasks_root, selected),
                "pending_controls": _has_pending_controls(task_dir, controls),
            }
        )

    @app.post("/api/tasks/<task_id>/append")
    def append_task(task_id: str) -> Response:
        task_id = task_id.strip()
        if not task_id:
            return jsonify({"ok": False, "error": "missing task_id"}), 400
        payload = _request_payload()
        text = str(payload.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "missing field: text"}), 400
        result = handle_console_action_result(
            tasks_root,
            {"action": "append", "task_id": task_id, "text": text},
            retry=retry,
            app_server_retry=app_server_retry,
            run_followup_in_background=run_followup_in_background,
        )
        return jsonify(
            {
                "ok": True,
                "backend": result.backend,
                "task_id": task_id,
                "stream_url": f"/api/tasks/{task_id}/stream",
            }
        )

    @app.post("/api/tasks/<task_id>/interrupt")
    def interrupt_task(task_id: str) -> Response:
        handle_console_action(tasks_root, {"action": "interrupt", "task_id": _require_task_id(task_id)})
        return jsonify({"ok": True})

    @app.post("/api/tasks/<task_id>/ack")
    def ack_task(task_id: str) -> Response:
        payload = _request_payload()
        handle_console_action(
            tasks_root,
            {
                "action": "ack",
                "task_id": _require_task_id(task_id),
                "note": str(payload.get("note") or ""),
            },
        )
        return jsonify({"ok": True})

    @app.post("/api/tasks/<task_id>/retry")
    def retry_task(task_id: str) -> Response:
        payload = _request_payload()
        publish = payload.get("publish") in {True, 1, "1", "true", "on"}
        result = handle_console_action_result(
            tasks_root,
            {
                "action": "retry",
                "task_id": _require_task_id(task_id),
                "generator": "app-server",
                "publish": "1" if publish else "",
            },
            retry=retry,
            app_server_retry=app_server_retry,
            run_followup_in_background=run_followup_in_background,
        )
        return jsonify({"ok": True, "generator": "app-server", "backend": result.backend})

    @app.post("/api/sessions/<path:session_key>/rename")
    def rename_session(session_key: str) -> Response:
        payload = _request_payload()
        handle_console_action(
            tasks_root,
            {
                "action": "rename_session",
                "task_id": _task_id_for_session(tasks_root, session_key),
                "session_key": session_key,
                "session_title": str(payload.get("session_title") or ""),
            },
        )
        return jsonify({"ok": True})

    @app.delete("/api/sessions/<path:session_key>")
    def delete_session(session_key: str) -> Response:
        handle_console_action(
            tasks_root,
            {
                "action": "delete_session",
                "task_id": _task_id_for_session(tasks_root, session_key),
                "session_key": session_key,
            },
        )
        return jsonify({"ok": True})

    @app.get("/api/tasks/<task_id>/stream")
    def stream_task(task_id: str) -> Response:
        tid = task_id.strip()

        def generate() -> Any:
            import time as _time
            for _ in range(120):
                payload = _task_stream_payload(tasks_root, tid)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if payload.get("done"):
                    return
                _time.sleep(1)

        response = Response(generate(), content_type="text/event-stream; charset=utf-8")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    # SPA fallback: serve built Vue frontend (must be registered AFTER API routes)
    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"

    @app.route("/assets/<path:filename>")
    def serve_assets(filename: str) -> Any:
        asset_dir = frontend_dist / "assets"
        if not asset_dir.is_dir():
            return jsonify({"ok": False, "error": "frontend assets not found"}), 404
        return send_from_directory(str(asset_dir), filename)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path: str) -> Any:
        index_path = frontend_dist / "index.html"
        if index_path.is_file():
            return send_file(str(index_path))
        return (
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>IM-Collab</title></head>'
            '<body style="font-family:sans-serif;padding:2rem;"><h1>Frontend not built</h1>'
            '<p>Build the frontend first: <code>cd frontend && npm run build</code></p>'
            '<p>Or start Vite dev server: <code>cd frontend && npm run dev</code></p></body></html>',
            200,
        )

    return app


def _request_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _find_task_summary(tasks_root: Path, task_id: str) -> TaskSummary | None:
    return next((task for task in build_task_index(tasks_root) if task.task_id == task_id), None)


def _task_summary_payload(task: TaskSummary) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "state": task.state,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "summary": task.summary,
        "session_key": task.session_key,
        "session_title": task.session_title,
        "chat_name": task.chat_name,
        "chat_id": task.chat_id,
        "codex_thread_id": task.codex_thread_id,
        "artifact_outputs": [list(output) for output in task.artifact_outputs],
    }


def _task_stream_payload(tasks_root: Path, task_id: str) -> dict[str, Any]:
    selected = _find_task_summary(tasks_root, task_id)
    if selected is None:
        return {
            "ok": False,
            "done": True,
            "state": "failed",
            "pending_controls": False,
            "stream_texts": [],
            "artifacts": None,
            "current_turn_artifacts": [],
            "error": "task not found",
        }
    task_dir = selected.path
    controls = read_control_commands(task_dir)
    pending_controls = _has_pending_controls(task_dir, controls)
    try:
        artifacts = read_artifacts(task_dir)
    except ProtocolError:
        artifacts = None
    try:
        status = read_status(task_dir)
        error = status.get("error")
    except ProtocolError as exc:
        status = {"state": "failed", "error": str(exc)}
        error = str(exc)
    messages = read_chat_messages(task_dir)
    return {
        "ok": True,
        "done": selected.state in {"failed", "waiting_for_user"}
        or (selected.state == "completed" and not pending_controls),
        "state": selected.state,
        "pending_controls": pending_controls,
        "stream_texts": [str(message.get("text") or "") for message in messages if str(message.get("text") or "").strip()],
        "artifacts": artifacts,
        "current_turn_artifacts": _current_turn_artifacts(task_dir),
        "error": error,
    }


def _has_pending_controls(task_dir: Path, controls: list[dict[str, Any]] | None = None) -> bool:
    try:
        status = read_status(task_dir)
    except ProtocolError:
        return False
    status_time = _parse_iso_datetime(str(status.get("updated_at") or ""))
    if status_time is None:
        return False
    for command in controls or read_control_commands(task_dir):
        if command.get("type") not in {"append_instruction", "confirm_instruction", "card_action"}:
            continue
        command_time = _parse_iso_datetime(str(command.get("timestamp") or ""))
        if command_time is None or command_time > status_time:
            return True
    return False


def _current_turn_artifacts(task_dir: Path) -> list[dict[str, Any]]:
    try:
        artifacts = read_artifacts(task_dir)
    except ProtocolError:
        return []
    return _prioritize_clickable([
        _artifact_payload({**item, "source_task_id": task_dir.name})
        for item in artifact_items(artifacts)
        if _include_artifact(item)
    ])


def _session_artifacts(tasks_root: Path, selected: TaskSummary) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for task in build_task_index(tasks_root):
        if task.session_key != selected.session_key:
            continue
        try:
            artifacts = read_artifacts(task.path)
        except ProtocolError:
            continue
        for item in artifact_items(artifacts):
            if not _include_artifact(item):
                continue
            key = (_artifact_kind(item), _artifact_url(item) or remote_label(item) or str(item.get("path") or ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(_artifact_payload({**item, "source_task_id": task.task_id}))
    return _prioritize_clickable(out)


def _include_artifact(item: dict[str, Any]) -> bool:
    values = {
        str(item.get("kind") or "").lower(),
        str(item.get("type") or "").lower(),
        str(item.get("id") or "").lower(),
    }
    if values & {"document", "docx", "slides", "presentation", "ppt", "pptx", "whiteboard", "board", "diagram", "mermaid"}:
        return True
    remote = item.get("remote")
    if not isinstance(remote, dict):
        return False
    return any(remote.get(field) for field in ("document_id", "xml_presentation_id", "whiteboard_token"))


def _artifact_payload(item: dict[str, Any]) -> dict[str, Any]:
    url = _artifact_url(item)
    return {
        "id": str(item.get("id") or item.get("kind") or ""),
        "kind": _artifact_kind(item),
        "title": _artifact_title(item),
        "label": _artifact_title(item),
        "path": str(item.get("path") or "") or None,
        "remote": item.get("remote") if isinstance(item.get("remote"), dict) else None,
        "url": url,
        "clickable": bool(url),
        "source_task_id": _artifact_source_task_id(item),
    }


def _artifact_url(item: dict[str, Any]) -> str | None:
    remote = item.get("remote") if isinstance(item.get("remote"), dict) else {}
    if isinstance(remote, dict):
        for field in ("url", "web_url", "permalink"):
            value = remote.get(field)
            if value:
                return str(value)
    return None


def _artifact_kind(item: dict[str, Any]) -> str:
    raw = str(item.get("kind") or item.get("id") or "").lower()
    if raw in {"presentation", "ppt", "pptx"}:
        return "slides"
    if raw in {"diagram", "mermaid", "board"}:
        return "whiteboard"
    if raw == "docx":
        return "document"
    return raw or "artifact"


def _artifact_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    if title:
        return title
    remote = item.get("remote")
    if isinstance(remote, dict):
        remote_title = str(remote.get("label") or remote.get("title") or remote.get("name") or "").strip()
        if remote_title:
            return remote_title
    return str(item.get("kind") or item.get("id") or "artifact")


def _prioritize_clickable(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clickable = [item for item in items if item.get("clickable") is True]
    fallback = [item for item in items if item.get("clickable") is not True]
    return clickable + fallback


def _artifact_source_task_id(item: dict[str, Any]) -> str | None:
    source_task_id = item.get("source_task_id")
    if isinstance(source_task_id, str) and source_task_id.strip():
        return source_task_id
    path = str(item.get("path") or "").strip()
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] == "tasks":
        return parts[1]
    return None


def _parse_iso_datetime(raw: str) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _task_id_for_session(tasks_root: Path, session_key: str) -> str:
    bindings_path = tasks_root / "task-bindings.json"
    if not bindings_path.exists():
        return "local-session"
    try:
        payload = json.loads(bindings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "local-session"
    if not isinstance(payload, dict):
        return "local-session"
    binding = payload.get(session_key)
    if not isinstance(binding, dict):
        return "local-session"
    task_id = str(binding.get("active_task_id") or binding.get("last_task_id") or "").strip()
    return task_id or "local-session"


def _require_task_id(task_id: str) -> str:
    value = task_id.strip()
    if not value:
        raise ValueError("missing task_id")
    return value
