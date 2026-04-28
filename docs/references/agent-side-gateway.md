# Agent-Side Gateway

In this project, the "gateway" is not a new Agent framework and not a replacement for Codex + superpowers.

It is the boundary that turns external office events into internal Agent tasks, and turns task artifacts back into office-channel responses.

## Current Gateway Shape

```text
Feishu long connection
  -> lark-cli event +subscribe
  -> events/im/*.json
  -> scripts/run_event_consumer.py
  -> tasks/<task_id>/request.md
  -> Codex + superpowers / lark-cli tools
  -> tasks/<task_id>/artifacts.json
  -> lark-cli im +messages-reply
```

## Responsibilities

- consume event files emitted by `lark-cli`
- deduplicate by `message_id`
- skip bot self-messages
- isolate failed events
- create task directories
- invoke the delivery flow when explicitly requested

## Non-Responsibilities

- It does not perform Agent planning.
- It does not implement Feishu APIs.
- It does not replace `lark-cli`, `lark-openapi-mcp`, or Presenton.
- It does not become OMO, OMX, OpenClaw, LangBot, or another main orchestrator.

## Why This Is Enough For The MVP

`lark-cli event +subscribe` already handles the hard platform side: Feishu long connection, bot identity, compact event conversion, reconnect behavior, and file output. The local gateway only adapts that existing wheel to the repository task protocol.

## Possible Production Evolution

If the project needs a production service later, this layer can evolve into a small event service with a real queue, metrics, and deployment lifecycle. Even then, Codex + superpowers remains the orchestration layer; the gateway remains an event and tool boundary.
