from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import traceback
from datetime import UTC, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.console_demo_seed import (
    DEMO_TASK_ID,
    ensure_local_smoke_demo_task,
    resolve_repo_relative_path,
)
from bridge.cockpit_console_html import (
    render_assistant_typing_fragment,
    render_assistant_bubble_fragment,
    render_pending_reply_marker_fragment,
    render_task_chat_fragment,
    render_user_chat_message_fragment,
)
from bridge.codex_app_server import AppServerClient, CodexAppServerBackend, StdioAppServerTransport
from bridge.task_control import read_control_commands
from bridge.task_console_web import handle_console_action, render_console_html
from bridge.task_index import build_task_index
from bridge.task_ops import retry_golembot_task
from bridge.task_protocol import read_status

FollowupRunner = Callable[[Path], None]


def _default_console_port() -> int:
    raw = os.environ.get("IM_COLLAB_CONSOLE_PORT", "").strip()
    if raw.isdigit():
        p = int(raw)
        if 1 <= p <= 65535:
            return p
    return 8765


def _loopback_host_arg(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _dualstack_loopback_server(
    port: int,
    handler: type[BaseHTTPRequestHandler],
) -> ThreadingHTTPServer:
    """Listen on ::1 with IPv4-mapped IPv6 so http://localhost works when it resolves to ::1."""

    class _DualStackLoopback(ThreadingHTTPServer):
        address_family = socket.AF_INET6

        def server_bind(self) -> None:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

    return _DualStackLoopback(("::1", port, 0, 0), handler)


def build_server(
    host: str,
    port: int,
    tasks_root: Path,
    event_dir: Path,
    *,
    ipv4_only: bool = False,
    followup_runner: FollowupRunner | None = None,
    run_followup_in_background: bool = True,
) -> ThreadingHTTPServer:
    followup_runner = followup_runner or _make_codex_app_server_followup_runner(PROJECT_ROOT)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed_url = urlparse(self.path)
            qs = parse_qs(parsed_url.query)
            if parsed_url.path == "/api/task-stream":
                self._send_task_stream((qs.get("task") or [""])[0])
                return
            task = (qs.get("task") or [None])[0]
            q = (qs.get("q") or [""])[0]
            try:
                html = render_console_html(
                    tasks_root,
                    event_dir,
                    selected_task_id=task,
                    search_query=q,
                )
            except Exception:
                html = _error_page_html(traceback.format_exc())
            self._send_html(html)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            form = {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}
            if self._wants_json():
                self._handle_json_post(form)
                return
            try:
                flash = handle_console_action(tasks_root, form)
            except Exception as exc:
                flash = f"error: {exc}"
            stay = (form.get("redirect_task") or form.get("task_id") or "").strip() or None
            self._redirect_after_post(stay, form.get("q", ""), flash)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _wants_json(self) -> bool:
            accept = self.headers.get("Accept", "")
            requested_with = self.headers.get("X-Requested-With", "")
            return "application/json" in accept or requested_with.lower() in {"fetch", "xmlhttprequest"}

        def _handle_json_post(self, form: dict[str, str]) -> None:
            try:
                handle_console_action(tasks_root, form)
                backend = ""
                if form.get("action") == "append":
                    backend = _trigger_real_codex_backend(
                        tasks_root / form.get("task_id", ""),
                        followup_runner,
                        run_followup_in_background=run_followup_in_background,
                    )
                payload = {
                    "ok": True,
                    "task_id": form.get("task_id", ""),
                    "backend": backend,
                    "message_html": render_user_chat_message_fragment(form.get("text", "")),
                    "pending_marker_html": render_pending_reply_marker_fragment(),
                    "typing_html": render_assistant_typing_fragment(),
                    "stream_url": f"/api/task-stream?task={quote(form.get('task_id', ''), safe='')}",
                }
                self._send_json(payload)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)

        def _send_task_stream(self, task_id: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            last_payload = ""
            for _ in range(90):
                payload = _task_stream_payload(tasks_root, task_id)
                encoded = json.dumps(payload, ensure_ascii=False)
                if encoded != last_payload:
                    try:
                        self.wfile.write(f"data: {encoded}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except BrokenPipeError:
                        return
                    last_payload = encoded
                if payload.get("done"):
                    return
                time.sleep(1)

        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _redirect_after_post(self, task_id: str | None, q: str, flash: str) -> None:
            params = []
            if task_id:
                params.append(("task", task_id))
            if q:
                params.append(("q", q))
            if flash:
                params.append(("flash", flash))
            location = "/"
            if params:
                location += "?" + "&".join(f"{quote(key, safe='')}={quote(value, safe='')}" for key, value in params)
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    if _loopback_host_arg(host):
        if ipv4_only:
            bind_host = "127.0.0.1"
        else:
            try:
                return _dualstack_loopback_server(port, Handler)
            except OSError:
                pass
            bind_host = "127.0.0.1"
    else:
        bind_host = host
    return ThreadingHTTPServer((bind_host, port), Handler)


class _SharedCodexAppServerFollowupRunner:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._lock = threading.Lock()
        self._transport: StdioAppServerTransport | None = None
        self._backend: CodexAppServerBackend | None = None

    def __call__(self, task_dir: Path) -> None:
        with self._lock:
            retry_golembot_task(
                task_dir,
                generator="app-server",
                publish=False,
                codex_backend=self._get_backend(),
            )

    def _get_backend(self) -> CodexAppServerBackend:
        if self._backend is None:
            self._transport = StdioAppServerTransport(cwd=self.project_root)
            client = AppServerClient(self._transport)
            client.initialize()
            self._backend = CodexAppServerBackend(client, project_root=self.project_root)
        return self._backend

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._backend = None


def _make_codex_app_server_followup_runner(project_root: Path) -> _SharedCodexAppServerFollowupRunner:
    return _SharedCodexAppServerFollowupRunner(project_root)


def _trigger_real_codex_backend(
    task_dir: Path,
    followup_runner: FollowupRunner,
    *,
    run_followup_in_background: bool,
) -> str:
    status = read_status(task_dir)
    if status.get("state") == "running":
        return "active_turn"
    if run_followup_in_background:
        threading.Thread(target=followup_runner, args=(task_dir,), daemon=True).start()
    else:
        followup_runner(task_dir)
    return "codex_app_server"


def _task_stream_payload(tasks_root: Path, task_id: str) -> dict[str, object]:
    selected = next((task for task in build_task_index(tasks_root) if task.task_id == task_id), None)
    if selected is None:
        return {"ok": False, "done": True, "error": "task not found"}
    pending_controls = _has_control_newer_than_status(selected.path)
    return {
        "ok": True,
        "done": selected.state in {"failed", "waiting_for_user"} or (selected.state == "completed" and not pending_controls),
        "state": selected.state,
        "chat_html": render_task_chat_fragment(selected),
        "assistant_html": render_assistant_bubble_fragment(selected),
        "pending_controls": pending_controls,
    }


def _has_control_newer_than_status(task_dir: Path) -> bool:
    try:
        status = read_status(task_dir)
    except Exception:
        return False
    status_time = _parse_iso_datetime(str(status.get("updated_at") or ""))
    if status_time is None:
        return False
    for command in read_control_commands(task_dir):
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


def _error_page_html(trace: str) -> str:
    return (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>控制台错误</title></head><body><h1>渲染失败</h1>"
        f"<pre>{escape(trace)}</pre></body></html>"
    )


def _effective_tcp_port(server: ThreadingHTTPServer) -> int:
    addr = server.server_address
    return int(addr[1])


def _print_listen_urls(host_arg: str, effective_port: int) -> None:
    """Print URLs humans should open (first line stays http://127.0.0.1: for tests / bookmarks)."""
    if _loopback_host_arg(host_arg):
        print(f"http://127.0.0.1:{effective_port}", flush=True)
        print(f"http://localhost:{effective_port}", flush=True)
        print(
            "提示：若曾只用 localhost 打不开，请优先用第一行地址；"
            "本服务在环回上已尽量同时兼容 IPv4 / IPv6。",
            flush=True,
        )
        return
    print(f"http://{host_arg}:{effective_port}", flush=True)
    if host_arg == "0.0.0.0":
        print("（监听 0.0.0.0 时也可用本机局域网 IP + 端口从其他设备访问。）", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IM-Collab local web console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port",
        type=int,
        default=_default_console_port(),
        help="Listen port (default: 8765, or IM_COLLAB_CONSOLE_PORT).",
    )
    parser.add_argument(
        "--tasks-root",
        type=Path,
        default=Path("tasks"),
        help="Task directory (relative paths are resolved from the repository root, not cwd).",
    )
    parser.add_argument(
        "--event-dir",
        type=Path,
        default=Path("events"),
        help="Event directory (relative paths are resolved from the repository root).",
    )
    parser.add_argument(
        "--ensure-demo",
        action="store_true",
        help=f"Create {DEMO_TASK_ID} sample task + bindings if missing (for cockpit preview).",
    )
    parser.add_argument(
        "--ipv4-only",
        action="store_true",
        help="Listen on 127.0.0.1 only (skip IPv6 dual-stack). Use when connection to localhost fails.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the demo task URL in the default browser after the server starts.",
    )
    parser.add_argument("--print-url", action="store_true", help="Print the URL and exit without serving.")
    args = parser.parse_args()

    tasks_root = resolve_repo_relative_path(args.tasks_root, PROJECT_ROOT)
    event_dir = resolve_repo_relative_path(args.event_dir, PROJECT_ROOT)
    if args.ensure_demo:
        ensure_local_smoke_demo_task(tasks_root, PROJECT_ROOT)

    try:
        server = build_server(
            args.host,
            args.port,
            tasks_root,
            event_dir,
            ipv4_only=args.ipv4_only,
        )
    except OSError as exc:
        print(f"监听失败: {exc}", file=sys.stderr)
        print("可尝试: --ipv4-only  （跳过 IPv6 双栈）或更换 --port。", file=sys.stderr)
        return 1

    port = _effective_tcp_port(server)
    _print_listen_urls(args.host, port)
    demo_status = tasks_root / DEMO_TASK_ID / "status.json"
    demo_url = f"http://127.0.0.1:{port}/?task={DEMO_TASK_ID}"
    if demo_status.is_file():
        print(f"示例任务页: {demo_url}", flush=True)
    if args.open:
        import threading
        import time
        import webbrowser

        def _browse() -> None:
            time.sleep(0.45)
            webbrowser.open(demo_url if demo_status.is_file() else f"http://127.0.0.1:{port}/")

        threading.Thread(target=_browse, daemon=True).start()
    if args.print_url:
        server.server_close()
        return 0
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
