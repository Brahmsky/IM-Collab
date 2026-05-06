from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol

from bridge.codex_app_server import AppServerClient, CodexAppServerBackend, CodexTurn, StdioAppServerTransport
from bridge.codex_task_runner import REQUIRED_CODEX_OUTPUTS, _validate_artifact_item_paths
from bridge.chat_messages import append_assistant_message_from_artifacts, append_chat_message, seed_chat_messages_from_task
from bridge.task_protocol import read_artifacts, read_status
from bridge.task_control import read_control_commands
from bridge.task_protocol import write_status


class AppServerTaskBackend(Protocol):
    def start_task(self, task_dir: Path, thread_id: str | None = None, input_text: str | None = None) -> CodexTurn: ...

    def wait_for_task(self, thread_id: str, turn_id: str, on_idle: Callable[[], None] | None = None) -> dict: ...

    def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict: ...

    def interrupt_turn(self, thread_id: str, turn_id: str) -> dict: ...


def run_codex_app_server_task(
    task_dir: Path,
    project_root: Path | None = None,
    backend: AppServerTaskBackend | None = None,
    thread_id: str | None = None,
    on_turn_started: Callable[[CodexTurn], None] | None = None,
) -> CodexTurn:
    write_status(task_dir, "running")
    project_root = project_root or Path.cwd()
    close_transport = None
    if backend is None:
        transport = StdioAppServerTransport(cwd=project_root)
        close_transport = transport.close
        client = AppServerClient(transport)
        client.initialize()
        backend = CodexAppServerBackend(client, project_root=project_root)

    try:
        (task_dir / "codex-stream.jsonl").unlink(missing_ok=True)
        turn = _start_backend_task(backend, task_dir, thread_id=thread_id)
        if turn.turn_id is None:
            raise RuntimeError("codex app-server did not return an active turn id")
        if on_turn_started:
            on_turn_started(turn)
        control_offset = len(read_control_commands(task_dir))

        def process_controls() -> None:
            nonlocal control_offset
            commands = read_control_commands(task_dir)
            for command in commands[control_offset:]:
                _apply_control_command(backend, turn, command)
            control_offset = len(commands)

        process_controls()
        _wait_for_task(backend, turn, process_controls, task_dir=task_dir)
        _validate_outputs(task_dir)
        seed_chat_messages_from_task(
            task_dir,
            created_at=str(read_status(task_dir).get("created_at") or ""),
        )
        if thread_id and _append_assistant_message_from_stream(task_dir):
            pass
        else:
            append_assistant_message_from_artifacts(task_dir, read_artifacts(task_dir))
    except Exception as exc:
        write_status(task_dir, "failed", error=f"Codex app-server task failed: {exc}")
        raise
    finally:
        if close_transport:
            close_transport()

    write_status(task_dir, "completed")
    return turn


def _validate_outputs(task_dir: Path) -> None:
    for filename in REQUIRED_CODEX_OUTPUTS:
        path = task_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing Codex output: {path}")
    _validate_artifact_item_paths(read_artifacts(task_dir), task_dir=task_dir)


def _start_backend_task(backend: AppServerTaskBackend, task_dir: Path, thread_id: str | None) -> CodexTurn:
    input_text = _latest_append_instruction_text(task_dir) if thread_id else None
    params = inspect.signature(backend.start_task).parameters
    if "input_text" in params:
        return backend.start_task(task_dir, thread_id=thread_id, input_text=input_text)
    return backend.start_task(task_dir, thread_id=thread_id)


def _latest_append_instruction_text(task_dir: Path) -> str | None:
    for command in reversed(read_control_commands(task_dir)):
        if command.get("type") != "append_instruction":
            continue
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        text = payload.get("codex_input_text")
        if not isinstance(text, str) or not text.strip():
            text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _wait_for_task(
    backend: AppServerTaskBackend,
    turn: CodexTurn,
    on_idle: Callable[[], None],
    task_dir: Path | None = None,
) -> dict:
    params = inspect.signature(backend.wait_for_task).parameters
    kwargs = {}
    if "on_idle" in params:
        kwargs["on_idle"] = on_idle
    if "on_event" in params and task_dir is not None:
        kwargs["on_event"] = lambda event: _append_codex_stream_event(task_dir, event)
    if kwargs:
        return backend.wait_for_task(turn.thread_id, str(turn.turn_id), **kwargs)
    return backend.wait_for_task(turn.thread_id, str(turn.turn_id))


def _apply_control_command(
    backend: AppServerTaskBackend,
    turn: CodexTurn,
    command: dict,
) -> None:
    command_type = command.get("type")
    payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
    if command_type == "append_instruction":
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            backend.steer_turn(turn.thread_id, str(turn.turn_id), text)
    elif command_type == "interrupt":
        backend.interrupt_turn(turn.thread_id, str(turn.turn_id))


def _append_codex_stream_event(task_dir: Path, event: dict) -> None:
    text = _extract_codex_event_text(event)
    if not text:
        return
    payload = {"timestamp": datetime.now(UTC).isoformat(), "text": text}
    with (task_dir / "codex-stream.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _append_assistant_message_from_stream(task_dir: Path) -> dict | None:
    text = _latest_codex_stream_text(task_dir)
    if not text:
        return None
    return append_chat_message(task_dir, "assistant", text, source="codex_stream")


def _latest_codex_stream_text(task_dir: Path) -> str:
    path = task_dir / "codex-stream.jsonl"
    if not path.is_file():
        return ""
    for raw in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        text = str(payload.get("text") or "").strip() if isinstance(payload, dict) else ""
        if not text or text.startswith("Under-development features enabled:"):
            continue
        return text
    return ""


def _extract_codex_event_text(event: dict) -> str:
    candidates = [event.get("text"), event.get("delta"), event.get("message"), event.get("content")]
    params = event.get("params") if isinstance(event.get("params"), dict) else {}
    candidates.extend([params.get("text"), params.get("delta"), params.get("message"), params.get("content")])
    item = params.get("item") if isinstance(params.get("item"), dict) else {}
    candidates.extend([item.get("text"), item.get("delta"), item.get("message"), item.get("content")])
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
