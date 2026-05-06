#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

QUIET=0
if [[ "${1:-}" == "--quiet" ]]; then
  QUIET=1
fi

LOG_DIR="$ROOT_DIR/logs/services"
mkdir -p "$LOG_DIR"

say() {
  if [[ "$QUIET" != "1" ]]; then
    printf '%s\n' "$*"
  fi
}

stop_pid_file() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] || return 0
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    say "stopped $(basename "$pid_file" .pid) pid=$pid"
  fi
  rm -f "$pid_file"
}

for pid_file in "$LOG_DIR"/*.pid; do
  [[ -e "$pid_file" ]] || continue
  stop_pid_file "$pid_file"
done

pkill -f "scripts/task_console_web.py" 2>/dev/null || true
pkill -f "codex app-server" 2>/dev/null || true
pkill -f "golembot gateway -d .experiments/golembot-codex" 2>/dev/null || true
pkill -f "scripts/subscribe_feishu_events.py" 2>/dev/null || true
pkill -f "scripts/run_event_consumer.py" 2>/dev/null || true
pkill -f "lark-cli event \\+subscribe" 2>/dev/null || true

say "services stopped"
