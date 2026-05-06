from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

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
        payload = _task_stream_payload(tasks_root, task_id.strip())

        def generate() -> Any:
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

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
