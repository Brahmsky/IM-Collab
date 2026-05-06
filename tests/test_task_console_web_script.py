from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import scripts.task_console_web as task_console_web
from scripts.task_console_web import _make_codex_app_server_followup_runner


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
