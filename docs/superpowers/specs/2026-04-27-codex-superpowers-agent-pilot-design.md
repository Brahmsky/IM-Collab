# Codex Superpowers Agent Pilot Design

**Goal:** Build the local MVP for an IM-to-office Agent Pilot where Codex + superpowers is the only orchestration layer.

**Decision:** Do not use any separate Agent framework as the main planner or executor. External systems may be copied, forked, hosted, or called through CLI, HTTP, MCP, or Gateway boundaries, but only as tools that Codex can drive.

## Architecture

The system is a file-protocol workspace around Codex. Python Bridge receives or simulates an IM request, creates a task directory, writes `request.md` and `status.json`, and then starts Codex in the same workspace. Codex uses project-local office skills plus superpowers process skills to plan, execute, verify, and write `artifacts.json`.

For the first local MVP, real Feishu, Presenton, and gateway calls are replaced by deterministic local artifacts. This validates the task contract before binding to external credentials or network services.

## Components

- `AGENTS.md`: project instructions for Codex, including RTK usage and the Codex + superpowers orchestration boundary.
- `skills/feishu-office/SKILL.md`: thin routing layer over Feishu CLI built-in skills and official lark-openapi-mcp.
- `skills/presenton-slides/SKILL.md`: thin routing layer over Presenton API/MCP and local fallback output.
- `skills/delivery-archive/SKILL.md`: completion contract for `artifacts.json` and final delivery summary.
- `docs/references/existing-office-wheels.md`: current external tool references and setup entry points.
- `bridge/external_tools.py`: machine-readable catalog of preferred existing office wheels.
- `bridge/codex_runner.py`: builds the Codex CLI task prompt and subprocess arguments.
- `bridge/task_protocol.py`: creates task directories and validates task status/artifact JSON.
- `bridge/local_codex_smoke.py`: deterministic local stand-in for the first Codex-run artifact writer.
- `examples/demo_request.md`: simulated IM context and user command.
- `scripts/smoke_demo.py`: end-to-end local smoke script.
- `tests/`: protocol and smoke tests.

## Data Flow

1. A request enters from `examples/demo_request.md` for the MVP.
2. `scripts/smoke_demo.py` creates `tasks/<task_id>/request.md`.
3. `status.json` starts as `queued`.
4. The local smoke runner writes deterministic office artifacts and sets status to `completed`.
5. `artifacts.json` contains document, slide, whiteboard, summary, and next-step fields.
6. Later Feishu Bridge code will replace step 1 and Codex CLI execution will replace the smoke runner, without changing the task directory contract.

## Error Handling

Task status is the source of truth. `status.json` must be valid JSON with `task_id`, `state`, `created_at`, `updated_at`, and optional `error`. Valid states are `queued`, `running`, `waiting_for_user`, `completed`, and `failed`.

If artifact validation fails, the task must be marked `failed` and include an error message. Bridge code must not infer success from terminal output or tmux screen text.

## Testing

The MVP is tested with pytest. Tests cover request creation, status transitions, artifact validation, and the end-to-end smoke demo.

## Scope

Included now:

- Switch project documentation to Codex + superpowers.
- Create local task protocol and deterministic smoke demo.
- Add project-local skills that route to existing office tools instead of reimplementing office behavior.

Deferred:

- Real Feishu webhook and message send APIs.
- Real Presenton service calls.
- Real Codex CLI subprocess/tmux automation.
- Textual dashboard.
- Offline conflict resolution.
