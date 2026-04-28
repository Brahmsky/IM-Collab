# Source-Grounded Group Briefing Gate Design

## Product Shape

When a user mentions the Feishu bot in a group chat, the agent should not immediately write final office artifacts. It first turns the recent group chat into a source-grounded briefing layer:

```text
@Agent request
  -> collect recent group messages
  -> write brief.json and brief.md
  -> detect conflicts and open questions
  -> if uncertain: ask the group to confirm
  -> if confirmed: start document/slides/whiteboard generation
  -> publish Feishu artifacts
```

The key product behavior is that the agent acts like an office pilot, not a one-shot summarizer. It reviews the source conversation, shows what it understood, asks for confirmation when the source is ambiguous, and only then executes.

## Evidence Layer

`brief.json` is the machine-readable source of truth for downstream generation. `brief.md` is the human-readable side-annotation view.

Every extracted claim must cite original `message_id` values. If a deadline, format rule, assignment, attachment, or requirement cannot be traced to a message, it must not enter the summary. Conflicts must remain visible as conflicts; the system must not silently choose one side.

The briefing stage produces:

- normalized source messages
- side annotations
- summary buckets
- conflicts
- open questions

## Confirmation Gate

If `brief.json` contains annotations of type `conflict` or `open_question`, the task enters `waiting_for_user` before artifact generation.

The agent should reply in Feishu with:

- a concise explanation that it has finished the group-chat briefing
- the conflicts and open questions
- message references for each uncertain item
- a clear instruction: reply with confirmation, corrections, or additional requirements

No document, slides, or whiteboard should be generated while the task is waiting for confirmation.

## Continue Path

When the user confirms or adds information in the same group session, the Bridge should route that message to the waiting task rather than creating a new independent task. The confirmation becomes a control command or request update, and the same Codex thread can continue.

The minimal implementation can start with:

- mark task `waiting_for_user`
- write `brief.json`, `brief.md`, and `confirmation.md`
- send a Feishu reply with the confirmation request
- allow later `append`/`retry`/manual confirmation through the existing task console

The ideal implementation should later add a start/confirm button in Feishu card messages and GUI.

## GUI Role

GUI is an operator cockpit, not the primary user experience. It should show:

- current task state
- group briefing result
- conflicts/open questions
- active thread/turn
- append, interrupt, retry, ack, confirm/start controls

The formal GUI should be designed as a polished first version. The current web console is only an engineering control surface and should not be treated as final product UI.

## Downstream Generation Rule

Document, slides, and whiteboard generation must prefer `brief.json` over raw chat logs. Raw chat logs remain useful for audit, but downstream artifacts should be based on the source-grounded brief to preserve traceability and reduce hallucinated requirements.
