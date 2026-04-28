---
name: feishu-office
description: Use when an IM-Collab task needs Feishu IM, docs, slides, whiteboard, file, or multi-device office artifacts
---

# Feishu Office

This is a routing skill, not a Feishu implementation. Prefer existing wheels:

1. Feishu CLI built-in skills installed by `npx skills add larksuite/cli -y -g`.
2. `lark-cli` commands for IM, docs, drive, sheets, tasks, wiki, and related office operations.
3. `larksuite/lark-openapi-mcp` when MCP access or wider OpenAPI coverage is better than CLI shortcuts.

## Tool Order

- Use Feishu CLI shortcuts first for common operations.
- Use Feishu CLI API commands or raw API access when shortcuts do not cover the required endpoint.
- Use official `lark-openapi-mcp` when the agent runtime has MCP configured.
- Use local Markdown artifacts only for smoke tests or when credentials are absent.

## Setup Commands

```bash
npm install -g @larksuite/cli
npx skills add larksuite/cli -y -g
lark-cli auth login --recommend
lark-cli auth status
lark-cli doctor
```

## Artifact Contract

Do not treat a chat answer as office delivery. Write created Feishu links or local fallback paths to `tasks/<task_id>/artifacts.json` with `document`, `slides`, `whiteboard`, `summary`, and `next_steps`.

Sources: <https://feishu-cli.com/> and <https://github.com/larksuite/lark-openapi-mcp>.
