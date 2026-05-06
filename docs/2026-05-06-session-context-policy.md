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

A normal group-chat continuation to the bot continues the active group session:

- keep the same Codex execution thread for that group session;
- collect only the delta group messages since the last absorbed group message;
- send the user's current instruction plus that delta group context to Codex;
- advance the last absorbed group message boundary only after the turn is accepted by the backend.

Ordinary group messages that are not addressed to the bot should not automatically pollute the Codex thread. They become available as possible delta context only when the bot is next invoked for the active session.

## Briefing And Recall Roles

The group-chat context path has three separate responsibilities.

`select_briefing_context` is the cheap context selector. It is implemented in `bridge/group_context_selector.py`. It uses structured message tags, attachments, and recent-tail preservation. It does not scan raw message text for important-looking keywords.

`LangExtract + DeepSeek V4 Flash` is the optional semantic evidence extractor. It is implemented in `bridge/group_briefing_extractors/langextract_deepseek.py` and enabled with `brief_extractor="langextract-deepseek"`. The optional dependency is recorded in `requirements-langextract.txt` as `langextract[openai]==1.3.0`.

`group_briefing` is the source-grounded briefing layer. It turns selected messages or extracted evidence into `brief.json` and `brief.md`, so Codex can use a traceable evidence layer instead of raw noisy group chat.

## Current Selector Logic

`select_briefing_context(messages, max_messages=45, recent_tail=12)` behaves as follows:

- return all messages if they already fit the budget;
- include messages with priority tags such as `formal_notice`, `deadline`, `requirement`, `decision`, `correction`, `conflict`, `open_question`, `latest`, `final`, `attachment`, `template`, `deliverable`, or `bot_request`;
- include messages with attachments;
- always preserve the most recent `recent_tail` messages;
- if still over budget, rank non-recent candidates by tag weight and attachment presence;
- restore original chronological order before returning.

This is not semantic retrieval. It is structured filtering plus recency. Its quality depends on upstream message tags and attachment metadata. The semantic step is the optional LangExtract extractor after selection.

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

The best tested path is conservative selection with 60 messages and 16 recent-tail messages, then LangExtract + DeepSeek V4 Flash evidence extraction.

## Required State Model

To match the product semantics, the durable state needs these fields:

- `group_id` or `chat_id`;
- active session id per group;
- session id to Codex thread id;
- session id to last absorbed group message id;
- task/artifact ids generated by each Codex turn.

The current code already has `task-bindings.json` and Codex thread binding, but the group-session model is still too coarse: the current `build_golembot_session_key()` path effectively binds one session key to one group/channel unless an additional session id is introduced.

## Non-Goals

- The GUI should not be responsible for long-term context.
- The GUI should not replay its visible chat history into Codex.
- The frontend should not expose internal status, task ids, event logs, raw control JSON, or timeline internals as normal product UI.
- The default path should not silently enable paid external extraction. LangExtract + DeepSeek remains an explicit backend choice.
