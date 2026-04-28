# GolemBot Harness Spike

Date: 2026-04-28

## Purpose

Evaluate GolemBot as an agent-side harness gateway for IM-Collab.

The target shape is:

```text
Feishu IM
  -> GolemBot Gateway
  -> Codex engine
  -> IM-Collab task protocol / office tools
  -> Feishu delivery
```

This is different from traditional workflow platforms. GolemBot is relevant because it treats Codex, Claude Code, OpenCode, and Cursor as interchangeable coding-agent engines behind channel adapters.

## What Was Deployed

An isolated GolemBot assistant was created under `.experiments/golembot-codex`.

Configuration used:

- `engine: codex`
- local gateway on `127.0.0.1:3199`
- bearer token enabled
- Codex safe mode
- project root exposed through `codex.addDirs`
- Feishu channel configured with environment variables, not hardcoded secrets

The experiment directory is gitignored.

## Verified

- `golembot doctor` passed.
- GolemBot found the local Codex CLI.
- GolemBot found Codex ChatGPT OAuth at `~/.codex/auth.json`.
- HTTP gateway started successfully.
- Dashboard served at `http://127.0.0.1:3199/`.
- `/health` returned OK.
- `/api/channels` showed Feishu once credentials and SDK dependency were present.
- HTTP `/chat` invoked Codex and returned streamed SSE events.
- Codex read the project `AGENTS.md` through `codex.addDirs`.
- GolemBot persisted session mapping in `.golem/sessions.json`.
- Feishu WebSocket adapter connected successfully after installing `@larksuiteoapi/node-sdk` in the assistant directory.

## Important Findings

GolemBot is a close fit for the "big gateway" shape:

- It separates channel adapters from the coding-agent engine.
- It has a persistent HTTP gateway and Dashboard.
- It supports Feishu long-connection mode.
- Its Feishu adapter preserves `message_id`, `chat_id`, `sender_id`, `sender_name`, `chat_type`, `mentioned`, attachments, files, and raw event payload.
- It supports proactive send via `/api/send`.
- It supports group policy, mention-only behavior, group history, and multi-bot peer awareness.
- It stores `sessionKey -> Codex thread_id` mappings.

The biggest issue found:

- Current GolemBot `0.46.0` can fail native Codex resume when explicit `codex.sandbox` / `codex.approval` options are configured. The observed Codex error was that `codex exec resume` did not accept `--sandbox` in that argument position. GolemBot then fell back to restoring prior conversation history and starting a fresh Codex thread.

This means session continuity has two layers:

1. GolemBot conversation history can preserve conversational context.
2. Native Codex thread resume may require a config workaround or upstream patch.

## Session Management Requirement

For IM-Collab, session management must be explicit. Do not rely only on terminal state.

Recommended identity mapping:

```text
Feishu message
  message_id: platform id for dedupe and quote reply
  chat_id: stable conversation id
  chat_type: dm or group
  sender_id: user/bot identity

GolemBot
  conversationKey: channel + chat + optional thread
  sessionKey: stable agent session id
  engineSessionId: Codex thread id when resume works

IM-Collab
  task_id: durable task directory id
  status.json: queued/running/waiting_for_user/completed/failed
  artifacts.json: final deliverables
```

Recommended task mapping:

- Group `@bot` message starts or updates a conversation session.
- A concrete office request creates a `task_id`.
- Follow-up messages in the same Feishu conversation can update the active task if it is not completed.
- Completed tasks remain addressable by `task_id`.
- A new explicit request creates a new task even if it comes from the same chat.

Recommended storage:

- Keep GolemBot's `.golem/sessions.json` as the harness session store.
- Keep IM-Collab `tasks/<task_id>/status.json` and `artifacts.json` as the durable task store.
- Keep only a small session-to-task binding file in IM-Collab:

```text
tasks/task-bindings.json
```

with:

```json
{
  "feishu:<chat_id>": {
    "session_key": "feishu:<chat_id>",
    "active_task_id": "im-...",
    "codex_thread_id": "...",
    "updated_at": "..."
  }
}
```

## Integration Options

### Option A: GolemBot as Channel Gateway, Python Keeps Task Protocol

GolemBot receives Feishu messages and calls Codex. Codex writes files under `tasks/<task_id>`. Existing Python delivery helpers publish artifacts.

Pros:

- Strong harness gateway alignment.
- Minimal custom Feishu event code.
- Keeps Codex + superpowers as the executor.

Cons:

- Need to teach GolemBot/Codex to use IM-Collab task protocol.
- Need a clean delivery trigger after artifacts are ready.

### Option B: GolemBot Custom Adapter or Skill Calls Python Task API

GolemBot handles IM and session management. A custom skill or HTTP endpoint creates tasks and invokes delivery.

Pros:

- Clean separation between channel/session and office delivery.
- Python code shrinks to task API and Feishu office delivery helpers.

Cons:

- Requires writing a small adapter/API layer.
- Need to avoid duplicating GolemBot's own session store.

### Option C: Keep lark-cli Event Ingress for MVP, Use GolemBot Later

Continue current MVP path and use GolemBot as a reference until resume and task mapping are tested more.

Pros:

- Lowest risk.
- Current MVP already works.

Cons:

- Does not solve the "persistent harness gateway" concern as strongly.

## Recommendation

Use GolemBot as the first real gateway candidate.

Next implementation target:

1. Keep the current lark-cli MVP path intact.
2. Add a GolemBot-specific task instruction skill that forces Codex to create/update `tasks/<task_id>`.
3. Test one real Feishu message through GolemBot.
4. Verify the resulting session key, Codex thread id, task id, status, and artifacts.
5. Decide whether Python event consumer can be retired or kept only as fallback.

## Open Questions

- Can native Codex resume be fixed by GolemBot config only, or does GolemBot need an upstream patch for `codex exec resume` flags?
- Should final Feishu delivery be done by GolemBot's Feishu adapter or by existing lark-cli delivery helpers?
- Should `task_id` be one per user request or one long-lived task per Feishu thread?
- How should clarification questions map to `waiting_for_user` in `status.json`?
