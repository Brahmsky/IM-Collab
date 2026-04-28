# Agent Pilot Product Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current Agent-Pilot MVP into a product-shaped closed loop: Feishu card actions resume tasks, follow-up requests modify existing artifacts, group briefings remain source-grounded, and the cockpit shows enough state for live operation.

**Architecture:** Keep Codex + superpowers as the only planner/executor. Python Bridge owns event parsing, durable task state, card callback routing, and task control commands. Feishu remains the user-facing multi-end surface; local console remains an operator cockpit.

**Tech Stack:** Python 3.11+, pytest, lark-cli, Feishu long-connection event files, Codex app-server, task directories under `tasks/<task_id>`, JSON/JSONL file protocol.

---

## Current Gap Summary

The current repository already has:

- Feishu IM ingress through event files.
- Group-chat source-grounded `brief.json` and `brief.md`.
- `waiting_for_user` gate when conflicts/open questions are found.
- `confirmation_card.json` and `delivery_card.json`.
- Interactive card sending through `lark-cli im +messages-reply --msg-type interactive --content`.
- Codex app-server thread reuse and active-turn steering.
- CLI/web control console over `tasks/`, `events/`, and `control.jsonl`.

The missing product closures are:

- Feishu card button callbacks are not parsed or routed.
- A "start" button does not yet resume a waiting task.
- Follow-up modification requests do not yet consistently bind to prior artifacts.
- Brief extraction is still heuristic and should be made more inspectable.
- The GUI is an engineering console, not a polished operator cockpit.

## File Structure

- Modify `bridge/feishu_events.py`: parse both IM message events and interactive card callback events into typed event objects.
- Modify `bridge/golembot_dispatch.py`: route card callbacks to waiting tasks or task controls without creating new tasks.
- Modify `bridge/group_briefing.py`: keep card action values stable and include task/session hints that callback routing can trust.
- Modify `bridge/golembot_office_loop.py`: make resumed waiting tasks consume card-originated control commands as first-class confirmation context.
- Modify `bridge/codex_app_server_task_runner.py`: ensure follow-up modification prompts include prior `artifacts.json`, `brief.json`, and `control.jsonl`.
- Modify `bridge/task_index.py` and `bridge/task_console_web.py`: expose card callback state, waiting confirmations, and active controls in the cockpit.
- Add `tests/test_feishu_card_events.py`: card callback parser tests.
- Extend `tests/test_golembot_dispatch.py`: callback routing and card-start resume tests.
- Extend `tests/test_golembot_office_loop.py`: resumed waiting task consumes confirmation commands.
- Extend `tests/test_codex_app_server_backend.py` or existing runner tests: follow-up prompt includes prior artifacts and controls.
- Update `README.md`: document card callback event subscription and product flow.

---

### Task 1: Parse Feishu Interactive Card Callback Events

**Files:**
- Modify: `bridge/feishu_events.py`
- Test: `tests/test_feishu_card_events.py`

- [ ] **Step 1: Write the failing parser tests**

Create `tests/test_feishu_card_events.py`:

```python
from __future__ import annotations

from bridge.feishu_events import parse_card_action_event


def test_parse_compact_card_action_event() -> None:
    payload = {
        "type": "card.action.trigger",
        "message_id": "om_card",
        "open_id": "ou_user",
        "chat_id": "oc_group",
        "action": {"value": {"action": "start_task", "task_id": "im-om_waiting"}},
    }

    parsed = parse_card_action_event(payload)

    assert parsed.message_id == "om_card"
    assert parsed.chat_id == "oc_group"
    assert parsed.sender_open_id == "ou_user"
    assert parsed.action == "start_task"
    assert parsed.task_id == "im-om_waiting"
    assert parsed.value == {"action": "start_task", "task_id": "im-om_waiting"}


def test_parse_lark_callback_card_action_event() -> None:
    payload = {
        "schema": "2.0",
        "header": {"event_type": "card.action.trigger"},
        "event": {
            "operator": {"open_id": "ou_user"},
            "context": {"open_message_id": "om_card", "open_chat_id": "oc_group"},
            "action": {"value": {"action": "append_requirement", "task_id": "im-om_waiting"}},
        },
    }

    parsed = parse_card_action_event(payload)

    assert parsed.message_id == "om_card"
    assert parsed.chat_id == "oc_group"
    assert parsed.sender_open_id == "ou_user"
    assert parsed.action == "append_requirement"
    assert parsed.task_id == "im-om_waiting"
```

- [ ] **Step 2: Run the parser tests to verify they fail**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_feishu_card_events.py -q
```

Expected: FAIL because `parse_card_action_event` is not defined.

- [ ] **Step 3: Implement the minimal parser**

In `bridge/feishu_events.py`, add:

```python
@dataclass(frozen=True)
class CardActionEvent:
    message_id: str
    chat_id: str
    sender_open_id: str
    action: str
    task_id: str
    value: dict[str, Any]
    raw: dict[str, Any]


def parse_card_action_event(payload: dict[str, Any]) -> CardActionEvent:
    if payload.get("type") == "card.action.trigger":
        value = _card_value(payload.get("action", {}))
        return CardActionEvent(
            message_id=str(payload.get("message_id", "")),
            chat_id=str(payload.get("chat_id", "")),
            sender_open_id=str(payload.get("open_id") or payload.get("sender_id") or ""),
            action=str(value.get("action", "")),
            task_id=str(value.get("task_id", "")),
            value=value,
            raw=payload,
        )

    event = payload.get("event", payload)
    value = _card_value(event.get("action", {}))
    context = event.get("context", {})
    operator = event.get("operator", {})
    return CardActionEvent(
        message_id=str(context.get("open_message_id", "")),
        chat_id=str(context.get("open_chat_id", "")),
        sender_open_id=str(operator.get("open_id", "")),
        action=str(value.get("action", "")),
        task_id=str(value.get("task_id", "")),
        value=value,
        raw=payload,
    )


def is_card_action_event(payload: dict[str, Any]) -> bool:
    return payload.get("type") == "card.action.trigger" or payload.get("header", {}).get("event_type") == "card.action.trigger"


def _card_value(action: Any) -> dict[str, Any]:
    if isinstance(action, dict) and isinstance(action.get("value"), dict):
        return action["value"]
    return {}
```

- [ ] **Step 4: Run the parser tests to verify they pass**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_feishu_card_events.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
rtk git add bridge/feishu_events.py tests/test_feishu_card_events.py
rtk git commit -m "feat: parse feishu card action events"
```

---

### Task 2: Route Card Actions Into Waiting Tasks

**Files:**
- Modify: `bridge/golembot_dispatch.py`
- Test: `tests/test_golembot_dispatch.py`

- [ ] **Step 1: Write a failing dispatch test for start button callbacks**

Append to `tests/test_golembot_dispatch.py`:

```python
def test_dispatch_card_start_action_runs_waiting_task_and_publishes(tmp_path: Path) -> None:
    event_path = tmp_path / "card-event.json"
    tasks_root = tmp_path / "tasks"
    task_dir = tasks_root / "im-om_waiting"
    task_dir.mkdir(parents=True)
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "im-om_waiting",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    event_path.write_text(
        json.dumps(
            {
                "type": "card.action.trigger",
                "message_id": "om_card",
                "chat_id": "oc_group",
                "open_id": "ou_requester",
                "action": {"value": {"action": "start_task", "task_id": "im-om_waiting"}},
            }
        ),
        encoding="utf-8",
    )
    seen: dict[str, object] = {}

    def fake_office_runner(**kwargs) -> dict[str, object]:
        seen["office_kwargs"] = kwargs
        return {"task_id": "im-om_waiting", "task_dir": task_dir.as_posix()}

    def fake_publisher(published_task_dir: Path) -> dict[str, object]:
        seen["published_task_dir"] = published_task_dir
        (published_task_dir / "delivery_card.json").write_text(
            json.dumps({"header": {"title": {"content": "办公材料已生成"}}}),
            encoding="utf-8",
        )
        return {
            "task_id": "im-om_waiting",
            "artifacts": {
                "task_id": "im-om_waiting",
                "document": {"remote": {"url": "https://feishu/doc"}},
                "slides": {"remote": {"url": "https://feishu/slides"}},
                "whiteboard": {"remote": {"whiteboard_token": "wb_123"}},
                "summary": "已发布。",
                "next_steps": [],
            },
        }

    def fake_card_replier(message_id: str, card_path: Path, idempotency_key: str, dry_run: bool) -> dict[str, object]:
        seen["card_reply"] = {"message_id": message_id, "card_path": card_path}
        return {"ok": True}

    result = dispatch_event_via_golembot(
        event_path,
        gateway_url="http://127.0.0.1:3199",
        token="secret",
        publish=True,
        execute_reply=True,
        tasks_root=tasks_root,
        office_runner=fake_office_runner,
        publisher=fake_publisher,
        card_replier=fake_card_replier,
    )

    assert seen["office_kwargs"]["task_id"] == "im-om_waiting"
    assert seen["office_kwargs"]["message"] == "开始执行"
    assert seen["published_task_dir"] == task_dir
    assert seen["card_reply"]["card_path"] == task_dir / "delivery_card.json"
    assert result["task"]["task_id"] == "im-om_waiting"
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_golembot_dispatch.py::test_dispatch_card_start_action_runs_waiting_task_and_publishes -q
```

Expected: FAIL because `dispatch_event_via_golembot` tries to parse the callback as an IM event.

- [ ] **Step 3: Implement card action routing**

In `bridge/golembot_dispatch.py`:

```python
from bridge.feishu_events import is_card_action_event, parse_card_action_event
```

At the top of `dispatch_event_via_golembot`, after loading `payload`, add:

```python
    if is_card_action_event(payload):
        return _dispatch_card_action(
            payload,
            publish=publish,
            generator=generator,
            execute_reply=execute_reply,
            tasks_root=tasks_root,
            office_runner=office_runner,
            publisher=publisher,
            replier=replier,
            card_replier=card_replier,
        )
```

Add helper:

```python
def _dispatch_card_action(
    payload: dict[str, Any],
    publish: bool,
    generator: str,
    execute_reply: bool,
    tasks_root: Path,
    office_runner: OfficeRunner,
    publisher: Publisher,
    replier: Replier,
    card_replier: CardReplier,
) -> dict[str, Any]:
    parsed = parse_card_action_event(payload)
    task_dir = tasks_root / parsed.task_id
    command = append_control_command(
        task_dir,
        "card_action",
        {
            "action": parsed.action,
            "message_id": parsed.message_id,
            "chat_id": parsed.chat_id,
            "sender_id": parsed.sender_open_id,
            "value": parsed.value,
        },
        operator="feishu_card",
    )
    if parsed.action == "start_task":
        task_result = office_runner(
            message="开始执行",
            session_key=f"feishu:{parsed.chat_id}",
            chat_id=parsed.chat_id,
            sender_id=parsed.sender_open_id,
            tasks_root=tasks_root,
            task_id=parsed.task_id,
            generator=generator,
            publish=False,
            conversation_context=[],
        )
        publish_result = publisher(Path(str(task_result["task_dir"]))) if publish else None
        if publish_result is not None:
            reply_markdown = build_delivery_markdown(publish_result["artifacts"])
            reply = _reply_with_optional_card(
                parsed.message_id,
                reply_markdown,
                f"{parsed.message_id}-card-start",
                not execute_reply,
                task_dir=Path(str(task_result["task_dir"])),
                card_name="delivery_card.json",
                replier=replier,
                card_replier=card_replier,
            )
        else:
            reply = replier(parsed.message_id, "已开始执行。", f"{parsed.message_id}-card-start", not execute_reply)
        return {"task_id": parsed.task_id, "control": command, "task": task_result, "publish": publish_result, "reply": reply}
    reply = replier(parsed.message_id, "已记录你的补充。", f"{parsed.message_id}-card-action", not execute_reply)
    return {"task_id": parsed.task_id, "control": command, "reply": reply}
```

- [ ] **Step 4: Run the callback routing test**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_golembot_dispatch.py::test_dispatch_card_start_action_runs_waiting_task_and_publishes -q
```

Expected: PASS.

- [ ] **Step 5: Run related dispatch tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_feishu_card_events.py tests/test_golembot_dispatch.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add bridge/golembot_dispatch.py tests/test_golembot_dispatch.py
rtk git commit -m "feat: route feishu card actions"
```

---

### Task 3: Make Waiting-Task Resume Consume Confirmation Controls

**Files:**
- Modify: `bridge/golembot_office_loop.py`
- Test: `tests/test_golembot_office_loop.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_golembot_office_loop.py`:

```python
def test_resumed_waiting_task_includes_control_confirmations_in_request(tmp_path: Path) -> None:
    task_dir = tmp_path / "waiting-task"
    task_dir.mkdir(parents=True)
    (task_dir / "request.md").write_text("# Existing request\n", encoding="utf-8")
    (task_dir / "status.json").write_text(
        json.dumps(
            {
                "task_id": "waiting-task",
                "state": "waiting_for_user",
                "created_at": "2026-04-28T01:00:00+00:00",
                "updated_at": "2026-04-28T01:00:00+00:00",
                "error": "需要确认",
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "control.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-04-28T01:01:00+00:00",
                "type": "card_action",
                "operator": "feishu_card",
                "payload": {"action": "start_task", "value": {"task_id": "waiting-task"}},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    run_golembot_office_task(
        message="开始执行",
        session_key="feishu:oc_group",
        chat_id="oc_group",
        sender_id="ou_requester",
        tasks_root=tmp_path,
        task_id="waiting-task",
        generator="local",
        publish=False,
    )

    request = (task_dir / "request.md").read_text(encoding="utf-8")
    assert "## Confirmation Controls" in request
    assert "card_action" in request
    assert "start_task" in request
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_golembot_office_loop.py::test_resumed_waiting_task_includes_control_confirmations_in_request -q
```

Expected: FAIL because existing task requests are not amended with confirmation controls.

- [ ] **Step 3: Implement request amendment for resumed waiting tasks**

In `bridge/golembot_office_loop.py`, import:

```python
from bridge.task_control import read_control_commands
```

After `if not task_dir.exists(): ... else: brief = None`, add:

```python
    if task_dir.exists():
        _append_confirmation_controls_to_request(task_dir)
```

Add helper:

```python
def _append_confirmation_controls_to_request(task_dir: Path) -> None:
    commands = read_control_commands(task_dir)
    confirmation_commands = [command for command in commands if command.get("type") in {"confirm_instruction", "card_action"}]
    if not confirmation_commands:
        return
    request_path = task_dir / "request.md"
    current = request_path.read_text(encoding="utf-8")
    if "## Confirmation Controls" in current:
        return
    lines = ["", "## Confirmation Controls"]
    for command in confirmation_commands:
        lines.append(f"- {command.get('type')}: {json.dumps(command.get('payload', {}), ensure_ascii=False)}")
    request_path.write_text(current.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run the waiting resume test**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_golembot_office_loop.py::test_resumed_waiting_task_includes_control_confirmations_in_request -q
```

Expected: PASS.

- [ ] **Step 5: Run office-loop tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_golembot_office_loop.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add bridge/golembot_office_loop.py tests/test_golembot_office_loop.py
rtk git commit -m "feat: include confirmations when resuming tasks"
```

---

### Task 4: Stabilize Follow-Up Modification Requests

**Files:**
- Modify: `bridge/codex_app_server_task_runner.py`
- Modify: `bridge/golembot_office_loop.py`
- Test: existing Codex app-server runner tests or `tests/test_codex_app_server_backend.py`

- [ ] **Step 1: Write a failing prompt test**

Add a test near existing app-server runner tests:

```python
def test_app_server_task_prompt_includes_existing_artifacts_and_controls(tmp_path: Path) -> None:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "request.md").write_text("# Request\n把刚才的 PPT 改成 5 分钟版\n", encoding="utf-8")
    (task_dir / "artifacts.json").write_text(
        json.dumps({"task_id": "task", "slides": {"remote": {"url": "https://feishu/slides"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (task_dir / "control.jsonl").write_text(
        json.dumps({"type": "append_instruction", "payload": {"text": "补充移动端演示"}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    prompt = build_app_server_task_prompt(task_dir, project_root=tmp_path)

    assert "artifacts.json" in prompt
    assert "https://feishu/slides" in prompt
    assert "control.jsonl" in prompt
    assert "补充移动端演示" in prompt
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_codex_app_server_backend.py::test_app_server_task_prompt_includes_existing_artifacts_and_controls -q
```

Expected: FAIL because the prompt builder is missing or does not include all context.

- [ ] **Step 3: Implement prompt context inclusion**

In `bridge/codex_app_server_task_runner.py`, expose or update `build_app_server_task_prompt(task_dir, project_root)` so it includes:

```python
parts = [
    "You are running an IM-Collab office task.",
    f"Project root: {project_root.as_posix()}",
    f"Task directory: {task_dir.as_posix()}",
    "Read request.md first.",
]
for filename in ("brief.json", "brief.md", "artifacts.json", "control.jsonl"):
    path = task_dir / filename
    if path.exists():
        parts.append(f"\n## Existing {filename}\n")
        parts.append(path.read_text(encoding="utf-8"))
parts.append("Update existing Feishu artifacts when the user asks for modifications; do not create unrelated duplicate deliverables unless necessary.")
return "\n".join(parts)
```

- [ ] **Step 4: Run the prompt test**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_codex_app_server_backend.py::test_app_server_task_prompt_includes_existing_artifacts_and_controls -q
```

Expected: PASS.

- [ ] **Step 5: Run app-server tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_codex_app_server_backend.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add bridge/codex_app_server_task_runner.py tests/test_codex_app_server_backend.py
rtk git commit -m "feat: ground follow-up turns in existing artifacts"
```

---

### Task 5: Improve Briefing Auditability Without Replacing the Skill

**Files:**
- Modify: `bridge/group_briefing.py`
- Modify: `skills/group-briefing/references/schema.md`
- Test: `tests/test_group_briefing.py`

- [ ] **Step 1: Write a failing test for annotation confidence and bucket source counts**

Append to `tests/test_group_briefing.py`:

```python
def test_group_brief_records_confidence_and_source_counts() -> None:
    brief = build_group_brief(
        chat_id="oc_group",
        messages=[
            {"message_id": "om_1", "sender_id": "teacher", "content": "周五 18:00 前提交方案。"},
            {"message_id": "om_2", "sender_id": "student", "content": "PPT 做 8 页。"},
        ],
    )

    assert all("confidence" in annotation for annotation in brief["annotations"])
    assert brief["summary"]["source_message_count"] == 2
    assert brief["summary"]["annotation_count"] == len(brief["annotations"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_group_briefing.py::test_group_brief_records_confidence_and_source_counts -q
```

Expected: FAIL because confidence/source counts are missing.

- [ ] **Step 3: Implement confidence and source counts**

In `bridge/group_briefing.py`, ensure each annotation includes:

```python
"confidence": "heuristic",
```

And ensure summary includes:

```python
"source_message_count": len(normalized_messages),
"annotation_count": len(annotations),
```

- [ ] **Step 4: Update schema docs**

In `skills/group-briefing/references/schema.md`, document:

```markdown
- `annotations[].confidence`: currently `heuristic`; future LLM-assisted extractors may use `high`, `medium`, or `low`.
- `summary.source_message_count`: number of normalized source messages.
- `summary.annotation_count`: number of generated side annotations.
```

- [ ] **Step 5: Run group briefing tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_group_briefing.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add bridge/group_briefing.py skills/group-briefing/references/schema.md tests/test_group_briefing.py
rtk git commit -m "feat: add briefing audit metadata"
```

---

### Task 6: Add Cockpit Visibility for Card Actions and Waiting Confirmations

**Files:**
- Modify: `bridge/task_index.py`
- Modify: `bridge/task_console_web.py`
- Test: `tests/test_task_index.py`
- Test: `tests/test_task_console_web.py`

- [ ] **Step 1: Write failing task index test**

Append to `tests/test_task_index.py`:

```python
def test_task_index_shows_waiting_confirmation_controls(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "task-1"
    task_dir.mkdir(parents=True)
    write_json(task_dir / "status.json", {"task_id": "task-1", "state": "waiting_for_user", "updated_at": "2026-04-28T01:00:00+00:00"})
    (task_dir / "control.jsonl").write_text(
        json.dumps({"type": "card_action", "payload": {"action": "start_task"}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    [task] = build_task_index(tmp_path / "tasks")

    assert task.pending_controls == 1
    assert task.last_control_type == "card_action"
```

- [ ] **Step 2: Run index test to verify it fails**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_index.py::test_task_index_shows_waiting_confirmation_controls -q
```

Expected: FAIL because `pending_controls` and `last_control_type` are missing.

- [ ] **Step 3: Implement task summary fields**

In `bridge/task_index.py`, add fields to `TaskSummary`:

```python
pending_controls: int = 0
last_control_type: str = ""
```

When building a summary, read `control.jsonl` and populate:

```python
controls = read_control_commands(task_dir)
pending_controls=len(controls)
last_control_type=str(controls[-1].get("type", "")) if controls else ""
```

- [ ] **Step 4: Show controls in web console cards**

In `bridge/task_console_web.py`, render a compact line:

```python
<p class="meta">controls: {task.pending_controls} {html.escape(task.last_control_type)}</p>
```

- [ ] **Step 5: Run console tests**

Run:

```bash
rtk .venv/bin/python -m pytest tests/test_task_index.py tests/test_task_console_web.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add bridge/task_index.py bridge/task_console_web.py tests/test_task_index.py tests/test_task_console_web.py
rtk git commit -m "feat: show task controls in cockpit"
```

---

### Task 7: Final Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/demo-chain.md` if demo commands are stale.

- [ ] **Step 1: Update README product-flow section**

In `README.md`, update the Feishu chain section to mention:

```markdown
- Subscribe to both IM message and card action events when the lark-cli event command supports multiple event types.
- `card.action.trigger` starts waiting tasks through `control.jsonl`.
- Follow-up text in the same active session is steered into the running Codex turn.
- Follow-up text after completion should reuse the same Codex thread and prior artifacts.
```

- [ ] **Step 2: Run full verification**

Run:

```bash
rtk .venv/bin/python -m pytest -q
rtk git diff --check
rtk .venv/bin/python -m py_compile bridge/feishu_events.py bridge/golembot_dispatch.py bridge/golembot_office_loop.py bridge/codex_app_server_task_runner.py bridge/group_briefing.py bridge/task_index.py bridge/task_console_web.py
```

Expected:

```text
all tests pass
git diff --check emits no output
py_compile exits 0
```

- [ ] **Step 3: Commit docs and any final fixes**

Run:

```bash
rtk git add README.md docs/demo-chain.md
rtk git commit -m "docs: document product closure flow"
```

If `docs/demo-chain.md` did not change, use:

```bash
rtk git add README.md
rtk git commit -m "docs: document product closure flow"
```

---

## Self-Review

- Spec coverage: card callbacks, waiting-task continuation, follow-up artifact grounding, source-grounded brief auditability, cockpit observability, and documentation are all mapped to tasks.
- Placeholder scan: no `TBD`, `TODO`, or "implement later" remains in the plan. Each task has exact files, commands, and code-level guidance.
- Type consistency: `CardActionEvent`, `parse_card_action_event`, `is_card_action_event`, `card_action`, `start_task`, `pending_controls`, and `last_control_type` use the same names across tasks.
- Scope: this plan does not attempt to redesign the final polished GUI or add voice/offline support. Those remain later product tracks after the core loop is closed.
