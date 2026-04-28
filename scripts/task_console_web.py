from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bridge.task_console_web import handle_console_action, render_console_html


def build_server(
    host: str,
    port: int,
    tasks_root: Path,
    event_dir: Path,
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._send_html(render_console_html(tasks_root, event_dir))

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            form = {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}
            try:
                flash = handle_console_action(tasks_root, form)
            except Exception as exc:
                flash = f"error: {exc}"
            self._send_html(render_console_html(tasks_root, event_dir, flash=flash))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IM-Collab local web console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--tasks-root", type=Path, default=Path("tasks"))
    parser.add_argument("--event-dir", type=Path, default=Path("events"))
    parser.add_argument("--print-url", action="store_true", help="Print the URL and exit without serving.")
    args = parser.parse_args()

    server = build_server(args.host, args.port, args.tasks_root, args.event_dir)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    print(url, flush=True)
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
