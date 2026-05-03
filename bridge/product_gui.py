from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bridge.artifacts import artifact_items, remote_label
from bridge.task_control import append_control_command
from bridge.task_index import TaskSummary, build_task_index


STATIC_DIR = Path(__file__).with_name("product_gui_static")
LOCAL_CJK_FONT = Path("/home/lifei/.local/share/fonts/NotoSansSC-VF.ttf")


@dataclass(frozen=True)
class ArtifactView:
    id: str
    kind: str
    title: str
    format_hint: str
    status: str
    value: str
    url: str


@dataclass(frozen=True)
class ExecutionStepView:
    id: str
    label: str
    status: str


def build_workspace_view(tasks_root: Path = Path("tasks")) -> dict[str, Any]:
    bindings = _read_bindings(tasks_root)
    tasks = {task.task_id: task for task in build_task_index(tasks_root)}
    groups: dict[str, dict[str, Any]] = {}

    for session_id, binding in bindings.items():
        task = _task_for_binding(binding, tasks)
        group_id = str(binding.get("chat_id") or _group_id_from_session(session_id))
        group = groups.setdefault(
            group_id,
            {
                "group_id": group_id,
                "group_name": str(binding.get("chat_name") or group_id or _group_id_from_session(session_id)),
                "sessions": [],
            },
        )
        group["sessions"].append(_session_summary(session_id, binding, task))

    for group in groups.values():
        group["sessions"].sort(key=lambda item: item["updated_at"], reverse=True)

    ordered_groups = sorted(groups.values(), key=lambda item: str(item["group_name"]))
    selected = _first_active_session(ordered_groups)
    return {
        "groups": ordered_groups,
        "selected_session_id": selected,
        "total_sessions": sum(len(group["sessions"]) for group in ordered_groups),
    }


def build_selected_session_view(tasks_root: Path, session_id: str) -> dict[str, Any]:
    bindings = _read_bindings(tasks_root)
    binding = bindings.get(session_id)
    if binding is None:
        raise KeyError(f"unknown session: {session_id}")

    tasks = {task.task_id: task for task in build_task_index(tasks_root)}
    task = _task_for_binding(binding, tasks)
    if task is None:
        raise KeyError(f"session has no task: {session_id}")

    task_dir = tasks_root / task.task_id
    artifacts = _read_json(task_dir / "artifacts.json") if (task_dir / "artifacts.json").exists() else {}
    request = _read_request_message(task_dir / "request.md")
    artifact_views = [_artifact_view(item, task.state) for item in artifact_items(artifacts)]
    return {
        "session_id": session_id,
        "title": str(binding.get("session_title") or _title_from_task(task)),
        "source_group": str(binding.get("chat_name") or binding.get("chat_id") or _group_id_from_session(session_id)),
        "user_request": request or task.summary,
        "agent_messages": [_agent_message(task, artifact_views)],
        "execution_steps": [asdict(step) for step in _execution_steps(task, artifact_views)],
        "artifacts": [asdict(item) for item in artifact_views],
        "task_detail": {
            "task_id": task.task_id,
            "state": task.state,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "target": task.summary,
            "codex_thread_id": task.codex_thread_id,
            "active_turn_id": task.active_turn_id,
            "artifact_count": len(artifact_views),
            "error": task.error,
        },
    }


def create_product_gui_app(tasks_root: Path = Path("tasks")):
    from flask import Flask, jsonify, request, send_from_directory

    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/static/fonts/noto-sans-sc.ttf")
    def noto_sans_sc():
        if not LOCAL_CJK_FONT.exists():
            return "", 404
        return send_from_directory(LOCAL_CJK_FONT.parent, LOCAL_CJK_FONT.name)

    @app.get("/api/workspace")
    def workspace():
        return jsonify(build_workspace_view(tasks_root))

    @app.get("/api/sessions/<path:session_id>")
    def selected_session(session_id: str):
        try:
            return jsonify(build_selected_session_view(tasks_root, session_id))
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 404

    @app.post("/api/sessions/<path:session_id>/messages")
    def append_message(session_id: str):
        data = request.get_json(silent=True) or {}
        text = str(data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "missing text"}), 400
        try:
            task_dir = _task_dir_for_session(tasks_root, session_id)
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 404
        command = append_control_command(
            task_dir,
            "append_instruction",
            {
                "source": "gui",
                "kind": "operator_followup",
                "session_id": session_id,
                "text": text,
            },
            operator="gui",
        )
        return jsonify({"ok": True, "command": command})

    return app


def _session_summary(
    session_id: str,
    binding: dict[str, Any],
    task: TaskSummary | None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "title": str(binding.get("session_title") or _title_from_task(task) if task else _title_from_session(session_id)),
        "state": task.state if task else "unknown",
        "updated_at": task.updated_at if task else str(binding.get("updated_at") or ""),
        "active_task_id": str(binding.get("active_task_id") or ""),
        "last_task_id": str(binding.get("last_task_id") or ""),
        "summary": task.summary if task else "",
        "artifact_count": len(task.artifact_outputs) if task else 0,
    }


def _task_for_binding(binding: dict[str, Any], tasks: dict[str, TaskSummary]) -> TaskSummary | None:
    task_id = str(binding.get("active_task_id") or binding.get("last_task_id") or "")
    return tasks.get(task_id)


def _task_dir_for_session(tasks_root: Path, session_id: str) -> Path:
    binding = _read_bindings(tasks_root).get(session_id)
    if binding is None:
        raise KeyError(f"unknown session: {session_id}")
    task_id = str(binding.get("active_task_id") or binding.get("last_task_id") or "")
    if not task_id:
        raise KeyError(f"session has no task: {session_id}")
    return tasks_root / task_id


def _artifact_view(item: dict[str, Any], task_state: str) -> ArtifactView:
    remote = item.get("remote") if isinstance(item.get("remote"), dict) else {}
    path = str(item.get("path") or "")
    value = remote_label(item) or path
    status = "completed" if remote_label(item) else ("generating" if task_state == "running" else "pending")
    return ArtifactView(
        id=str(item.get("id") or item.get("kind") or "artifact"),
        kind=str(item.get("kind") or item.get("type") or "artifact"),
        title=str(item.get("title") or item.get("id") or item.get("kind") or "artifact"),
        format_hint=_format_hint(item, path),
        status=status,
        value=value,
        url=str(remote.get("url") or ""),
    )


def _format_hint(item: dict[str, Any], path: str) -> str:
    suffix = Path(path).suffix.removeprefix(".")
    if suffix:
        return suffix
    kind = str(item.get("kind") or "file")
    return kind


def _execution_steps(task: TaskSummary, artifacts: list[ArtifactView]) -> list[ExecutionStepView]:
    if task.state == "completed":
        execution_status = "done"
        artifact_status = "done"
        delivery_status = "done"
    elif task.state == "running":
        execution_status = "active"
        artifact_status = "active" if artifacts else "todo"
        delivery_status = "todo"
    elif task.state == "waiting_for_user":
        execution_status = "active"
        artifact_status = "todo"
        delivery_status = "todo"
    else:
        execution_status = "todo"
        artifact_status = "todo"
        delivery_status = "todo"

    return [
        ExecutionStepView("context", "读取会话上下文", "done"),
        ExecutionStepView("brief", "整理关键信息与待办", "done" if task.state in {"running", "waiting_for_user", "completed"} else "todo"),
        ExecutionStepView("artifacts", "生成交付产物", artifact_status if artifact_status != "done" else execution_status),
        ExecutionStepView("delivery", "回传或等待用户确认", delivery_status),
    ]


def _agent_message(task: TaskSummary, artifacts: list[ArtifactView]) -> str:
    completed_count = sum(1 for item in artifacts if item.status == "completed")
    if task.state == "completed":
        return f"文档生成完成，已生成 {len(artifacts)} 个产物。"
    if task.state == "running":
        return f"收到，正在为你梳理并生成相关材料，当前已完成 {completed_count} 个产物。"
    if task.state == "waiting_for_user":
        return "我已经整理出需要确认的信息，请补充或确认后继续。"
    if task.error:
        return "任务执行遇到问题，右侧详情中有错误信息。"
    return "任务已进入队列。"


def _read_bindings(tasks_root: Path) -> dict[str, dict[str, Any]]:
    path = tasks_root / "task-bindings.json"
    if not path.exists():
        return _demo_bindings(tasks_root)
    data = _read_json(path)
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def _read_request_message(path: Path) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## User Message") + 1
    except ValueError:
        return ""
    collected = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _first_active_session(groups: list[dict[str, Any]]) -> str:
    for group in groups:
        for session in group["sessions"]:
            if session["state"] == "running":
                return str(session["session_id"])
    for group in groups:
        if group["sessions"]:
            return str(group["sessions"][0]["session_id"])
    return ""


def _title_from_task(task: TaskSummary | None) -> str:
    if task and task.summary:
        return task.summary[:28]
    if task:
        return task.task_id
    return "未命名任务"


def _title_from_session(session_id: str) -> str:
    return session_id.rsplit(":", 1)[-1].replace("-", " ")


def _group_id_from_session(session_id: str) -> str:
    parts = session_id.split(":")
    return parts[1] if len(parts) > 1 else session_id


def _demo_bindings(tasks_root: Path) -> dict[str, dict[str, Any]]:
    tasks = build_task_index(tasks_root)
    if tasks:
        task = tasks[0]
        return {
            task.session_key or f"local:{task.task_id}": {
                "session_key": task.session_key or f"local:{task.task_id}",
                "chat_id": "local",
                "chat_name": "local",
                "session_title": _title_from_task(task),
                "active_task_id": task.task_id if task.state == "running" else None,
                "last_task_id": task.task_id,
            }
        }
    return {}
