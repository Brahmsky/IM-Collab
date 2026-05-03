from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Protocol

from bridge.codex_app_server import AppServerClient, CodexAppServerBackend, CodexTurn, StdioAppServerTransport
from bridge.codex_task_runner import REQUIRED_CODEX_OUTPUTS, _validate_artifact_item_paths
from bridge.task_protocol import read_artifacts
from bridge.task_control import read_control_commands
from bridge.task_protocol import write_status


class AppServerTaskBackend(Protocol):
    def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn: ...

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
        turn = backend.start_task(task_dir, thread_id=thread_id)
        if turn.turn_id is None:
            raise RuntimeError("codex app-server did not return an active turn id")
        if on_turn_started:
            on_turn_started(turn)
        control_offset = 0

        def process_controls() -> None:
            nonlocal control_offset
            commands = read_control_commands(task_dir)
            for command in commands[control_offset:]:
                _apply_control_command(backend, turn, command)
            control_offset = len(commands)

        process_controls()
        _wait_for_task(backend, turn, process_controls)
        _validate_outputs(task_dir)
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


def _wait_for_task(
    backend: AppServerTaskBackend,
    turn: CodexTurn,
    on_idle: Callable[[], None],
) -> dict:
    if "on_idle" in inspect.signature(backend.wait_for_task).parameters:
        return backend.wait_for_task(turn.thread_id, str(turn.turn_id), on_idle=on_idle)
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
