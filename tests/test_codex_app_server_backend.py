from __future__ import annotations

import json
from pathlib import Path

import pytest

from bridge.codex_app_server import AppServerClient, CodexAppServerBackend
from bridge.codex_app_server_task_runner import run_codex_app_server_task
from bridge.task_protocol import create_task
from tests.test_codex_task_runner import write_codex_outputs


class FakeLineTransport:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = [json.dumps(response) for response in responses]
        self.writes: list[str] = []

    def write_line(self, line: str) -> None:
        self.writes.append(line)

    def read_line(self) -> str:
        if not self.responses:
            raise AssertionError("no fake response queued")
        return self.responses.pop(0)


def test_app_server_client_sends_json_rpc_requests_with_incrementing_ids() -> None:
    transport = FakeLineTransport(
        [
            {"id": 1, "result": {"threadId": "thread_123"}},
            {"id": 2, "result": {"turnId": "turn_456"}},
        ]
    )
    client = AppServerClient(transport)

    assert client.request("thread/start", {"cwd": "/repo"}) == {"threadId": "thread_123"}
    assert client.request("turn/start", {"threadId": "thread_123"}) == {"turnId": "turn_456"}

    assert json.loads(transport.writes[0]) == {"id": 1, "method": "thread/start", "params": {"cwd": "/repo"}}
    assert json.loads(transport.writes[1]) == {"id": 2, "method": "turn/start", "params": {"threadId": "thread_123"}}


def test_app_server_client_raises_remote_error_message() -> None:
    transport = FakeLineTransport([{"id": 1, "error": {"message": "bad thread"}}])
    client = AppServerClient(transport)

    with pytest.raises(RuntimeError, match="bad thread"):
        client.request("thread/resume", {"threadId": "missing"})


def test_app_server_client_initializes_protocol_before_real_work() -> None:
    transport = FakeLineTransport([{"id": 1, "result": {"protocolVersion": 1}}])
    client = AppServerClient(transport, client_name="im-collab", client_version="0.1")

    client.initialize()

    initialize = json.loads(transport.writes[0])
    initialized = json.loads(transport.writes[1])
    assert initialize == {
        "id": 1,
        "method": "initialize",
        "params": {
            "clientInfo": {"name": "im-collab", "title": "IM-Collab", "version": "0.1"},
            "capabilities": {"experimentalApi": True},
        },
    }
    assert initialized == {"method": "initialized", "params": {}}


def test_codex_app_server_backend_starts_thread_and_turn_for_task(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")
    transport = FakeLineTransport(
        [
            {"id": 1, "result": {"threadId": "thread_123"}},
            {"id": 2, "result": {"turnId": "turn_456"}},
        ]
    )
    backend = CodexAppServerBackend(AppServerClient(transport), project_root=Path("/repo"))

    result = backend.start_task(task_dir)

    assert result.thread_id == "thread_123"
    assert result.turn_id == "turn_456"
    thread_start = json.loads(transport.writes[0])
    turn_start = json.loads(transport.writes[1])
    assert thread_start["method"] == "thread/start"
    assert thread_start["params"]["cwd"] == "/repo"
    assert thread_start["params"]["approvalPolicy"] == "never"
    assert turn_start["method"] == "turn/start"
    assert turn_start["params"]["threadId"] == "thread_123"
    assert turn_start["params"]["cwd"] == "/repo"
    assert turn_start["params"]["sandboxPolicy"]["type"] == "workspaceWrite"
    assert task_dir.as_posix() in turn_start["params"]["sandboxPolicy"]["writableRoots"]
    assert turn_start["params"]["input"][0]["type"] == "text"
    assert "Required outputs" in turn_start["params"]["input"][0]["text"]


def test_codex_app_server_backend_reads_nested_turn_id_from_start_response(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")
    transport = FakeLineTransport(
        [
            {"id": 1, "result": {"threadId": "thread_123"}},
            {"id": 2, "result": {"turn": {"id": "turn_nested", "status": "running"}}},
        ]
    )
    backend = CodexAppServerBackend(AppServerClient(transport), project_root=Path("/repo"))

    result = backend.start_task(task_dir)

    assert result.turn_id == "turn_nested"


def test_codex_app_server_backend_can_steer_and_interrupt_active_turn() -> None:
    transport = FakeLineTransport(
        [
            {"id": 1, "result": {"accepted": True}},
            {"id": 2, "result": {"interrupted": True}},
        ]
    )
    backend = CodexAppServerBackend(AppServerClient(transport), project_root=Path("/repo"))

    assert backend.steer_turn("thread_123", "turn_456", "补充移动端同步说明") == {"accepted": True}
    assert backend.interrupt_turn("thread_123", "turn_456") == {"interrupted": True}

    steer = json.loads(transport.writes[0])
    interrupt = json.loads(transport.writes[1])
    assert steer == {
        "id": 1,
        "method": "turn/steer",
        "params": {
            "threadId": "thread_123",
            "expectedTurnId": "turn_456",
            "input": [{"type": "text", "text": "补充移动端同步说明"}],
        },
    }
    assert interrupt == {
        "id": 2,
        "method": "turn/interrupt",
        "params": {"threadId": "thread_123", "turnId": "turn_456"},
    }


def test_app_server_client_waits_for_matching_turn_completed_notification() -> None:
    transport = FakeLineTransport(
        [
            {"method": "turn/completed", "params": {"threadId": "other", "turn": {"id": "turn_x", "status": "completed"}}},
            {
                "method": "turn/completed",
                "params": {"threadId": "thread_123", "turn": {"id": "turn_456", "status": "completed"}},
            },
        ]
    )
    client = AppServerClient(transport)

    result = client.wait_for_turn_completed("thread_123", "turn_456")

    assert result["status"] == "completed"


def test_app_server_client_raises_when_turn_fails() -> None:
    transport = FakeLineTransport(
        [
            {
                "method": "turn/completed",
                "params": {
                    "threadId": "thread_123",
                    "turn": {"id": "turn_456", "status": "failed", "error": {"message": "tool failed"}},
                },
            }
        ]
    )
    client = AppServerClient(transport)

    with pytest.raises(RuntimeError, match="tool failed"):
        client.wait_for_turn_completed("thread_123", "turn_456")


def test_run_codex_app_server_task_marks_completed_after_turn_finishes(tmp_path: Path) -> None:
    task_dir = create_task(tmp_path, "im-om_123", "Generate a deck.")

    class FakeBackend:
        def start_task(self, task_path: Path):
            write_codex_outputs(task_path)
            from bridge.codex_app_server import CodexTurn

            return CodexTurn(thread_id="thread_123", turn_id="turn_456")

        def wait_for_task(self, thread_id: str, turn_id: str):
            return {"id": turn_id, "status": "completed"}

    result = run_codex_app_server_task(task_dir, project_root=tmp_path, backend=FakeBackend())

    assert result.thread_id == "thread_123"
    assert result.turn_id == "turn_456"
