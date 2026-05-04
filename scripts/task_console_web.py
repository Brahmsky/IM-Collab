from __future__ import annotations

import argparse
import os
import socket
import sys
import traceback
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.console_demo_seed import (
    DEMO_TASK_ID,
    ensure_local_smoke_demo_task,
    resolve_repo_relative_path,
)
from bridge.task_console_web import handle_console_action, render_console_html


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
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            qs = parse_qs(urlparse(self.path).query)
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
            try:
                flash = handle_console_action(tasks_root, form)
            except Exception as exc:
                flash = f"error: {exc}"
            stay = (form.get("redirect_task") or form.get("task_id") or "").strip() or None
            try:
                html = render_console_html(
                    tasks_root,
                    event_dir,
                    flash=flash,
                    selected_task_id=stay,
                    search_query="",
                )
            except Exception:
                html = _error_page_html(traceback.format_exc())
            self._send_html(html)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    if _loopback_host_arg(host):
        try:
            return _dualstack_loopback_server(port, Handler)
        except OSError:
            pass
        bind_host = "127.0.0.1"
    else:
        bind_host = host
    return ThreadingHTTPServer((bind_host, port), Handler)


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
    parser.add_argument("--print-url", action="store_true", help="Print the URL and exit without serving.")
    args = parser.parse_args()

    tasks_root = resolve_repo_relative_path(args.tasks_root, PROJECT_ROOT)
    event_dir = resolve_repo_relative_path(args.event_dir, PROJECT_ROOT)
    if args.ensure_demo:
        ensure_local_smoke_demo_task(tasks_root, PROJECT_ROOT)

    server = build_server(args.host, args.port, tasks_root, event_dir)
    port = _effective_tcp_port(server)
    _print_listen_urls(args.host, port)
    demo_status = tasks_root / DEMO_TASK_ID / "status.json"
    if demo_status.is_file():
        print(
            f"示例任务页: http://127.0.0.1:{port}/?task={DEMO_TASK_ID}",
            flush=True,
        )
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
