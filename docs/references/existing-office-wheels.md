# Existing Office Wheels

Use these tools instead of implementing office-suite behavior locally.

## Feishu CLI / Lark CLI

- Site: <https://feishu-cli.com/>
- Package: `@larksuite/cli`
- Binary: `lark-cli`
- Role: primary CLI for Feishu/Lark IM, docs, drive, sheets, tasks, wiki, and related office automation.
- Agent skills: install with `npx skills add larksuite/cli -y -g`.
- Verification: `lark-cli auth status` and `lark-cli doctor`.

## Feishu/Lark OpenAPI MCP

- Repository: <https://github.com/larksuite/lark-openapi-mcp>
- Role: official MCP server exposing Feishu/Lark Open Platform APIs to agents.
- Use when MCP is better than CLI shortcuts or when broader OpenAPI coverage is needed.

## Presenton

- Documentation: <https://docs.presenton.ai/generate-presentation-over-mcp>
- Repository: <https://github.com/presenton/presenton>
- Role: open-source presentation generator with API and built-in MCP.
- MCP endpoint: `/mcp`, cloud endpoint `https://api.presenton.ai/mcp`.
- HTTP generation endpoint: `/api/v1/ppt/presentation/generate`.
