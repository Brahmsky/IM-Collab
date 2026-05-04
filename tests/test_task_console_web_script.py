from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.task_console_web import _task_stream_payload, build_server


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
    assert "补充团队分工。" in payload["message_html"]
    assert "<!DOCTYPE html>" not in json.dumps(payload)
    assert seen["task_dir"] == "task-1"
    assert _task_stream_payload(tasks_root, "task-1")["done"] is False
