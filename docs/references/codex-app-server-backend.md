# Codex App-Server Backend

## Decision

IM-Collab should move toward Codex persistent sessions through `codex app-server`.

This is not a custom agent framework. The project-owned code is only a thin bridge from IM-Collab's durable task protocol to Codex's app-server protocol:

- IM-Collab owns Feishu ingress, task directories, bindings, status, artifacts, and delivery.
- Codex app-server owns persistent threads, turns, steer, interrupt, resume, skills, apps, and model/runtime controls.
- CodexMonitor remains a reference implementation for app-server lifecycle and cockpit UX, not a required deployed service.
- CliDeck is optional and no longer on the critical path.

## Current Spike

`bridge/codex_app_server.py` adds:

- `StdioAppServerTransport`: starts `codex app-server` over stdio.
- `AppServerClient`: sends JSON-RPC requests and notifications.
- `AppServerClient.initialize()`: performs the required `initialize` request and `initialized` notification.
- `CodexAppServerBackend.start_task()`: maps a task directory to `thread/start` and `turn/start`.
- `CodexAppServerBackend.steer_turn()`: maps operator/user additions to `turn/steer`.
- `CodexAppServerBackend.interrupt_turn()`: maps operator control to `turn/interrupt`.

`bridge/codex_app_server_task_runner.py` adds:

- `run_codex_app_server_task()`: runs one task through app-server, waits for the matching `turn/completed` notification, validates required task outputs, and updates `status.json`.

`bridge/task_binding.py` now preserves:

- `codex_thread_id`
- `active_turn_id`

`bridge/golembot_office_loop.py` now supports:

- `generator="app-server"` as a parallel execution path beside `local` and `codex`.

## Verified Locally

- Unit tests cover request ID generation, error propagation, initialize/initialized handshake, task-to-turn mapping, steer, interrupt, and durable binding fields.
- Real smoke test completed an `initialize` handshake with local `codex app-server`.
- Full repository test suite passed.

## Next Integration Step

Add a new runner path beside the current `codex exec` runner:

1. Start or reuse a Codex app-server process.
2. Create a task directory from the Feishu event as today.
3. Call `CodexAppServerBackend.start_task(task_dir)`.
4. Store returned `thread_id` and `turn_id` in `tasks/task-bindings.json`.
5. Consume app-server events until the turn completes.
6. Validate `plan.json`, `document.md`, `slides.md`, `whiteboard.mmd`, and `artifacts.json`.
7. Mark `status.json` completed or failed.
8. Publish artifacts through the existing Feishu delivery code.

Current command-line entry points accept the new generator:

```bash
rtk .venv/bin/python scripts/run_golembot_office_task.py \
  --message "生成项目方案" \
  --session-key "feishu:oc_123" \
  --chat-id "oc_123" \
  --sender-id "ou_456" \
  --task-id "gb-app-server-smoke" \
  --generator app-server
```

After that:

- New Feishu messages in the same session can target the existing `codex_thread_id`.
- If a turn is active, send `turn/steer`.
- If no turn is active, send `turn/start` on the existing thread.
- GUI controls can call `turn/interrupt` or append instructions through the same backend.

## Risks

- `codex app-server` is currently exposed as an experimental Codex CLI command.
- The app-server protocol can evolve, so IM-Collab should keep the adapter small and tested.
- `status.json` and `artifacts.json` must remain the competition-facing source of truth even when execution moves to persistent Codex threads.
