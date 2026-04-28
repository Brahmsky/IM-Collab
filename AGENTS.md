# IM-Collab Agent Instructions

Use `rtk` before shell commands in this repository.

## Project Direction

This repository builds an Agent-Pilot office collaboration workflow for the competition brief in `落地方案.md`.

Use Codex + superpowers as the only orchestration layer. Do not introduce OMO, OMX, or another Agent framework as the main planner or executor. External projects, services, forks, gateways, CLIs, HTTP APIs, and MCP servers may be used only as tools that Codex drives.

## Architecture Boundary

- Python Bridge owns IM ingress, task directory creation, status/artifact JSON, external process calls, and result egress.
- Codex + superpowers owns planning, clarification, tool selection, execution, review, and verification.
- Feishu, Presenton, lark-cli, lark-openapi-mcp, and future gateways are external tool surfaces.
- Task completion is determined by `tasks/<task_id>/status.json` and `tasks/<task_id>/artifacts.json`, not by tmux or terminal text.

## Task Protocol

Each task directory contains:

- `request.md`: user command, IM context, constraints, and acceptance criteria.
- `status.json`: machine-readable task state.
- `artifacts.json`: final delivery links/files/summaries.
- `tmux.log`: optional operator log.

Valid states are `queued`, `running`, `waiting_for_user`, `completed`, and `failed`.

## Development Rules

- Use `rtk` before shell commands.
- Prefer small, testable Python modules.
- Write tests before implementation for behavior changes.
- Keep the local MVP independent of real Feishu or Presenton credentials.
