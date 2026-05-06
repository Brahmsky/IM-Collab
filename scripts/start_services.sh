#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST="${IM_COLLAB_CONSOLE_HOST:-127.0.0.1}"
PORT="${IM_COLLAB_CONSOLE_PORT:-8765}"
LOG_DIR="$ROOT_DIR/logs/services"
EVENT_DIR="${IM_COLLAB_EVENT_DIR:-events/im}"
BOT_OPEN_ID="${IM_COLLAB_BOT_OPEN_ID:-}"
mkdir -p "$LOG_DIR"

run_bg() {
  local name="$1"
  shift
  local pid_file="$LOG_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"
  setsid "$@" >"$log_file" 2>&1 < /dev/null &
  echo "$!" > "$pid_file"
  printf '%s pid=%s log=%s\n' "$name" "$(cat "$pid_file")" "$log_file"
}

wait_for_http() {
  local url="$1"
  for _ in $(seq 1 30); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

bash "$ROOT_DIR/scripts/stop_services.sh" --quiet

run_bg task_console_web \
  rtk .venv/bin/python scripts/task_console_web.py \
    --host "$HOST" \
    --port "$PORT" \
    --ipv4-only

run_bg golembot_gateway \
  rtk npm exec -- golembot gateway -d .experiments/golembot-codex --verbose

run_bg feishu_listener \
  rtk .venv/bin/python scripts/subscribe_feishu_events.py \
    --output-dir "$EVENT_DIR"

consumer_args=(
  rtk .venv/bin/python scripts/run_event_consumer.py
  --event-dir "$EVENT_DIR"
  --dispatch golembot
  --publish
  --execute
  --generator app-server
)
if [[ -n "$BOT_OPEN_ID" ]]; then
  consumer_args+=(--bot-open-id "$BOT_OPEN_ID")
fi
run_bg event_consumer "${consumer_args[@]}"

url="http://$HOST:$PORT/"
if wait_for_http "$url"; then
  printf 'web console: %s\n' "$url"
else
  printf 'web console did not become ready in time, see %s\n' "$LOG_DIR/task_console_web.log" >&2
  exit 1
fi

printf 'status: bash scripts/status_services.sh\n'
printf 'stop:   bash scripts/stop_services.sh\n'
