---
name: golembot-task-protocol
description: Use when a GolemBot or other IM harness gateway message needs to start, continue, clarify, or complete an IM-Collab office task.
---

# GolemBot Task Protocol

## Core Rule

GolemBot is the channel and harness gateway. It is not the project planner of record. Codex + superpowers still owns reasoning and execution; the durable task state lives in `tasks/<task_id>/`.

## Session Mapping

For every incoming IM task, keep these identities distinct:

| Layer | Identifier | Purpose |
| --- | --- | --- |
| Feishu | `message_id` | dedupe and quote reply |
| Feishu | `chat_id` + optional thread | conversation scope |
| GolemBot | `sessionKey` | long-lived harness session |
| GolemBot | `engineSessionId` | Codex thread id when native resume works |
| IM-Collab | `task_id` | durable office task directory |

Never use terminal text as the completion signal. Use `status.json` and `artifacts.json`.

## Task Lifecycle

1. Read the incoming request and conversation context.
2. If this is a new concrete office request, create a new `tasks/<task_id>/` with `request.md` and `status.json`.
3. If the message is a clarification or correction for an active unfinished task in the same session, update that task instead of creating a duplicate.
4. Use `waiting_for_user` when required information is missing.
5. Use `running` while generating artifacts.
6. Use `completed` only after `artifacts.json` contains the final deliverables.
7. Use `failed` with a clear error if the task cannot continue.

## Required Files

Each task directory must contain:

- `request.md`: original user request, IM metadata, context, constraints, and acceptance criteria.
- `status.json`: `task_id`, state, timestamps, and optional error.
- `artifacts.json`: final links/files/summaries after delivery.

Generated local office drafts should use:

- `document.md`
- `slides.md`
- `whiteboard.mmd`
- `plan.json`

## Tool Entry

When a GolemBot conversation requests a concrete office deliverable, prefer the repository script instead of hand-assembling task files:

```bash
rtk .venv/bin/python scripts/run_golembot_office_task.py \
  --message "<user request>" \
  --session-key "<golembot session key>" \
  --chat-id "<feishu chat id>" \
  --sender-id "<feishu sender id>" \
  --task-id "im-<message id>" \
  --generator codex
```

Do not use `--publish` inside the GolemBot/Codex runtime. Codex should only generate local task artifacts. The Python Bridge publishes real Feishu office artifacts after GolemBot returns.

The script returns JSON. Send `reply_markdown` back to the current GolemBot conversation.

`--generator local` is only for unit tests and local smoke checks. Do not use it in the competition demo chain.

In group chats, the session key usually appears in the prompt as `[Group: feishu:<chat_id> | ...]`. Use that `feishu:<chat_id>` value. In private chats, use GolemBot's session key when provided by the harness; if unavailable, ask for a one-line operator confirmation before starting a durable task.

## Clarification Behavior

Ask a clarification only when the missing detail affects the deliverable. Examples:

- audience or length for a presentation
- whether to use existing chat history or only the latest instruction
- whether a document should be created or an existing one updated

When asking, set `status.json` to `waiting_for_user` and include the question in the status error/detail field or request notes.

## Common Mistakes

- Do not let GolemBot conversation memory replace `tasks/<task_id>/`.
- Do not create a new task for every follow-up message in the same unfinished task.
- Do not publish partial results as completed artifacts.
- Do not publish Feishu artifacts from inside Codex; publishing is a Python Bridge responsibility.
- Do not call Feishu raw APIs if `lark-cli`, GolemBot Feishu adapter, or lark-openapi-mcp already covers the operation.
- Do not switch to LangBot, OpenClaw, n8n, Dify, or another planner as the main orchestration layer.
