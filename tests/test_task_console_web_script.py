from __future__ import annotations

import json
import http.client
import os
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from bridge.codex_app_server import CodexTurn
from bridge.golembot_office_loop import run_golembot_office_task
import scripts.task_console_web as task_console_web
from scripts.task_console_web import _make_codex_app_server_followup_runner, _task_stream_payload, build_server
from tests.test_codex_task_runner import write_codex_outputs


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_task_console_web_script_prints_startup_url() -> None:
    repo = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console_web.py"),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--print-url",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert completed.stdout.startswith("http://127.0.0.1:")


def test_task_console_web_script_default_port_from_env() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["IM_COLLAB_CONSOLE_PORT"] = "19999"

    completed = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "task_console_web.py"),
            "--host",
            "127.0.0.1",
            "--print-url",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )

    first_line = completed.stdout.strip().splitlines()[0]
    assert first_line == "http://127.0.0.1:19999"


def test_task_console_web_json_append_does_not_return_full_page_and_triggers_codex(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    write_json(
        task_dir / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    (task_dir / "request.md").write_text(
        "session_key: feishu:oc_group\nchat_id: oc_group\nsender_id: ou_user\n\n## User Message\n生成材料\n",
        encoding="utf-8",
    )
    seen: dict[str, str] = {}

    def fake_followup_runner(followup_task_dir: Path) -> None:
        seen["task_dir"] = followup_task_dir.name

    server = build_server(
        "127.0.0.1",
        0,
        tasks_root,
        tmp_path / "events",
        ipv4_only=True,
        followup_runner=fake_followup_runner,
        run_followup_in_background=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        body = urllib.parse.urlencode(
            {"action": "append", "task_id": "task-1", "redirect_task": "task-1", "text": "补充团队分工。"}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/",
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            content_type = response.headers["Content-Type"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert content_type == "application/json; charset=utf-8"
    assert payload["ok"] is True
    assert payload["task_id"] == "task-1"
    assert payload["backend"] == "codex_app_server"
    assert payload["stream_url"] == "/api/task-stream?task=task-1"
    assert 'data-role="chat-message-user"' in payload["message_html"]
    assert 'data-role="chat-message-assistant-live"' in payload["typing_html"]
    assert "补充团队分工。" in payload["message_html"]
    assert "<!DOCTYPE html>" not in json.dumps(payload)
    assert seen["task_dir"] == "task-1"
    assert _task_stream_payload(tasks_root, "task-1")["done"] is False


def test_task_console_web_json_append_persists_message_before_followup_runner(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    write_json(
        task_dir / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    (task_dir / "request.md").write_text(
        "session_key: feishu:oc_group\nchat_id: oc_group\nsender_id: ou_user\n\n## User Message\n生成材料\n",
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_followup_runner(followup_task_dir: Path) -> None:
        commands = [
            json.loads(line)
            for line in (followup_task_dir / "control.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        seen["commands"] = commands

    server = build_server(
        "127.0.0.1",
        0,
        tasks_root,
        tmp_path / "events",
        ipv4_only=True,
        followup_runner=fake_followup_runner,
        run_followup_in_background=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        body = urllib.parse.urlencode(
            {"action": "append", "task_id": "task-1", "redirect_task": "task-1", "text": "你好，回复"}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/",
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["ok"] is True
    commands = seen["commands"]
    assert isinstance(commands, list)
    assert commands[-1]["type"] == "append_instruction"
    assert commands[-1]["payload"]["source"] == "gui"
    assert commands[-1]["payload"]["kind"] == "operator_followup"
    assert commands[-1]["payload"]["text"] == "你好，回复"


def test_task_console_web_plain_post_redirects_to_get_after_append(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    write_json(
        task_dir / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    (task_dir / "request.md").write_text(
        "session_key: feishu:oc_group\nchat_id: oc_group\nsender_id: ou_user\n\n## User Message\n生成材料\n",
        encoding="utf-8",
    )

    server = build_server(
        "127.0.0.1",
        0,
        tasks_root,
        tmp_path / "events",
        ipv4_only=True,
        followup_runner=lambda _task_dir: None,
        run_followup_in_background=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        body = urllib.parse.urlencode(
            {"action": "append", "task_id": "task-1", "redirect_task": "task-1", "text": "你好"}
        )
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = conn.getresponse()
        response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 303
    assert response.getheader("Location") == "/?task=task-1"


def test_task_console_web_json_append_reuses_thread_without_resteering_preexisting_message(tmp_path: Path) -> None:
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "task-1"
    write_json(
        task_dir / "status.json",
        {
            "task_id": "task-1",
            "state": "completed",
            "created_at": "2026-04-28T01:00:00+00:00",
            "updated_at": "2026-04-28T01:00:00+00:00",
            "error": None,
        },
    )
    write_json(
        task_dir / "artifacts.json",
        {
            "task_id": "task-1",
            "summary": "旧材料",
            "next_steps": [],
            "items": [{"id": "document", "kind": "document", "path": "document.md"}],
        },
    )
    (task_dir / "document.md").write_text("旧材料\n", encoding="utf-8")
    (task_dir / "request.md").write_text(
        "session_key: feishu:oc_group\nchat_id: oc_group\nsender_id: ou_user\n\n## User Message\n生成材料\n",
        encoding="utf-8",
    )
    write_json(
        tasks_root / "task-bindings.json",
        {
            "feishu:oc_group": {
                "session_key": "feishu:oc_group",
                "chat_id": "oc_group",
                "last_task_id": "task-1",
                "codex_thread_id": "thread_existing",
            }
        },
    )
    seen: dict[str, object] = {"steers": []}

    class FakeAppServerBackend:
        def start_task(self, followup_task_dir: Path, thread_id: str | None = None) -> CodexTurn:
            seen["thread_id"] = thread_id
            return CodexTurn(thread_id=thread_id or "thread_new", turn_id="turn_followup")

        def wait_for_task(self, thread_id: str, turn_id: str, on_idle=None) -> dict:
            assert on_idle is not None
            on_idle()
            write_codex_outputs(task_dir)
            return {"id": turn_id, "status": "completed"}

        def steer_turn(self, thread_id: str, turn_id: str, text: str) -> dict:
            seen["steers"].append((thread_id, turn_id, text))
            return {"accepted": True}

        def interrupt_turn(self, thread_id: str, turn_id: str) -> dict:
            raise AssertionError("interrupt should not be called")

    def followup_runner(followup_task_dir: Path) -> None:
        run_golembot_office_task(
            message="你好，回复",
            session_key="feishu:oc_group",
            chat_id="oc_group",
            sender_id="ou_user",
            tasks_root=tasks_root,
            task_id=followup_task_dir.name,
            generator="app-server",
            publish=False,
            codex_backend=FakeAppServerBackend(),
        )

    server = build_server(
        "127.0.0.1",
        0,
        tasks_root,
        tmp_path / "events",
        ipv4_only=True,
        followup_runner=followup_runner,
        run_followup_in_background=False,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        body = urllib.parse.urlencode(
            {"action": "append", "task_id": "task-1", "redirect_task": "task-1", "text": "你好，回复"}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/",
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert payload["ok"] is True
    assert seen["thread_id"] == "thread_existing"
    assert seen["steers"] == []


def test_default_followup_runner_reuses_one_app_server_backend_for_session(tmp_path: Path, monkeypatch) -> None:
    tasks_root = tmp_path / "tasks"
    calls: list[object] = []

    class FakeTransport:
        instances = 0

        def __init__(self, cwd=None):
            FakeTransport.instances += 1
            self.cwd = cwd

        def close(self) -> None:
            return None

    class FakeClient:
        def __init__(self, transport):
            self.transport = transport

        def initialize(self):
            return {"ok": True}

    class FakeBackend:
        def __init__(self, client, project_root: Path):
            self.client = client
            self.project_root = project_root

    def fake_retry(task_dir: Path, generator: str = "app-server", publish: bool = False, codex_backend=None):
        calls.append(codex_backend)
        return {"task_id": task_dir.name}

    monkeypatch.setattr(task_console_web, "StdioAppServerTransport", FakeTransport)
    monkeypatch.setattr(task_console_web, "AppServerClient", FakeClient)
    monkeypatch.setattr(task_console_web, "CodexAppServerBackend", FakeBackend)
    monkeypatch.setattr(task_console_web, "retry_golembot_task", fake_retry)

    runner = _make_codex_app_server_followup_runner(tmp_path)
    runner(tasks_root / "task-1")
    runner(tasks_root / "task-1")

    assert FakeTransport.instances == 1
    assert len(calls) == 2
    assert calls[0] is calls[1]
