# Gateway Wheels Evaluation

This note evaluates whether the project should keep writing its own Python Bridge, or replace most of it with existing gateway/workflow wheels.

The focus is agent harness infrastructure, not traditional workflow automation. n8n, Dify, FastGPT, and similar tools are useful as callable tools/workflows, but they should not be treated as the main candidate for the agent-side gateway unless they can host or drive Codex/Claude Code/OpenCode-style harness sessions.

## Project Requirements

The gateway candidate must be checked against these concrete requirements:

- Feishu/Lark IM ingress: receive private chat and group `@bot` messages.
- Feishu/Lark egress: send progress, clarification, and final artifact replies.
- Conversation context: preserve chat id, sender, mentions, message id, recent history, and attachments where possible.
- Task protocol: create or update a durable task record with `request.md`, `status.json`, and `artifacts.json`.
- Codex backend: invoke Codex + superpowers as the main planner/executor, not replace it with another planner.
- Office tools: call lark-cli, lark-openapi-mcp, Presenton, Slides, Docs, Whiteboard, and future MCP tools.
- Human-in-the-loop: support clarification, approval, retry, and resume.
- Observability: expose task state, logs, failures, and delivery artifacts.
- Security: preserve Feishu identity, bot/user scopes, allowlists, and tool permission boundaries.
- Local MVP: run without public callback URL and without production infrastructure.

## Candidate Classes

### 0. GolemBot

GolemBot is the closest discovered project to this repository's gateway requirement.

Fit:

- Strong channel fit. It advertises Slack, Telegram, Discord, Feishu, DingTalk, WeCom, WeChat, and HTTP API adapters.
- Strong coding-agent fit. It explicitly lists Cursor, Claude Code, OpenCode, and Codex as engines behind the gateway service.
- Strong decoupling fit. Its architecture separates channel adapters, gateway service, `createAssistant()`, engine backend, and provider routing.
- It acknowledges Codex-specific configuration: safe/unrestricted mode, sandbox, approval, search, added directories, and provider constraints.

Limits:

- It is new and must be tested locally before becoming a dependency.
- It may route Codex through its own assistant/session abstraction, so we must verify that Codex + superpowers remains the planner/executor and that project `AGENTS.md`/skills are loaded correctly.
- It may not natively produce this repository's `tasks/<task_id>/request.md`, `status.json`, and `artifacts.json`; an adapter may still be needed.
- We must verify Feishu app setup, group `@bot`, private chat, restart behavior, attachment handling, and final artifact reply.

Verdict:

- Highest-priority replacement candidate for the current Python IM gateway.
- If it works, our Python code can shrink to task protocol and delivery helpers, or become a backend invoked by GolemBot.
- Keep this candidate.

Source:

- GolemBot README says one command connects coding agents to Slack, Telegram, Discord, Feishu, DingTalk, WeCom, WeChat, or HTTP clients.
- Its diagram separates gateway service from Cursor/Claude Code/OpenCode/Codex engines.
- Its engine table lists Codex skill injection through workspace `AGENTS.md` and session resume through `exec resume <thread_id>`.

### 0.5 OpenClaw ACP / Codex Harness

This is the most important same-level harness reference.

Fit:

- Strong harness fit. OpenClaw ACP sessions are designed to run external coding harnesses such as Pi, Claude Code, Codex, OpenCode, and Gemini CLI through an ACP backend plugin.
- Strong persistent-session fit. The ACP operator flow includes spawning a Codex session, binding work to a thread, checking runtime state, steering an active session, setting timeouts, permissions, model, and stopping work.
- Strong Codex-specific fit. OpenClaw's Codex Harness lets OpenClaw run embedded turns through the Codex app-server while Codex owns low-level agent session behavior such as native thread resume and compaction.
- Good boundary model: OpenClaw can own chat channels, session files, approvals, media delivery, and transcript mirror while Codex owns the low-level harness turn.

Limits:

- It can easily become the primary agent runtime if we adopt it wholesale.
- It is a heavier dependency than GolemBot or lark-cli.
- We must verify whether Codex app-server requirements match our installed Codex environment.
- It may require accepting OpenClaw's session and permission model instead of our simpler task directory protocol.

Verdict:

- Keep as the strongest architecture reference and possible post-MVP harness gateway.
- Do not adopt blindly until GolemBot and the current lark-cli path are compared.

Sources:

- OpenClaw ACP docs say ACP sessions run external coding harnesses like Pi, Claude Code, Codex, OpenCode, and Gemini CLI through ACP backend plugins.
- OpenClaw Codex Harness docs say the bundled Codex plugin lets Codex own low-level agent session behavior while OpenClaw owns chat channels, session files, approvals, media delivery, and transcript mirroring.

### 1. lark-cli event subscription

Current wheel in use.

Fit:

- Strong Feishu fit. `lark-cli event +subscribe` already handles bot identity, long connection event delivery, compact event output, and local file emission.
- Best for local MVP because it does not require a public webhook server.
- Works naturally with this repository's task directory protocol.

Limits:

- It is an event ingress wheel, not a complete agent gateway.
- Queueing, deduplication, retry, task state, and Codex invocation still need a thin local adapter.

Verdict:

- Keep as the default MVP ingress wheel.
- The adapter should stay thin and mostly map event files to task protocol.

Source:

- `lark-cli` repository says it is built for humans and AI Agents and covers Messenger, Docs, Base, Sheets, Calendar, Mail, Tasks, Meetings, and more.
- Official risk warning also matters: AI agents acting with Feishu authorization can leak data or perform unauthorized operations, so gateway permissions must be conservative.

### 2. LangBot

LangBot is a bot gateway/application framework with a documented Feishu/Lark platform adapter.

Fit:

- Strong channel fit. It supports Feishu bot connection, long connection mode, webhook mode, private chat, and group usage.
- Useful if we want a ready-made bot WebUI, bot platform management, and less custom event plumbing.

Limits:

- It is closer to a chatbot platform than this project's file-protocol task gateway.
- We still need a plugin/adapter that turns LangBot events into `tasks/<task_id>/request.md`, invokes Codex, and returns artifact links.
- If LangBot's own LLM pipeline becomes the planner, it conflicts with the "Codex + superpowers only" orchestration boundary.

Verdict:

- Good replacement candidate for Feishu ingress/egress.
- Not a drop-in replacement for the whole Python Bridge unless we write a Codex task plugin.

Sources:

- LangBot docs describe Feishu app setup, bot creation in WebUI, long connection as the default mode, webhook fallback, and adding the bot to groups/private chats.
- LangBot's repository describes it as a production-grade IM bot platform with access control, rate limiting, sensitive word filtering, monitoring, exception handling, plugin ecosystem, MCP support, Web management panel, Lark support, and integrations with Dify, n8n, Langflow, Coze, Claude, Gemini, OpenClaw, and others.

### 2.5 AstrBot

AstrBot is another Chinese ecosystem IM bot platform.

Fit:

- Strong IM platform fit. It lists Feishu/Lark, DingTalk, WeCom, QQ, Telegram, Slack, Discord, and more.
- Strong plugin/ecosystem fit. It has a WebUI, agent sandbox, MCP, skills, knowledge base, and many community plugins.
- Strong language fit for this repository because it is primarily Python.

Limits:

- It is an agent chatbot platform, not specifically a coding-agent gateway.
- Its own agent/sandbox/LLM pipeline can become the main orchestrator unless constrained.
- We must verify whether it can delegate to local Codex CLI cleanly without reimplementing a plugin.

Verdict:

- Good fallback channel gateway candidate after GolemBot/LangBot.
- Higher risk of orchestration overlap than GolemBot.

Source:

- AstrBot README describes it as an all-in-one agent chatbot platform with Feishu/Lark support, plugins, MCP, skills, knowledge base, sandbox, WebUI, and Dify/Coze integrations.

### 3. OpenClaw Gateway + Feishu plugin

OpenClaw has the closest conceptual match to "agent-side gateway".

Fit:

- Strong gateway fit. OpenClaw Gateway owns routed channel sessions, WebSocket gateway connectivity, transcript/history tools, outbound message routing, and approval tools.
- It can expose channel conversations to Codex or other MCP clients through `openclaw mcp serve`.
- OpenClaw Feishu plugins exist and advertise Feishu WebSocket event subscription, batching, mention preservation, history API, access control, cards, multi-account support, and per-sender tool policy.
- OpenClaw CLI backends mention local AI CLI sessions, including session continuity and optional MCP loopback.

Limits:

- It is a large external agent framework/runtime. If it hosts the main reasoning loop, it can violate the project decision that Codex + superpowers is the only orchestration layer.
- The official MCP bridge docs say live queue state exists only while the bridge is connected, and when the MCP client disconnects the bridge exits and live queue is gone. That is useful but not the whole durable task protocol.
- Feishu plugin quality and compatibility must be verified in our environment before depending on it.
- Likely Node/TS operational surface is larger than the current lark-cli setup.

Verdict:

- Best reference architecture for the "real gateway" idea.
- Potential future replacement for IM channel gateway, especially if we want multi-channel routing.
- Do not make it the main planner/executor unless project direction changes.

Sources:

- OpenClaw MCP docs describe `openclaw mcp serve` for Codex/Claude Code/other MCP clients to talk to OpenClaw-backed channel conversations, with tools like `conversations_list`, `messages_read`, `events_wait`, `messages_send`, and approval tools.
- OpenClaw CLI backend docs say local AI CLIs can be used as text fallback, but for full harness runtime with background tasks and persistent external coding sessions, ACP Agents are the intended path.
- OpenClaw Feishu channel docs describe a Feishu/Lark bot over WebSocket event subscription without exposing a public webhook URL.
- A Feishu plugin repository advertises batching, mention preservation, history, access control, cards, multi-account support, and per-sender policy.

### 4. agentgateway

agentgateway is an MCP/A2A/LLM proxy and governance layer.

Fit:

- Strong tool/security gateway fit: MCP federation, OpenAPI integration, OAuth, RBAC, telemetry, guardrails, and A2A.
- Useful if this project later exposes many office tools through MCP and needs policy/observability.

Limits:

- It is not a Feishu IM bot gateway.
- It does not replace task protocol, Codex invocation, or office artifact delivery.

Verdict:

- Good future tool gateway, not the immediate Feishu event bridge.

Source:

- agentgateway README describes it as an open-source proxy for agent-to-LLM, agent-to-tool, and agent-to-agent communication, with LLM Gateway, MCP Gateway, A2A Gateway, guardrails, security, and observability.

### 5. mcp-agent + Temporal

mcp-agent can run MCP workflows on asyncio or Temporal.

Fit:

- Strong durable workflow fit. Temporal adds durable state, automatic retries, pause/resume, and human approvals.
- Strong match for the "long-running office task with approvals" requirement.
- It can keep tool access in MCP form and offload non-deterministic I/O safely.

Limits:

- It is a workflow runtime, not a Feishu channel gateway.
- If it becomes the agent orchestration layer, it may compete with Codex + superpowers.
- Running Temporal adds a server/worker dependency that is probably too heavy for the current MVP.

Verdict:

- Good post-MVP durability backend.
- Best use is to wrap task lifecycle and external side effects, while Codex remains a backend activity.

Sources:

- mcp-agent docs say switching to Temporal adds durable state, retries, and first-class pause/resume for long-running MCP tools.
- Pydantic AI Temporal docs explain that model requests, tool calls, and MCP communication should be Temporal activities while workflow code coordinates execution.

### 6. LangGraph / LangGraph Platform

Fit:

- Strong durable agent workflow fit: persistence, thread identifiers, checkpointers, pause/resume, and human-in-the-loop.

Limits:

- It is an agent/workflow orchestration framework. Using it as the main planner would conflict with the Codex + superpowers boundary.
- It does not give us Feishu ingress by itself.

Verdict:

- Good conceptual reference for durable state and human-in-the-loop.
- Not the preferred implementation unless we intentionally add a second orchestration framework.

Source:

- LangGraph docs define durable execution as saving workflow progress at key points for pause/resume, human-in-the-loop, and failure recovery.

### 7. n8n

Fit:

- Strong low-code workflow fit. It has triggers, HTTP nodes, AI Agent nodes, sub-agent tools, and community Lark/Feishu packages.
- Good for stable, visible automations, especially if the agent should call prebuilt workflows.
- Strong decoupling fit for repeatable office operations: a Codex agent can call a single n8n webhook instead of manually orchestrating every API call.

Limits:

- Lark/Feishu support appears to rely on community nodes or manual HTTP requests, not a first-class official Feishu bot gateway in the same way LangBot/OpenClaw target chat channels.
- n8n's AI Agent would become another planner if used directly for reasoning.
- Better as an external workflow/tool surface than as the project gateway.

Verdict:

- Useful future "workflow wheel" that Codex can call.
- Not the best replacement for IM-to-Codex gateway.
- Demoted for gateway selection because this project needs a harness gateway, not a traditional workflow engine.

Sources:

- n8n docs describe AI Agent Tool nodes for root agents to call other agents as tools.
- Community Lark node packages integrate with Lark/Feishu using the official Lark SDK, but they come with community-node operational risk.
- One n8n Feishu/Lark community node includes `Send and Wait` for human-in-the-loop and `Send Streaming Message` for pushing AI Agent output to Feishu through a webhook.
- Chinese community/Bilibili/Zhihu examples commonly use n8n with Feishu group robots for message push, daily summaries, RPA-like workflows, and AI Agent workflows. These validate demand and patterns, but they are usually workflow demos rather than durable Codex task gateways.

### 8. Dify / FastGPT

Fit:

- They provide application builders, workflows, knowledge bases, and Lark/Feishu publishing or trigger plugins.
- Good for RAG/customer-service style bots.

Limits:

- They are opinionated app builders and can become the main agent/product layer.
- Direct Lark support can be edition/plugin dependent.
- Harder to keep Codex + superpowers as the sole planner.

Verdict:

- Useful reference or optional integration, but not ideal for this project's Codex-driven office automation.
- Demoted for gateway selection because they are application/workflow builders rather than coding-agent harness gateways.

Sources:

- Dify marketplace Lark Trigger plugin connects Dify workflows with Lark events.
- FastGPT docs state direct Lark bot integration starts from version 4.8.10 in the commercial edition.
- Chinese selection guides tend to position Dify for low-cost AI app/RAG construction, n8n for flexible automation, and Coze for quick bot building. That reinforces the split: use them as app/workflow tools, not as this project's Codex harness.

### 9. go-lark / OpenFeishu / SDK-level wheels

Fit:

- Good if a custom service is unavoidable.
- go-lark supports Feishu/Lark messaging APIs, chat bots, notification bots, rich text/cards, incoming hooks, encryption, token verification, and Gin/Hertz middleware.
- OpenFeishu and similar SDKs can reduce raw API work in Python.

Limits:

- SDKs are not gateways. They reduce API wrapping but still require us to implement event service, queue, task protocol, retry, delivery, and observability.
- go-lark only covers messaging/group/bot APIs and explicitly does not cover Docs, Calendar, and other office APIs.

Verdict:

- Use only if gateway products cannot satisfy the Feishu channel requirement.
- Prefer lark-cli/openapi-mcp for office operations.

Source:

- go-lark README says it implements Feishu/Lark messaging APIs, supports chat/notification bots, rich messages/cards, incoming hooks, encryption, and middleware, but limits scope to messaging/group/bot APIs.

## Requirement Fit Matrix

| Candidate | Feishu ingress | Task durability | Codex backend fit | Office tool fit | MVP cost | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| GolemBot | Strong | Unknown/Medium | Strong if Codex engine works | Medium | Medium | Best gateway replacement candidate |
| OpenClaw ACP / Codex Harness | Strong if channel/plugin works | Medium/Strong | Strong, but heavy | Medium | High | Best harness reference |
| lark-cli event + thin adapter | Strong | Thin adapter needed | Strong | Strong | Low | Best MVP |
| LangBot | Strong | Plugin needed | Medium | Medium | Medium | Best channel replacement candidate |
| AstrBot | Strong | Plugin needed | Medium | Medium | Medium | Python-friendly fallback |
| OpenClaw Gateway | Strong if plugin works | Medium | Medium/High as MCP bridge, risky as planner | Medium | High | Best architecture reference |
| agentgateway | Weak for IM | Weak | High as tool proxy | High for MCP/OpenAPI | Medium | Future tool gateway |
| mcp-agent + Temporal | Weak for IM | Strong | Medium as activity backend | High for MCP | High | Post-MVP durability |
| LangGraph | Weak for IM | Strong | Low/Medium due orchestration overlap | Medium | High | Reference only for now |
| n8n | Medium | Medium | Medium as callable workflow | Medium/High | Medium | Future workflow tool |
| Dify/FastGPT | Medium | Medium | Low/Medium | Medium | Medium/High | Not primary |

## Recommended Direction

Do not frame the project as "we wrote a Python Bridge from scratch." Frame it as:

```text
Feishu channel wheel
  -> thin task adapter
  -> Codex + superpowers backend
  -> office tool wheels
  -> delivery back to Feishu
```

For the current MVP:

- Keep `lark-cli event +subscribe` as the Feishu channel wheel.
- Keep only a thin local adapter for dedupe, task directory creation, status/artifact protocol, and invoking Codex.
- Avoid writing Feishu API logic ourselves.

For the next upgrade, evaluate gateway replacements in this order:

- Add a gateway abstraction with pluggable adapters:
  - `lark-cli-file` for current MVP.
  - `golembot` for Codex-native IM gateway evaluation.
  - `openclaw-acp` for full harness gateway evaluation.
  - `langbot` for ready-made bot gateway evaluation.
  - `astrbot` for Python-friendly IM bot platform evaluation.
  - `openclaw-mcp` for OpenClaw Gateway evaluation.
- Keep `CodexTaskBackend` separate from channel adapters.
- Keep task completion based on `status.json` and `artifacts.json`.

For post-MVP:

- If durability becomes the bottleneck, evaluate mcp-agent + Temporal or Temporal directly.
- If tool governance becomes the bottleneck, evaluate agentgateway.
- If repeatable deterministic workflows become the bottleneck, expose n8n workflows as tools for Codex to call.

## Current Decision

The Python code should shrink toward an adapter, not grow into a framework.

The immediate implementation should not replace the current lark-cli path until LangBot or OpenClaw is tested end-to-end with:

1. Feishu group `@bot` event.
2. Task creation.
3. Codex local artifact generation.
4. Feishu Doc/Slides/Whiteboard creation.
5. Final reply with artifact links.
6. Restart/retry behavior.

If a candidate cannot handle all six, it is a reference or partial wheel, not the project gateway.

The most promising replacement test is now:

```text
GolemBot Feishu adapter
  -> Codex engine in this repository
  -> task protocol prompt
  -> local artifacts
  -> lark-cli delivery
```

If GolemBot can keep Codex sessions coherent and expose enough Feishu message metadata, it may replace most of `scripts/subscribe_feishu_events.py`, `scripts/run_event_consumer.py`, and `scripts/process_feishu_event.py`.
