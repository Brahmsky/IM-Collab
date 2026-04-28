# GUI Wheels Evaluation

This note evaluates existing GUI/control-console wheels for the Agent-Pilot cockpit.

The project boundary remains unchanged: Codex + superpowers is the only orchestration layer. GUI tools may observe, control, or forward instructions to the task protocol, but they must not become the planner/executor.

## Packaging Decision: Web/TUI First, Desktop Optional

The competition-facing requirement is not "ship a desktop app". The user-facing product surface is Feishu IM plus Feishu documents/slides/whiteboards across desktop and phone. The operator-facing GUI should prove that tasks are observable and controllable: task state, IM events, artifacts, active runs, interrupt/append/retry controls, and audit history.

Tauri is therefore an optional packaging choice, not a required architecture layer. It is useful if we adopt a desktop-native Codex cockpit such as CodexMonitor, or if the final demo needs a polished desktop shell. It is not necessary for the core Agent-Pilot capability, and making it mandatory would add Rust/Tauri build and distribution work before the task protocol needs it.

Recommended stance:

- Keep the control surface web/TUI-first while the protocol is still changing.
- Do not spend project risk on desktop packaging until the task protocol, live session control, and Feishu group workflow are stable.
- Treat Tauri as a later packaging wrapper or as part of CodexMonitor only, not as a custom GUI stack we build from scratch.

Tauri source:

- `https://tauri.app/`

## Requirements

- Show task protocol state from `tasks/<task_id>/status.json`.
- Show delivery outputs from `tasks/<task_id>/artifacts.json`.
- Show Feishu event intake from `events/`.
- Surface whether a task is queued, running, waiting for user, completed, or failed.
- Support operator actions later: cancel, retry, append instruction, mark acknowledged.
- Avoid replacing Feishu as the user-facing office UI.
- Avoid replacing Codex + superpowers as the agent harness.

## Candidate: AgentPulse

Fit:

- The public material describes live monitoring for Claude Code and Codex CLI sessions, a web dashboard, session timelines, tool usage visibility, notes, AGENTS.md viewing/editing, and local-first operation.
- A separate AgentPulse page focuses on mobile supervision for terminal agents: push notification, all agents in one view, sending commands back, tmux/Kitty/iTerm2/WezTerm support, and Codex CLI support.

Limits found during local verification:

- The repository URL mentioned in the article, `https://github.com/jaystuart/agentpulse`, returned `Repository not found` during `git ls-remote`.
- The mobile-oriented site links to GitHub, but the accessible source target was not usable from this environment during this pass.
- The product shape is agent-session-centric, not task-protocol-centric. Even if it becomes installable, we still need a task protocol dashboard for `tasks/` and `events/`.

Verdict:

- Keep as a high-value reference for Agent Session Cockpit UX.
- Do not block the project on it until the source/install path is verified.

Sources:

- AgentPulse article: live monitoring for Claude Code and Codex CLI, web dashboard, prompt history, timeline, tool usage, notes, AGENTS.md support, local-first setup.
- AgentPulse mobile page: tmux/Kitty/iTerm2/WezTerm detection, Codex CLI support, phone-to-computer commands, self-hosted server.

## Candidate: Agent Sessions / Agent Cockpit

Fit:

- The project supports Codex CLI, Claude Code, Cursor CLI, Gemini CLI, Copilot CLI, OpenCode, and OpenClaw.
- It provides a local-first session browser, unified search, live HUD for active iTerm2 sessions, resume commands, saved sessions, and usage tracking.
- The GitHub repository is reachable.

Limits:

- It is native macOS and mostly read-only by design.
- It is optimized for browsing/resuming local coding-agent sessions, not controlling this repository's office task protocol.
- It does not directly display Feishu event ingestion, `status.json`, or `artifacts.json`.

Verdict:

- Useful as a reference or optional local developer tool.
- Not the main competition GUI because it is not cross-platform and does not expose task-level controls.

Source:

- `https://jazzyalex.github.io/agent-sessions/`
- `https://github.com/jazzyalex/agent-sessions`

## Candidate: CodexMonitor

Fit:

- Strong Codex fit. It is a Tauri app specifically for orchestrating multiple Codex agents across local workspaces.
- It uses the Codex app-server protocol, can spawn or connect to a Codex app-server, resume threads, track unread/running state, stop/interrupt in-flight turns, and support worktree/clone agents.
- It has composer controls for queue vs steer while a run is active, model picker, access mode, reasoning effort, context usage, skill autocomplete, prompt autocomplete, and file path autocomplete.
- It is open source and supports macOS/Linux/Windows build targets in principle through Tauri.
- It already exposes the exact class of operator controls IM-Collab eventually needs for Codex sessions: start thread, send user message, steer, interrupt, resume, read thread, list threads, compact thread, fork thread, list skills, and list apps.
- Its official site positions it as a desktop command center for any number of Codex agents across projects, with workspace orchestration, thread control, worktree agents, Git/GitHub insight, model/access controls, plans/reviews, skills/prompts, and Tauri + React packaging.

Limits:

- It is Codex-centric and code-workspace-centric, not Feishu/task-protocol-centric.
- It assumes `codex app-server`, while the current IM-Collab execution path uses `codex exec` and task files.
- Integrating it deeply may require moving from headless `codex exec` to app-server sessions, which is a bigger architecture change.
- It brings a TypeScript/React/Tauri/Rust application into a Python-bridge repository. That is acceptable as a sidecar or fork, but too heavy as the first custom GUI layer.
- It does not natively understand `tasks/<task_id>/status.json`, `artifacts.json`, or `events/`; those would need an adapter or a separate dashboard.

Verdict:

- Best candidate for a real Codex session cockpit if we decide to manage persistent Codex app-server sessions.
- Do not wire it into the MVP until we decide whether IM-Collab should move from `codex exec` to app-server session management.
- Keep as the strongest reference for "Agent Pilot cockpit" semantics: interrupt, steer, resume, worktree isolation, and per-run controls.

Source:

- `https://github.com/Dimillian/CodexMonitor`
- `https://www.codexmonitor.app/`

## Candidate: Codeman

Fit:

- Modern WebUI around tmux sessions with mobile-first UI, xterm.js terminal, multi-session dashboard, respawn controller, real-time terminal rendering, per-session token/cost tracking, and one-click management.
- It uses tmux, supports background service deployment, has mobile access options, and exposes persistent session behavior.
- Good match for "operator can see and steer agent terminals from desktop/phone".

Limits:

- Current README emphasizes Claude Code and OpenCode support; Codex support was not verified from the README in this pass.
- It is a terminal-session control plane, not a task-protocol dashboard.
- It may overlap with our bridge/session management if adopted wholesale.

Verdict:

- Strong candidate for terminal cockpit if Codex support is confirmed.
- Keep as a deployment experiment, not as the task-state source of truth.

Source:

- `https://github.com/Ark0N/Codeman`

## Candidate: vibe-kanban

Fit:

- Very mature AI coding agent workspace UI with kanban issues, agent workspaces, branches, terminals, dev server preview, diff review, PR creation, and support for Claude Code, Codex, Gemini CLI, GitHub Copilot, Amp, Cursor, OpenCode, Droid, CCR, and Qwen Code.
- It is easy to start with `npx vibe-kanban`.
- It is a strong reference for task planning/review GUI.

Limits:

- README says "Vibe Kanban is sunsetting"; adoption risk is high.
- It is a coding-agent product workflow, not an office-agent task protocol dashboard.
- Heavy Rust/TypeScript stack compared with this repository's Python bridge.

Verdict:

- Good UX reference for kanban + agent workspace + review flow.
- Not a dependency candidate unless its sunset status changes or a fork is chosen.

Source:

- `https://github.com/BloopAI/vibe-kanban`

## Candidate: CliDeck

Fit:

- Browser dashboard for multiple AI CLI agents.
- Supports Claude Code, Codex, Gemini CLI, OpenCode, Shell, and arbitrary terminal tools.
- Provides live status, message previews, session resume, project grouping, prompt library, search, plugins, browser/sound notifications, mobile remote control, and an autopilot that routes output between agents.
- MIT licensed.
- Published as an npm package (`clideck`), Node 18+, with a simple local browser surface on port 4000.
- Uses `node-pty`, WebSocket, xterm.js, and OpenTelemetry/notify hooks for status rather than replacing the agent terminal.
- Its Codex preset is first-class: command `codex`, resume command `codex resume {{sessionId}}`, Codex session-id regex, and optional Codex telemetry configuration.
- The server exposes useful control primitives: spawn PTY sessions, send input, resize, rename, mute, close, restart, group by project, and create programmatic sessions through plugins.
- It has a plugin system. A thin IM-Collab plugin could read `tasks/`, show task protocol state, and eventually send controlled prompts/commands to a Codex session.

Limits:

- It is an agent terminal dashboard, not a Feishu office task dashboard.
- Autopilot routing can become a second orchestrator if enabled, which conflicts with the Codex + superpowers boundary.
- Its default Codex path is interactive `codex`, not the current headless `codex exec` task runner.
- One-click Codex telemetry setup may edit `~/.codex/config.toml`; that should be opt-in, not part of the project bootstrap.
- Linux is described as untested in the README, so local validation is required before making it a recommended dependency.

Verdict:

- Good candidate for a lightweight browser cockpit around terminal agents.
- If evaluated, use only session/status/control features and disable or ignore autopilot.
- Better first spike than CodexMonitor if the goal is "operator can watch and steer CLI sessions from browser/mobile" with minimal architecture change.
- Do not let CliDeck Autopilot become the project orchestrator. Codex + superpowers remains the planner/executor; CliDeck is only a cockpit.

Source:

- `https://github.com/rustykuntz/clideck`
- `https://clideck.dev/`
- `https://www.npmjs.com/package/clideck`

## Candidate: amux

Fit:

- Web dashboard and mobile PWA for many tmux-backed agent sessions.
- Provides live session cards, status, token stats, terminal peek, send bar, board, notes, file browser, scheduler, and APIs for sending text, peeking output, starting/stopping sessions.
- Single-file / low-dependency shape is attractive for quick local deployment.

Limits:

- Current README says it supports Claude Code via tmux. Codex support was not verified as first-class.
- It includes broad CRM/email/browser automation features that are outside IM-Collab scope.
- Its agent-to-agent orchestration can become an undesired second control plane.

Verdict:

- Good source of ideas for tmux-backed web controls and mobile PWA.
- Candidate only if Codex support is validated or if we use its API patterns rather than adopting it.

Source:

- `https://github.com/mixpeek/amux`

## Candidate: claude-squad

Fit:

- Tmux-based manager for multiple AI terminal agents.
- README shows Codex profiles through a configurable `program` field.
- Mature compared with small dashboard experiments and simple to reason about.

Limits:

- It is terminal/TUI oriented and primarily branded around Claude Code.
- It does not understand IM-Collab task directories, Feishu events, or office artifacts.
- AGPL-3.0 license may complicate reuse depending on distribution plan.

Verdict:

- Useful for local operator session management.
- Better as a reference or side tool than project GUI.

Source:

- `https://github.com/smtg-ai/claude-squad`

## Candidate: cmux

Fit:

- Open-source macOS terminal built for AI coding agents, with notification rings, notification panel, browser split, session restore, and saved Claude Code/Codex sessions when resume tokens are available.
- It directly targets the "many terminal agents waiting for input" problem.

Limits:

- macOS/Ghostty-centered.
- GPL-3.0-or-later licensing may affect reuse.
- It is a terminal app, not a task protocol dashboard.

Verdict:

- Good local Mac operator experience and UX reference.
- Not the default project GUI because IM-Collab should stay Linux-friendly and task-protocol-first.

Source:

- `https://github.com/manaflow-ai/cmux`

## Candidate: z4j

Fit:

- Open-source control plane for Python task queues: Celery, RQ, Dramatiq, Huey, arq, and taskiq.
- Provides dashboard/API with retry, cancel, bulk actions, reconciliation, and monitoring.
- Runs locally with bundled SQLite.

Limits:

- It assumes tasks are in conventional queue backends, while IM-Collab currently uses a filesystem task protocol.
- Moving to z4j would mean introducing a real queue abstraction.
- It is useful for future productionization, not the current file-protocol MVP.

Verdict:

- Good future candidate if we migrate from file-only tasks to a Python queue backend.
- Not immediate unless we explicitly choose Celery/RQ/Dramatiq/Huey/taskiq.

Source:

- `https://z4j.com/`

## Candidate: Magentic-UI

Fit:

- Strong reference for human-in-the-loop interaction.
- It supports co-planning, interrupting/guiding task execution, approval guards, plan learning, and parallel task status indicators.

Limits:

- It is built on AutoGen and is a web-agent research platform.
- Adopting it as the main UI/runtime risks moving orchestration away from Codex + superpowers.
- It is better as an interaction reference than a dependency for the current architecture.

Verdict:

- Borrow interaction concepts: plan view, action guards, interrupt/chat guidance, and parallel task indicators.
- Do not adopt as the main GUI runtime.

Source:

- `https://github.com/microsoft/magentic-ui`

## Candidate: Textual

Fit:

- Open-source Python TUI framework.
- Official positioning includes internal tooling and real-time monitoring of running processes.
- It matches the current repository language and can read local files without adding a web stack.
- It lets us build a cockpit around the existing task protocol while reusing a UI framework instead of hand-writing terminal rendering.

Limits:

- Textual is a framework, not a prebuilt Agent dashboard.
- We still need to write thin adapters for `tasks/`, `events/`, and future control commands.
- The dependency is not currently installed.

Verdict:

- Best near-term implementation wheel for the competition control console.
- Keep the first version read-mostly: task list, detail view, artifacts, event count, and clear operator commands shown as disabled or dry-run until control protocol exists.

Source:

- `https://www.textualize.io/`

## Candidate: Laminar / TraceDog / OpenSearch Agent Health

Fit:

- Strong observability/evaluation/tracing direction.
- Useful for later quality analytics, latency, token/cost, grounding, and trace comparison.

Limits:

- They do not directly control this repository's task protocol.
- They are more useful once we have structured traces/spans, not as the first GUI.

Verdict:

- Post-MVP observability candidates.
- Not the immediate cockpit.

## Recommended Route

1. Keep the IM-Collab task protocol as the source of truth: `tasks/`, `events/`, `status.json`, and `artifacts.json`.
2. Keep the current Python console path for task-protocol visibility because it is already aligned with the repository boundary.
3. Spike CliDeck first as an external browser/mobile cockpit for live Codex CLI sessions. Use only session/status/control features; disable or ignore Autopilot.
4. Keep CodexMonitor as the high-fit later option if we decide to move execution from `codex exec` to persistent `codex app-server` sessions.
5. Do not make Tauri mandatory. Use it only if CodexMonitor becomes the chosen cockpit or the final deliverable needs a desktop shell.
6. Add write controls only after a control-command protocol exists, such as `tasks/<task_id>/control.jsonl`.
