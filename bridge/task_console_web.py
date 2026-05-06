from __future__ import annotations

import json
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from bridge.codex_app_server import AppServerClient, CodexAppServerBackend, StdioAppServerTransport
from bridge.cockpit_console_html import render_cockpit_document
from bridge.chat_messages import append_chat_message, seed_chat_messages_from_task
from bridge.task_control import append_control_command
from bridge.task_index import build_task_index, summarize_events
from bridge.task_ops import ack_task, retry_golembot_task
from bridge.task_protocol import read_artifacts, read_status

RetryFunc = Callable[..., dict[str, Any]]
AppServerRetryFunc = Callable[[Path, bool], dict[str, Any]]


@dataclass(frozen=True)
class ConsoleActionResult:
    flash: str = ""
    backend: str = ""


class _SharedCodexAppServerRetry:
    def __init__(
        self,
        project_root: Path,
        *,
        retry: RetryFunc,
        transport_cls: type[StdioAppServerTransport],
        client_cls: type[AppServerClient],
        backend_cls: type[CodexAppServerBackend],
    ) -> None:
        self.project_root = project_root
        self._retry = retry
        self._transport_cls = transport_cls
        self._client_cls = client_cls
        self._backend_cls = backend_cls
        self._lock = threading.Lock()
        self._transport: StdioAppServerTransport | None = None
        self._backend: CodexAppServerBackend | None = None

    def __call__(self, task_dir: Path, publish: bool = False) -> dict[str, Any]:
        with self._lock:
            return self._retry(
                task_dir,
                generator="app-server",
                publish=publish,
                codex_backend=self._get_backend(),
            )

    def _get_backend(self) -> CodexAppServerBackend:
        if self._backend is None:
            self._transport = self._transport_cls(cwd=self.project_root)
            client = self._client_cls(self._transport)
            client.initialize()
            self._backend = self._backend_cls(client, project_root=self.project_root)
        return self._backend

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._backend = None


def make_codex_app_server_retry(
    project_root: Path,
    *,
    retry: RetryFunc = retry_golembot_task,
    transport_cls: type[StdioAppServerTransport] = StdioAppServerTransport,
    client_cls: type[AppServerClient] = AppServerClient,
    backend_cls: type[CodexAppServerBackend] = CodexAppServerBackend,
) -> AppServerRetryFunc:
    return _SharedCodexAppServerRetry(
        project_root,
        retry=retry,
        transport_cls=transport_cls,
        client_cls=client_cls,
        backend_cls=backend_cls,
    )


def render_console_html(
    tasks_root: Path,
    event_dir: Path,
    flash: str = "",
    *,
    selected_task_id: str | None = None,
    search_query: str = "",
) -> str:
    tasks = build_task_index(tasks_root)
    events = summarize_events(event_dir)
    return render_cockpit_document(
        tasks,
        events,
        flash,
        selected_task_id=selected_task_id,
        search_query=search_query,
    )


def handle_console_action(
    tasks_root: Path,
    form: dict[str, str],
    retry: RetryFunc = retry_golembot_task,
    app_server_retry: AppServerRetryFunc | None = None,
    run_followup_in_background: bool = True,
) -> str:
    return handle_console_action_result(
        tasks_root,
        form,
        retry=retry,
        app_server_retry=app_server_retry,
        run_followup_in_background=run_followup_in_background,
    ).flash


def handle_console_action_result(
    tasks_root: Path,
    form: dict[str, str],
    retry: RetryFunc = retry_golembot_task,
    app_server_retry: AppServerRetryFunc | None = None,
    run_followup_in_background: bool = True,
) -> ConsoleActionResult:
    action = form.get("action", "")
    task_id = _required(form, "task_id")
    task_dir = tasks_root / task_id

    if action == "append":
        seed_chat_messages_from_task(
            task_dir,
            created_at=str(_safe_status(task_dir).get("created_at") or ""),
            assistant_text=str(_safe_artifacts(task_dir).get("summary") or ""),
        )
        append_chat_message(task_dir, "user", _required(form, "text"), source="gui")
        append_control_command(
            task_dir,
            "append_instruction",
            {
                "source": "gui",
                "kind": "operator_followup",
                "text": _required(form, "text"),
            },
            operator="operator",
        )
        return ConsoleActionResult(backend=_append_followup_backend(task_dir, app_server_retry, run_followup_in_background))

    if action == "interrupt":
        append_control_command(task_dir, "interrupt", {}, operator="operator")
        return ConsoleActionResult()

    if action == "ack":
        ack_task(task_dir, operator="operator", note=form.get("note", ""))
        return ConsoleActionResult()

    if action == "retry":
        generator = form.get("generator") or "local"
        publish = form.get("publish") in {"1", "true", "on"}
        if generator == "app-server" and app_server_retry is not None:
            app_server_retry(task_dir, publish)
            return ConsoleActionResult(backend="codex_app_server")
        retry(task_dir, generator=generator, publish=publish)
        return ConsoleActionResult(backend=generator)

    if action == "rename_session":
        title = _required(form, "session_title")
        _rename_session(tasks_root / "task-bindings.json", form.get("session_key", ""), task_id, title)
        return ConsoleActionResult()

    if action == "delete_session":
        _delete_session(tasks_root, task_id, form.get("session_key", ""))
        return ConsoleActionResult()

    raise ValueError(f"unsupported action: {action}")


def _append_followup_backend(
    task_dir: Path,
    app_server_retry: AppServerRetryFunc | None,
    run_followup_in_background: bool,
) -> str:
    if str(_safe_status(task_dir).get("state") or "") == "running":
        return "active_turn"
    if app_server_retry is None:
        return ""
    if run_followup_in_background:
        threading.Thread(target=app_server_retry, args=(task_dir, False), daemon=True).start()
    else:
        app_server_retry(task_dir, False)
    return "codex_app_server"


def _safe_status(task_dir: Path) -> dict[str, Any]:
    try:
        return read_status(task_dir)
    except Exception:
        return {}


def _safe_artifacts(task_dir: Path) -> dict[str, Any]:
    try:
        return read_artifacts(task_dir)
    except Exception:
        return {}


def _required(form: dict[str, str], key: str) -> str:
    value = form.get(key, "").strip()
    if not value:
        raise ValueError(f"missing field: {key}")
    return value


def _read_bindings(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"task binding index root must be an object: {path}")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _write_bindings(path: Path, bindings: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rename_session(index_path: Path, session_key: str, task_id: str, title: str) -> None:
    bindings = _read_bindings(index_path)
    if not session_key:
        session_key = f"local:{task_id}"
    if session_key not in bindings:
        bindings[session_key] = {
            "session_key": session_key,
            "chat_id": "local",
            "chat_name": "本地会话",
            "active_task_id": None,
            "last_task_id": task_id,
        }
    bindings[session_key] = {**bindings[session_key], "session_title": title}
    _write_bindings(index_path, bindings)


def _delete_session(tasks_root: Path, task_id: str, session_key: str) -> None:
    bindings_path = tasks_root / "task-bindings.json"
    bindings = _read_bindings(bindings_path)
    if session_key:
        bindings.pop(session_key, None)
    else:
        bindings = {
            key: value
            for key, value in bindings.items()
            if value.get("active_task_id") != task_id and value.get("last_task_id") != task_id
        }
    _write_bindings(bindings_path, bindings)

    task_dir = tasks_root / task_id
    if not task_dir.exists():
        return
    archive_root = tasks_root / ".archived"
    archive_root.mkdir(parents=True, exist_ok=True)
    destination = archive_root / task_id
    if destination.exists():
        suffix = 1
        while (archive_root / f"{task_id}-{suffix}").exists():
            suffix += 1
        destination = archive_root / f"{task_id}-{suffix}"
    shutil.move(task_dir.as_posix(), destination.as_posix())
