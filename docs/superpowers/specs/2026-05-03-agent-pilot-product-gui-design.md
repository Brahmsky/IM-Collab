# Agent-Pilot Product GUI Design

## Status

This document records the target product GUI direction discussed on 2026-05-03. It replaces the temporary web console as the reference for future frontend work.

The current Python web console remains an engineering surface. The target GUI should be treated as a polished Agent-Pilot product cockpit that is visually close to the provided reference screenshot: a light desktop app with a left task/session sidebar, a central agent conversation workspace, and a right task detail/artifact panel.

## Product Goal

Build a high-fidelity Agent-Pilot desktop-style cockpit for observing and steering IM-Collab tasks.

The GUI is not the main user entry point. Feishu group chat remains the natural user surface. The GUI exists for operators and power users who need to see active sessions, inspect task progress, add steering instructions, interrupt work, and open generated artifacts.

The GUI must share the same Codex execution backend as Feishu:

```text
Feishu group message
GUI input message
  -> same Bridge control/input channel
  -> same Codex app-server thread or active turn
  -> same task protocol
  -> same artifact delivery model
```

This means the GUI must not become a separate workflow engine or planner. It is another input and observation surface over the existing Agent-Pilot loop.

## Visual Reference

The reference screen has four stable regions:

1. Left rail: Agent-Pilot brand, utility actions, grouped chat/session navigation, settings.
2. Top workspace title: selected session title and lightweight window/action controls.
3. Center workspace: user request bubble, agent response, execution checklist, artifact cards, and bottom input composer.
4. Right inspector: task metadata, state, source group, target outputs, task id, and artifact list.

The first implementation should prioritize matching this composition over adding extra features. If a feature does not fit this frame cleanly, leave it out or mark it as future work.

## Layout Contract

### Left Sidebar

The left sidebar shows where the bot is deployed and which sessions exist under each group.

Required content:

- Brand row: Agent-Pilot logo and name.
- Utility actions:
  - New task: still unresolved; keep as a visible but low-risk action until product semantics are decided.
  - Search: character-level search across sessions.
  - Plugins: unresolved; likely hidden or disabled in the first product build unless there is a concrete plugin catalog.
  - Automation: unresolved; likely hidden or disabled in the first product build unless there is a concrete automation model.
- Task groups:
  - Each Feishu group where the bot is installed appears as a collapsible group.
  - Each group contains multiple sessions.
  - The active session is highlighted with a soft background and a blue indicator dot.
- Settings at the bottom.

The reference example contains three groups:

- 项目答辩群
- 客户反馈群
- 运营复盘群

These names are examples. Real data should come from Feishu chat metadata and task/session bindings.

### Session Model

A single Feishu group can contain many sessions.

The intended user-facing model is:

```text
Feishu group
  -> sessions created by explicit user action
  -> tasks and Codex turns inside a session
  -> artifacts produced or modified by those turns
```

The primary way to create a new session in a group is:

```text
@bot /new <user request>
```

or a Chinese equivalent such as:

```text
@bot 新开任务：<user request>
```

After `/new`, later bot-related group messages are attached to that new session until the session is closed, another session is explicitly selected, or a new session is started.

The GUI should expose sessions by human-readable titles, not raw `task_id`, `codex_thread_id`, or `turn_id`. Technical ids belong in the right inspector or debug expansion, not in the primary sidebar label.

### Search

Search is character-level session search.

Search should match:

- session title
- source group name
- latest summary
- artifact labels
- optionally task id for operators

Search is not an agentic semantic query in the first product GUI. It should be fast, predictable, and local.

### Center Workspace

The center workspace is a conversation-like task cockpit.

It should render:

- the initiating user request as a rounded bubble near the top
- the latest agent message
- an execution checklist
- generated or pending artifact cards
- a bottom input composer

The reference checklist shape:

```text
收到，正在为你梳理并生成相关材料，执行计划如下：

✓ 读取项目群聊上下文，提取关键信息与待办
✓ 整理第二周周进展与成果，撰写简报草稿
○ 生成 PPT 大纲
○ 撰写回传消息草稿

已生成 3 个产物
```

The checklist should be driven by task/run state when available, but early versions may use coarse task protocol milestones:

- read context
- build source-grounded brief
- run Codex task
- generate artifacts
- deliver results

Avoid hardcoding office deliverable types into the data layer. The UI may display example labels such as 简报草稿 or PPT 大纲, but the source of truth is `artifacts.json -> items[]` exposed through `TaskIndex.artifact_outputs`.

### Artifact Cards

Artifact cards in the center workspace and right inspector should represent arbitrary artifact items.

Each card should show:

- icon derived from artifact kind or MIME-like type
- human label
- local or remote format hint, such as `docx · 1,240 字`
- status: completed, generating, pending, failed
- if remote is available, a link or open action

The UI can visually specialize common office kinds:

- document / docx / markdown
- slides / ppt / deck
- text reply draft
- whiteboard / diagram
- file / attachment

But these specializations must be presentation adapters only. They must not reintroduce a fixed `document_url/slides_url/whiteboard_token` task model.

### Bottom Composer

The bottom composer sends messages into the same execution path as Feishu follow-up messages.

Conceptually:

```text
GUI composer message
  -> append_control_command(..., "append_instruction", payload)
  -> if active Codex turn exists: steer/append to active turn
  -> else attach to waiting or selected session
```

For Codex, the message should preserve its source:

```json
{
  "source": "gui",
  "kind": "operator_followup",
  "text": "补充团队分工，并把 PPT 初稿改成 5 分钟答辩版"
}
```

Feishu messages should likewise preserve their source:

```json
{
  "source": "feishu",
  "kind": "group_followup",
  "chat_id": "...",
  "message_id": "...",
  "text": "把刚才 PPT 改成 5 分钟答辩版"
}
```

The Bridge should pass the original natural language through to Codex rather than classifying it through brittle keyword routing.

### Right Inspector

The right panel shows task details for the selected session.

Required fields:

- status
- source group
- target or user-visible goal
- created time
- task id
- artifact count
- artifact list

Optional advanced fields:

- Codex thread id
- active turn id
- context pack id
- latest source-grounded brief
- unresolved conflicts/open questions
- control log entries

Advanced fields should be hidden behind an operator/debug disclosure, not shown by default in the polished product view.

## Data Model Mapping

The product GUI should use an adapter layer instead of reading raw files directly in components.

Input sources:

- `tasks/task-bindings.json`
- `tasks/<task_id>/status.json`
- `tasks/<task_id>/artifacts.json`
- `tasks/<task_id>/request.md`
- `tasks/<task_id>/control.jsonl`
- future context pack files
- future source-grounded briefing files
- Feishu chat metadata where available

Suggested frontend view model:

```text
WorkspaceView
  groups[]
    group_id
    group_name
    sessions[]
      session_id
      title
      latest_status
      latest_updated_at
      active_task_id
      artifact_count

SelectedSessionView
  session_id
  source_group
  title
  user_request
  agent_messages[]
  execution_steps[]
  artifacts[]
  task_detail
  composer_state
```

This view model can be served by Python first and later moved to a TypeScript/React sidecar if the frontend becomes a larger application.

## Codex Output Return Path

The difficult part is not static layout. The difficult part is making Codex progress feel live.

There are three levels of implementation:

1. Snapshot polling: read `status.json`, `artifacts.json`, and `control.jsonl` periodically. This is sufficient for the first polished visual implementation.
2. Structured progress events: Bridge writes step updates and artifact state changes as append-only events. The GUI subscribes or polls.
3. Codex app-server live stream: GUI receives assistant deltas, tool calls, and run state from the persistent Codex backend through a controlled API.

The first product GUI should be designed so level 1 works immediately and level 2/3 can replace the data source without redesigning the layout.

The GUI should not parse terminal text or tmux logs as the source of truth. Task protocol files and app-server events are the durable boundary.

## Open Design Reference Usage

Use `/home/lifei/.codex/open-design` as a design reference, not as the main runtime dependency.

Recommended references:

- `skills/dashboard`: layout thinking for sidebar + control panel surfaces.
- `skills/critique`: post-build design review rubric.
- `skills/tweaks`: later visual tuning suggestions.
- `craft/anti-ai-slop.md`: avoid generic AI dashboard tropes.
- `design-systems/application`: closest default style family for a light desktop app.
- `design-systems/raycast`, `design-systems/superhuman`, or `design-systems/linear-app`: useful references for app precision, but avoid blindly copying dark-mode styles.

Open Design should inform visual craft and review loops. It should not replace IM-Collab's Codex + superpowers orchestration boundary.

## Visual Quality Bar

The first serious UI implementation should not be a throwaway minimal version.

Quality requirements:

- Match the reference screenshot composition closely.
- Use stable three-column desktop layout.
- Use restrained light surfaces, subtle borders, and calm blue/purple accents.
- Keep cards at compact radius and avoid nested-card clutter.
- Avoid decorative blobs, generic gradients, emoji icons, and invented metrics.
- Use real-looking Agent-Pilot task data, not placeholder dashboard metrics.
- Text must not overflow, collide, or resize containers unexpectedly.
- Primary icon buttons should use a real icon library if available.

## Verification

Visual verification should use browser screenshots.

Preferred path:

- Playwright for deterministic screenshot and interaction checks.
- Camoufox may be used if it is available globally and works better in the local environment.

Required checks before considering the UI acceptable:

- desktop screenshot at the same aspect ratio as the reference image
- narrower desktop/tablet screenshot
- search interaction
- session selection
- composer send action writes the expected control command
- artifact card rendering for completed/generating/pending states
- no visible layout overflow

The visual target is not "roughly nicer than the current console". The target is high-fidelity enough that the screenshot reads as the same product family as the provided reference.

## Product Decisions Still Open

These should not block the first visual build, but they must stay visible:

- Whether the left "New task" button creates a GUI-only `/new` flow, opens a command composer, or is removed.
- Whether "Plugins" should exist before a real plugin catalog exists.
- Whether "Automation" should exist before a real automation model exists.
- How much operator-only detail should be visible by default.
- Whether the product GUI should eventually be a desktop shell, local web app, or both.

## Non-Goals

- Do not make the GUI an agent planner or workflow router.
- Do not reintroduce keyword-based intent classification in the frontend.
- Do not expose raw Codex thread mechanics to ordinary users.
- Do not build the final UI by continuing to enlarge the old Python string-based web console.
- Do not hardcode fixed deliverables as document/slides/whiteboard in the task model.

## Near-Term Implementation Direction

The recommended implementation path is:

1. Keep the existing engineering console intact for debugging.
2. Add a separate product GUI surface or route, rather than mutating the old console into the final UI.
3. Build a typed view adapter over task bindings, task status, control logs, and artifact items.
4. Render the screenshot-like layout with realistic fixture data first.
5. Wire session selection, search, artifact display, and composer control-command writing.
6. Add polling or event streaming for live task state.
7. Run Open Design-style critique and screenshot verification.

This keeps frontend polish and backend correctness decoupled while still ensuring the product GUI reflects the real Agent-Pilot session model.
