# IM-Collab Demo Chain

This is the current competition-facing chain:

```text
Feishu user message
  -> lark-cli long-connection event listener
  -> events/im/*.json
  -> event consumer
  -> GolemBot HTTP /chat
  -> Codex + superpowers
  -> scripts/run_golembot_office_task.py
  -> Feishu Docs / Slides / Whiteboard
  -> Feishu reply with artifact links
```

User-facing behavior stays simple: the user sends a natural-language office request in Feishu and receives document, slides, and whiteboard results back in Feishu.

## Print Commands

```bash
rtk .venv/bin/python scripts/print_demo_chain.py
```

This prints the three commands needed for the current chain:

1. GolemBot gateway
2. Feishu event listener
3. Event consumer with GolemBot dispatch

## Required Environment

The GolemBot gateway needs:

```bash
export FEISHU_APP_ID=...
export FEISHU_APP_SECRET=...
```

Do not commit these values.

## Run Shape

Run each command in its own terminal or tmux pane.

Use the default printed consumer command for the full demo path. It includes:

- `--dispatch golembot`
- `--generator codex`
- `--publish`
- `--execute`

That means the consumer forwards incoming Feishu events to GolemBot, asks Codex to generate task artifacts, publishes real Feishu office artifacts, and sends a real Feishu reply.

Do not use `--generator local` for the competition-facing flow. It is only for unit tests and smoke checks.

## Current Gateway Decision

GolemBot's native Feishu adapter connected but did not receive the tested IM events in this environment. The reliable path keeps lark-cli as the Feishu channel wheel and uses GolemBot for harness/session/Codex execution.

This still matches the intended architecture:

- lark-cli owns Feishu ingress.
- GolemBot owns harness session and Codex execution.
- IM-Collab owns durable task protocol and office delivery.
