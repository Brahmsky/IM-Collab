#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PORT="${IM_COLLAB_CONSOLE_PORT:-8765}"
LOG_DIR="$ROOT_DIR/logs/services"

printf 'pid files:\n'
if compgen -G "$LOG_DIR/*.pid" >/dev/null; then
  for pid_file in "$LOG_DIR"/*.pid; do
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    name="$(basename "$pid_file" .pid)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      printf '  %-20s running pid=%s\n' "$name" "$pid"
    else
      printf '  %-20s stale pid=%s\n' "$name" "${pid:-}"
    fi
  done
else
  printf '  none\n'
fi

printf '\nprocesses:\n'
pgrep -af "scripts/task_console_web.py|codex app-server|golembot gateway" || true

printf '\nport %s:\n' "$PORT"
lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true

printf '\nlogs:\n'
printf '  %s/task_console_web.log\n' "$LOG_DIR"
printf '  %s/golembot_gateway.log\n' "$LOG_DIR"
