# Session And Group Context Policy

Date: 2026-05-06

## Core Decision

IM-Collab only has two context layers:

1. Group-chat session context.
2. Codex execution session context.

The GUI chat is not a context manager. It is a conversation UI and return channel for the current Codex execution session. It must not rebuild, compress, or replay GUI message history into every Codex request. A GUI follow-up sends only the user's current message to the current Codex session, because Codex owns its own thread context.

## GUI Session Semantics

When the user sends a message in an existing GUI session:

- The frontend appends the user bubble immediately.
- The frontend creates a pending assistant bubble immediately.
- The backend sends only the current user message to the existing Codex thread.
- The pending assistant bubble is replaced or streamed with the Codex text result.
- If Codex emits artifact metadata in the supported format, the current assistant message may show current-turn artifact cards.
- The right-side artifact list is session-level generated artifacts, not the current message's only source of truth.

The GUI must not inject group-chat history, old GUI chat bubbles, or stale task JSON as prompt context.

## Group Chat Session Semantics

The group chat is the only channel that needs context injection.

`/new` starts a new group session:

- create a new logical group session under the same group chat;
- create or bind a fresh Codex execution thread;
- establish the initial group-context snapshot if the command needs it;
- record the last absorbed group message boundary.

The intended command grammar is:

- `/new <instruction>`
- `/new <time> <instruction>`

`<time>` is a relative lookback window. Supported syntax should be:

- `h`: hours, such as `6h`;
- `d`: days, such as `3d`;
- compound days plus hours, such as `2d6h`.

Examples:

- `/new 6h 帮我整理今天下午新增的需求`
- `/new 3d 生成这三天讨论出来的项目复盘`
- `/new 2d6h 根据最近两天半的上下文做交付方案`
- `/new 根据最近一轮群聊做项目方案`

For `/new <instruction>`, the initial group context window is:

```text
min(80 group messages, messages from now back to the previous /new boundary)
```

For `/new <time> <instruction>`, the initial group context window is:

```text
messages whose sent_at >= now - parsed(<time>)
```

This time window is an override. It should not depend on the previous `/new` boundary, because the user is explicitly saying how far back to look.

Current implementation status:

- `/new <instruction>` and `/new <time> <instruction>` are parsed by `bridge/group_session.py`;
- group `/new` session keys use `feishu:<chat_id>:session:<message_id>`, so multiple sessions can exist under the same group;
- `/new <instruction>` selects messages after the previous `/new` boundary, capped at 80 messages;
- `/new <time> <instruction>` computes an absolute cutoff from the trigger message time and passes it to the Feishu history reader;
- `bridge/lark_im.py` paginates Feishu history until the cutoff is reached;
- confirmation cards carry the originating `session_key`, so clicking "start" resumes the same isolated session;
- ordinary group follow-ups first look for the exact default group session, then fall back to the latest active `/new` session under the same group;
- session bindings persist `last_absorbed_message_id` per group session;
- active group follow-ups collect only the messages after `last_absorbed_message_id`, excluding the current trigger message;
- the follow-up payload sent to Codex includes the user's current instruction plus only that delta group context;
- after the turn is accepted, the binding advances `last_absorbed_message_id` to the current trigger message id.

A normal group-chat continuation to the bot continues the active group session:

- keep the same Codex execution thread for that group session;
- collect only the delta group messages since the last absorbed group message;
- send the user's current instruction plus that delta group context to Codex;
- advance the last absorbed group message boundary only after the turn is accepted by the backend.

Ordinary group messages that are not addressed to the bot should not automatically pollute the Codex thread. They become available as possible delta context only when the bot is next invoked for the active session.

## Briefing And Recall Roles

The group-chat context path has three separate responsibilities.

`select_briefing_context` is the cheap context limiter. It is implemented in `bridge/group_context_selector.py`. It only uses runtime-stable signals: attachments and recent-tail preservation. It does not scan raw message text for important-looking keywords, and it must not rely on fixture-only `tags`.

`LangExtract + DeepSeek V4 Pro` is the semantic evidence extractor. It is implemented in `bridge/group_briefing_extractors/langextract_deepseek.py` and enabled with `brief_extractor="langextract-deepseek"`. The default model is `deepseek-v4-pro` with high reasoning effort. The optional dependency is recorded in `requirements-langextract.txt` as `langextract[openai]==1.3.0`.

`group_briefing` is the source-grounded briefing layer. It turns selected messages or extracted evidence into `brief.json` and `brief.md`, so Codex can use a traceable evidence layer instead of raw noisy group chat.

Packaging boundary:

- Feishu messages are first collected as message dictionaries from `lark-cli`.
- The LangExtract path converts those dictionaries into plain source text with one line per message:

```text
[message_id] sender sent_at: content [附件:type:name]
```

- That source text, the extractor prompt, and examples are sent to DeepSeek through LangExtract's OpenAI-compatible provider.
- DeepSeek does not receive Codex task files directly.
- Codex later receives the task prompt plus project files such as `brief.json`, `brief.md`, and optionally `evidence.json`.

So the flow is:

```text
Feishu messages
-> source text for LangExtract
-> DeepSeek evidence extraction
-> evidence.json
-> brief.json / brief.md
-> Codex task execution
```

The default group-chat path now uses `brief_extractor="langextract-deepseek"`. The legacy `rules` path remains available only as an explicit fallback for tests, p2p/offline operation, or controlled local fixtures.

## Current Selector Logic

`select_briefing_context(messages, max_messages=45, recent_tail=12)` behaves as follows:

- return all messages if they already fit the budget;
- include messages with attachments;
- always preserve the most recent `recent_tail` messages;
- if still over budget, keep the most recent attachment-bearing non-tail candidates;
- restore original chronological order before returning.

This is not semantic retrieval. It is attachment preservation plus recency. The semantic step is the optional LangExtract extractor after selection. Fixture `tags` may remain in scenario data for evaluation commentary, but production selection must not depend on them.

## Existing Evaluation Result

The current long-context evaluation is documented in `docs/references/group-briefing-evidence-evaluation.md`.

Scenario:

- fixture: `examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json`
- 71 group messages;
- 8+ speakers;
- 24 attachment references;
- more than one week of conversation;
- oracle: `expected_brief.json` with 16 expected items.

Measured results:

| Setting | Evidence Items | Matched Oracle Items | Recall |
| --- | ---: | ---: | ---: |
| `extraction_passes=1` | 40 | 8 / 16 | 0.50 |
| `extraction_passes=2` | 46 | 9 / 16 | 0.56 |
| `--select-context --max-context-messages 45 --recent-tail 12` | 21 | 7 / 16 | 0.44 |
| `--select-context --max-context-messages 60 --recent-tail 16` | 50 | 13 / 16 | 0.81 |

These numbers are historical results from the earlier selector experiment. The current product direction is stricter: selector should not pretend to understand group-chat importance from fixture-only tags. Real semantic extraction belongs in LangExtract/evidence extraction, not in hand-maintained tag priority lists.

## Required State Model

To match the product semantics, the durable state needs these fields:

- `group_id` or `chat_id`;
- active session id per group;
- session id to Codex thread id;
- session id to last absorbed group message id;
- task/artifact ids generated by each Codex turn.

The current code uses `task-bindings.json` for this binding. Group `/new` sessions already include a session id in the key, and `last_absorbed_message_id` is persisted on that same binding entry. A future refinement could split this into a first-class group-session store, but the current binding model now covers the required product semantics.

## Non-Goals

- The GUI should not be responsible for long-term context.
- The GUI should not replay its visible chat history into Codex.
- The frontend should not expose internal status, task ids, event logs, raw control JSON, or timeline internals as normal product UI.
- Paid external extraction should be visible in backend configuration and logs. For group-chat task creation, LangExtract + DeepSeek is now the default semantic extractor; p2p and offline test paths can still use the explicit `rules` fallback.
