from __future__ import annotations

import json
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from bridge.codex_task_runner import build_codex_task_prompt


class LineTransport(Protocol):
    def write_line(self, line: str) -> None: ...

    def read_line(self, timeout_seconds: float | None = None) -> str | None: ...


class StdioAppServerTransport:
    def __init__(
        self,
        command: Sequence[str] = ("codex", "app-server"),
        cwd: Path | None = None,
    ) -> None:
        self.process = subprocess.Popen(
            list(command),
            cwd=cwd.as_posix() if cwd else None,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def write_line(self, line: str) -> None:
        if self.process.stdin is None:
            raise RuntimeError("codex app-server stdin is closed")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def read_line(self, timeout_seconds: float | None = None) -> str | None:
        if self.process.stdout is None:
            raise RuntimeError("codex app-server stdout is closed")
        if timeout_seconds is not None:
            ready, _, _ = select.select([self.process.stdout], [], [], timeout_seconds)
            if not ready:
                return None
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"codex app-server stopped before response: {stderr.strip()}")
        return line.rstrip("\n")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()


class AppServerClient:
    def __init__(
        self,
        transport: LineTransport,
        client_name: str = "im-collab",
        client_title: str = "IM-Collab",
        client_version: str = "0.1",
    ) -> None:
        self.transport = transport
        self._next_id = 1
        self.client_name = client_name
        self.client_title = client_title
        self.client_version = client_version
        self._pending_messages: list[dict[str, Any]] = []

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": self.client_name,
                    "title": self.client_title,
                    "version": self.client_version,
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self.notify("initialized")
        return result

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self.transport.write_line(
            json.dumps(
                {"id": request_id, "method": method, "params": params or {}},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

        while True:
            response = self._read_transport_message()
            if response.get("id") != request_id:
                self._pending_messages.append(response)
                continue
            if "error" in response:
                error = response["error"]
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise RuntimeError(message or "codex app-server request failed")
            result = response.get("result", {})
            return result if isinstance(result, dict) else {"value": result}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self.transport.write_line(
            json.dumps(
                {"method": method, "params": params or {}},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    def wait_for_turn_completed(
        self,
        thread_id: str,
        turn_id: str,
        timeout_seconds: float = 1800,
        on_idle: Callable[[], None] | None = None,
        poll_interval_seconds: float = 0.5,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._pending_messages:
                message = self._pending_messages.pop(0)
            else:
                remaining = deadline - time.monotonic()
                read_timeout = min(poll_interval_seconds, max(0.0, remaining))
                message = self._read_transport_message(timeout_seconds=read_timeout)
                if message is None:
                    if on_idle:
                        on_idle()
                    continue
            if message.get("method") != "turn/completed":
                continue
            params = message.get("params") if isinstance(message.get("params"), dict) else {}
            if params.get("threadId") != thread_id and params.get("thread_id") != thread_id:
                continue
            turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
            if turn.get("id") != turn_id and turn.get("turnId") != turn_id and turn.get("turn_id") != turn_id:
                continue
            status = str(turn.get("status") or "")
            if status == "failed":
                error = turn.get("error") if isinstance(turn.get("error"), dict) else {}
                raise RuntimeError(str(error.get("message") or "codex turn failed"))
            return turn
        raise TimeoutError(f"timed out waiting for Codex turn {turn_id}")

    def _read_transport_message(self, timeout_seconds: float | None = None) -> dict[str, Any] | None:
        try:
            line = self.transport.read_line(timeout_seconds=timeout_seconds)
        except TypeError:
            line = self.transport.read_line()
        if line is None:
            return None
        message = json.loads(line)
        return message if isinstance(message, dict) else {"value": message}


@dataclass(frozen=True)
class CodexTurn:
    thread_id: str
    turn_id: str | None


class CodexAppServerBackend:
    def __init__(self, client: AppServerClient, project_root: Path) -> None:
        self.client = client
        self.project_root = project_root

    def start_task(self, task_dir: Path, thread_id: str | None = None) -> CodexTurn:
        if thread_id is None:
            thread = self.client.request(
                "thread/start",
                {
                    "cwd": self.project_root.as_posix(),
                    "approvalPolicy": "never",
                    "persistExtendedHistory": True,
                    "experimentalRawEvents": False,
                },
            )
            thread_id = _required_string(thread, "threadId")
        else:
            self.client.request("thread/resume", {"threadId": thread_id})
        turn = self.client.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": _text_input(build_codex_task_prompt(task_dir)),
                "cwd": self.project_root.as_posix(),
                "approvalPolicy": "never",
                "sandboxPolicy": {
                    "type": "workspaceWrite",
                    "writableRoots": [self.project_root.as_posix(), task_dir.as_posix()],
                    "networkAccess": True,
                },
            },
        )
        return CodexTurn(thread_id=thread_id, turn_id=_optional_turn_id(turn))

    def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict[str, Any]:
        return self.client.request(
            "turn/steer",
            {
                "threadId": thread_id,
                "expectedTurnId": turn_id,
                "input": _text_input(text),
            },
        )

    def interrupt_turn(self, thread_id: str, turn_id: str) -> dict[str, Any]:
        return self.client.request(
            "turn/interrupt",
            {
                "threadId": thread_id,
                "turnId": turn_id,
            },
        )

    def wait_for_task(
        self,
        thread_id: str,
        turn_id: str,
        on_idle: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        return self.client.wait_for_turn_completed(thread_id, turn_id, on_idle=on_idle)


def _text_input(text: str) -> list[dict[str, str]]:
    trimmed = text.strip()
    if not trimmed:
        raise ValueError("text input must not be empty")
    return [{"type": "text", "text": trimmed}]


def _required_string(data: dict[str, Any], key: str) -> str:
    value = _optional_string(data, key)
    if not value:
        raise RuntimeError(f"codex app-server response missing `{key}`")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key) or data.get(_snake_case(key))
    return value if isinstance(value, str) and value else None


def _optional_turn_id(data: dict[str, Any]) -> str | None:
    turn_id = _optional_string(data, "turnId")
    if turn_id:
        return turn_id
    turn = data.get("turn")
    if isinstance(turn, dict):
        return _optional_string(turn, "turnId") or _optional_string(turn, "id")
    return None


def _snake_case(value: str) -> str:
    chars: list[str] = []
    for char in value:
        if char.isupper():
            chars.append("_")
            chars.append(char.lower())
        else:
            chars.append(char)
    return "".join(chars).lstrip("_")
