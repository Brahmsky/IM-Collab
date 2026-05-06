from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.codex_app_server import AppServerClient, CodexAppServerBackend, StdioAppServerTransport
from bridge.server_app import create_app
from bridge.task_console_web import make_codex_app_server_retry
from bridge.task_ops import retry_golembot_task

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


def _make_codex_app_server_followup_runner(project_root: Path):
    return make_codex_app_server_retry(
        project_root,
        retry=retry_golembot_task,
        transport_cls=StdioAppServerTransport,
        client_cls=AppServerClient,
        backend_cls=CodexAppServerBackend,
    )


def _resolve_repo_relative_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (PROJECT_ROOT / expanded).resolve()


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

    tasks_root = _resolve_repo_relative_path(args.tasks_root)
    event_dir = _resolve_repo_relative_path(args.event_dir)

    host = "127.0.0.1" if args.ipv4_only and _loopback_host_arg(args.host) else args.host
    port = args.port
    _print_listen_urls(args.host, port)
    if args.open:
        import threading
        import time
        import webbrowser

        def _browse() -> None:
            time.sleep(0.45)
            webbrowser.open(f"http://127.0.0.1:{port}/")

        threading.Thread(target=_browse, daemon=True).start()
    if args.print_url:
        return 0
    app = create_app(tasks_root=tasks_root, event_dir=event_dir)
    try:
        app.run(host=host, port=port, debug=False)
    except OSError as exc:
        print(f"监听失败: {exc}", file=sys.stderr)
        print("可尝试: --ipv4-only  （跳过 IPv6 双栈）或更换 --port。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
