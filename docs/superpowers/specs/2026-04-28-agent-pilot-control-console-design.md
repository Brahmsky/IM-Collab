# Agent Pilot Control Console Design

## Status

Approved direction from discussion: the Agent-Pilot chain is the core MVP; the remaining GUI should be a control console, not a replacement for Feishu, Codex, or the office suite.

## Goal

Build a local Agent-Pilot cockpit that observes IM-Collab tasks and prepares for operator control of agent loops.

## Product Boundary

The user-facing office surface remains Feishu: IM, Docx, Slides, and Whiteboard. The console is an operator surface for demos, debugging, and human-in-the-loop control.

The console must not become a planner, executor, or workflow engine. It reads and controls the existing task protocol:

- `events/`: Feishu event files emitted by `lark-cli`.
- `tasks/<task_id>/request.md`: task request and conversation context.
- `tasks/<task_id>/status.json`: durable task state.
- `tasks/<task_id>/artifacts.json`: local and remote deliverables.

## Wheel Strategy

Use existing wheels wherever practical:

- Textual is the default near-term GUI framework because it is Python-native, open source, suited to internal tooling and real-time process monitoring, and fits this repository's local file protocol.
- AgentPulse remains a reference for Codex/Claude session cockpit UX, but its public repository path could not be verified in this environment.
- Agent Sessions remains a useful read-only Codex session browser reference, but it is macOS-native and does not understand this project's task protocol.
- Magentic-UI is a strong human-in-the-loop UX reference, but it is an AutoGen-based agent runtime and must not become this project's main orchestration layer.

## First Console Shape

The first console is read-mostly:

- Left/task list: task id, state, updated time, short summary.
- Detail panel: selected task request, state, error, artifact links, whiteboard token.
- Events panel: event count and latest event file names.
- Footer/help: refresh key, quit key, and planned control actions.

The first implementation may be a Textual app or a fallback plain CLI summary if Textual is not installed. The data layer must be independent of Textual so tests do not require GUI rendering.

## Control Model

Write controls are not part of the first implementation. They should be added through an explicit command protocol rather than direct process mutation:

- `tasks/<task_id>/control.jsonl`
- command examples: `cancel`, `retry`, `append_instruction`, `acknowledge_error`
- each command records timestamp, operator, command type, and payload

The consumer/bridge can later read these commands and decide how to act. This preserves the architecture boundary: GUI emits operator intent; Python Bridge performs lifecycle actions; Codex + superpowers remains the planner/executor.

## Acceptance Criteria

- A command can show all task directories sorted by latest update.
- Completed tasks show remote Feishu document and slides links when present.
- Failed tasks show their error.
- Running tasks show state and request context.
- Event directory status is visible.
- Tests cover the task scanning and display model without requiring Textual.
- The README documents how to launch the console and what it does not do yet.

## Non-Goals

- Do not implement a new web office interface.
- Do not embed or replace Codex.
- Do not adopt AutoGen, LangGraph, OMO, OMX, or OpenClaw as the main planner.
- Do not implement destructive controls until command protocol and safety checks are specified.

