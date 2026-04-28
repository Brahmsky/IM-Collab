---
name: presenton-slides
description: Use when an IM-Collab task needs PPTX, PDF, slide outline, speaker notes, rehearsal questions, or Presenton integration
---

# Presenton Slides

This is a routing skill, not a slide engine. Prefer Presenton before hand-rolled PPT logic.

## Tool Order

1. Use Presenton MCP when configured. Its network MCP endpoint is `/mcp`; cloud is `https://api.presenton.ai/mcp`.
2. Use Presenton HTTP API when MCP is unavailable. The generation endpoint is `/api/v1/ppt/presentation/generate`.
3. Use local Markdown slide outlines only for smoke tests or when no Presenton endpoint is configured.

## Inputs

Provide `content`, `instructions`, requested slide count, language, template/theme, and export format. For API generation, map slide count to `n_slides` and export to `pptx` or `pdf`.

## Acceptance Criteria

- Prefer generated PPTX/PDF or Presenton edit link over local Markdown.
- Slide count matches the request unless the user approves a change.
- Write the slide file/link, outline, and speaker notes reference into `artifacts.json`.

Sources: <https://docs.presenton.ai/generate-presentation-over-mcp> and <https://github.com/presenton/presenton>.
