# Realistic Group Chat Dataset and Session Governance Design

## Purpose

The current MVP proves that a Feishu bot can receive an IM request, create a task, run Codex, publish Feishu office artifacts, and reply with cards. That is necessary but not enough for product validation.

The real competition scenario is not "one user asks the bot to make a PPT." It is a noisy group collaboration space where multiple people discuss requirements, change their minds, share links, mention deadlines, and introduce conflicts. The agent must behave like an office pilot inside that ongoing conversation.

This document records the product direction for:

- realistic group-chat validation data
- long-running group context
- session/task governance
- what controls are exposed to normal users vs operators

It is a design note, not an implementation plan.

## Current Gap

Current tests and demos are too clean:

- The bot often sees a direct instruction from one user.
- The group context is small and artificial.
- Task/session behavior is mostly implicit.
- There is no clear user-facing model for "new task", "continue previous task", "modify existing deliverable", or "show context".
- The temporary web console is an engineering surface, not a product GUI.

This means the MVP can pass a smoke test while still failing the real product question: can it help a team turn chaotic IM collaboration into traceable office deliverables?

## Realistic Validation Dataset

We need a deliberately messy group-chat scenario.

The dataset should include named roles:

- teacher or organizer
- team lead
- product/design member
- frontend member
- backend/member responsible for integration
- PPT/document owner
- observer or noisy participant
- bot

The conversation should include:

- real task goal
- deadline
- submission method
- document requirements
- PPT requirements
- whiteboard or flowchart requirement
- role assignments
- links and attachments
- noisy unrelated chat
- duplicate messages
- late corrections
- conflicts that must not be silently resolved

Important conflicts to simulate:

- PPT is 8 pages vs 10 pages.
- Deadline is Friday 18:00 vs Saturday noon.
- Document format is Markdown vs Word/docx.
- Final deliverable should be Feishu Slides vs exported PPTX.
- Whether mobile demo is required or optional.

Expected repository artifacts:

```text
examples/scenarios/messy_group_chat.json
examples/scenarios/messy_group_chat_script.md
examples/scenarios/expected_brief.json
examples/scenarios/long_context_archive.jsonl
examples/scenarios/expected_context_pack.json
```

`messy_group_chat.json` is machine-readable fixture input.

`messy_group_chat_script.md` is a human script that teammates can follow in a real Feishu group. Each teammate gets a role and sends messages in order, creating a realistic group history.

`expected_brief.json` is the oracle for what source-grounded briefing should find.

`long_context_archive.jsonl` simulates a group that already has many messages before the user invokes the bot.

`expected_context_pack.json` defines what the Bridge should select when the bot is mentioned, proving we do not feed the whole archive into Codex.

## Long-Running Context Model

A real group may have hundreds or thousands of messages. A single Codex turn must not receive the full group history by default.

The long-running context model should be layered:

```text
raw message archive
  -> rolling source-grounded brief
  -> confirmed project memory
  -> unresolved conflicts / open questions
  -> task-specific context pack
  -> Codex turn
```

### Raw Message Archive

All group messages should be archived with:

- `message_id`
- `chat_id`
- `sender`
- `sent_at`
- `content`
- `message_type`
- attachments, links, files, images, cards
- reply/thread metadata if available

This is the audit source. It should not be blindly sent to Codex.

### Rolling Brief

The system should periodically summarize recent messages into source-grounded briefs.

Trigger options:

- every N messages
- every time window
- when a bot task starts
- when an organizer/teacher sends a high-authority message

Rolling briefs should preserve:

- extracted claims
- message references
- confidence/extraction method
- conflicts
- open questions
- confirmed facts

### Project Memory

Only confirmed information should enter project memory.

Examples:

- project name
- competition track
- team members and roles
- accepted deadline
- accepted deliverable format
- selected presentation length
- confirmed demo story

Conflicts do not enter memory until confirmed. They remain unresolved items.

### Context Pack

When a user mentions the bot, Bridge should assemble a bounded context pack:

- current user message
- recent relevant raw messages
- latest rolling brief
- unresolved conflicts
- confirmed project memory
- active task state
- prior artifacts
- control log entries

The context pack should explain what it includes and what it intentionally excludes.

Codex should see the context pack and referenced source snippets, not the entire chat archive.

## Session and Task Governance

The product needs session governance, not just context compression.

Normal users should not manage raw `task_id`, `codex_thread_id`, or `turn_id`. They should reason in terms of:

- project
- current task
- previous deliverable
- new task
- continue
- status
- context

Internal mapping:

```text
chat_id
  -> project session
  -> task list
  -> active task
  -> Codex thread
  -> active turn
  -> artifacts
  -> controls
```

## Default Routing Policy

When a user sends a message in a group:

1. If there is an active Codex turn for the group, treat the message as an append/steer instruction unless it is clearly unrelated.
2. If there is a `waiting_for_user` task, treat the message as a confirmation or clarification.
3. If the message is a card `start_task` action, resume that waiting task.
4. If the latest completed task is recent and the message says "刚才", "继续", "修改", or references a deliverable, treat it as a follow-up modification.
5. If the message clearly introduces a separate objective, create a new task.
6. If ambiguous, ask the user whether this is a new task or a modification of the previous task.

The key product behavior is that uncertainty is handled by asking, not by guessing.

## User-Facing Commands

Normal group users should get a small, human-readable command surface.

Recommended commands:

```text
/new
/continue
/status
/close
/context
```

Chinese equivalents should also work:

```text
新开任务
继续刚才
当前进度
结束这个任务
你现在参考了哪些信息
```

Meanings:

- `/new`: start a new task without inheriting the active task state.
- `/continue`: continue the most recent task in the group.
- `/status`: show current task state and deliverables.
- `/close`: close/archive the current task.
- `/context`: show which messages, briefs, artifacts, and memories will be used.

Do not expose these to normal users:

```text
/resume thread_xxx
/reset codex_session
/debug
/reindex
raw task_id
raw codex_thread_id
raw turn_id
```

Those belong to the operator surface.

## Operator Surface

The operator surface can expose lower-level controls:

- active task
- Codex thread
- active turn
- context pack preview
- unresolved conflicts
- rolling brief history
- append instruction
- interrupt turn
- retry task
- archive task
- fork task
- force new session
- inspect artifacts

The operator surface should not become the planner or workflow engine. It emits controls into the existing task protocol. Python Bridge and Codex handle lifecycle and execution.

The current web console is not a final frontend. It is only an engineering control surface. It should be frozen for now and not treated as the product GUI.

## Real Product Flow

Ideal group flow:

```text
Team discusses in Feishu group.
Messages accumulate in archive.
Rolling briefs keep source-grounded state.

User mentions bot:
  "@助手 根据刚才讨论生成方案和答辩 PPT"

Bridge classifies:
  new task / continue / modify / status / context / ambiguous

Bridge assembles context pack:
  current message
  relevant recent source messages
  latest brief
  confirmed memory
  unresolved conflicts
  prior artifacts if any

If ambiguous:
  bot asks user to confirm new task vs modify existing task

If ready:
  Codex runs with context pack
  Feishu docs/slides/whiteboard are created or updated
  delivery card is sent to group

User continues:
  "把刚才 PPT 改成 5 分钟答辩版"

Bridge reuses previous task/thread/artifacts and creates a follow-up context pack.
```

## Validation Strategy

The next serious validation should not be GUI-driven.

Acceptance should focus on:

- Can a messy group chat produce a source-grounded brief?
- Does the brief cite original messages?
- Are conflicts preserved and surfaced?
- Does the bot ask for confirmation instead of guessing?
- Does `/new` or equivalent create a new task?
- Does `/continue` or "继续刚才" resume the correct task?
- Does `/context` show what the agent will use?
- Does a follow-up modification reuse previous artifacts?
- Does the operator have enough visibility to interrupt, retry, or append instructions?

## Near-Term Implementation Order

1. Add realistic group-chat fixtures and expected brief oracle.
2. Add long-context archive fixture and expected context pack.
3. Implement a context-pack builder around existing task protocol.
4. Add session routing policy for `/new`, `/continue`, `/status`, `/close`, and `/context`.
5. Add Feishu replies for `/status` and `/context`.
6. Validate with real teammates in a Feishu group using the script.

GUI redesign is intentionally deferred.
