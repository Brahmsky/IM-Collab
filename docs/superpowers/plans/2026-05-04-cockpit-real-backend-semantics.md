# Cockpit Real Backend Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cockpit UI mock-like conversation behavior with a real projection of task protocol files and control commands.

**Architecture:** Keep the Flask-free, server-rendered cockpit. Treat the web UI as a projection of `tasks/*` protocol state, not as a separate agent/workflow engine. GUI input writes the same `control.jsonl` append channel that Feishu follow-ups and Codex task prompts already consume.

**Tech Stack:** Python stdlib HTTP server, server-rendered HTML, `bridge.task_index`, `bridge.task_control`, `tasks/<task_id>/{request.md,status.json,artifacts.json,control.jsonl}`.

---

### Task 1: Remove Success Flash From Conversation Actions

**Files:**
- Modify: `bridge/task_console_web.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

```python
assert handle_console_action(tasks_root, {"action": "append", "task_id": "task-1", "text": "补充"}) == ""
```

- [x] **Step 2: Run test to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected before implementation: FAIL because append returns `已为任务 task-1 追加指令`.

- [x] **Step 3: Write minimal implementation**

In `handle_console_action(... action == "append")`, return `""` after writing the control command.

- [x] **Step 4: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected after implementation: PASS.

### Task 2: Preserve GUI Message Provenance

**Files:**
- Modify: `bridge/task_console_web.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

```python
assert commands[0]["payload"]["source"] == "gui"
assert commands[0]["payload"]["kind"] == "operator_followup"
```

- [x] **Step 2: Run test to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected before implementation: FAIL because payload only contains `text`.

- [x] **Step 3: Write minimal implementation**

Append payload:

```python
{
    "source": "gui",
    "kind": "operator_followup",
    "text": _required(form, "text"),
}
```

- [x] **Step 4: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected after implementation: PASS.

### Task 3: Use Real Request Text For User Bubble

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

Create `tasks/task-1/request.md` with:

```markdown
session_key: feishu:oc_group
chat_id: oc_group
sender_id: ou_user

## User Message
请根据项目群整理第二阶段材料，并生成 PPT 大纲。
```

Assert the rendered HTML includes that text.

- [x] **Step 2: Run test to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected before implementation: FAIL because the user bubble uses `artifacts.summary` fallback.

- [x] **Step 3: Write minimal implementation**

Add `_task_request_message()` and `_user_bubbles_html()` in `bridge/cockpit_console_html.py`, reading `request.md -> ## User Message`.

- [x] **Step 4: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected after implementation: PASS.

### Task 4: Render GUI Follow-Ups As Conversation Bubbles

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

Use `control.jsonl` with an `append_instruction` command and assert the text appears in the central message area.

- [x] **Step 2: Run test to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected before implementation: FAIL because follow-up controls only appear in the right-side timeline.

- [x] **Step 3: Write minimal implementation**

Add `_append_instruction_texts()` and append those texts to `_user_bubbles_html()`.

- [x] **Step 4: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected after implementation: PASS.

### Task 5: Replace Static Assistant Copy With State-Derived Copy

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

Assert the previous fixed sentence `收到，正在为你梳理并生成相关材料` is absent for a completed task, and assert a completed-state message appears.

- [x] **Step 2: Run test to verify it fails**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected before implementation: FAIL because the fixed sentence is always rendered.

- [x] **Step 3: Write minimal implementation**

Add `_assistant_status_message(t)` based on `status.state` and `artifact_outputs`.

- [x] **Step 4: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

Expected after implementation: PASS.

### Task 6: Complete Search Semantics

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

Add a task with `session_title="预算材料整理"` and assert `render_console_html(..., search_query="预算")` includes it.

- [x] **Step 2: Implement**

Extend `_filter_tasks()` haystack to include:

```python
t.session_title
t.chat_name
t.chat_id
artifact labels and values
```

- [x] **Step 3: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

### Task 7: Remove Clickable Fake Controls

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write the failing test**

Assert the rendered cockpit does not include `href="#"`.

- [x] **Step 2: Implement**

Replace plugin/automation/help/settings fake links with disabled buttons or real links to docs where available.

- [x] **Step 3: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

### Task 8: Productize Remaining Operator Copy

**Files:**
- Modify: `bridge/cockpit_console_html.py`
- Test: `tests/test_task_console_web.py`

- [x] **Step 1: Write tests**

Assert product mode does not contain `MVP` or `demo` in visible cockpit HTML.

- [x] **Step 2: Implement**

Replace visible development language with user-facing language. Keep development hints only in CLI output or docs.

- [x] **Step 3: Verify**

Run: `rtk .venv/bin/python -m pytest tests/test_task_console_web.py -q`

### Task 9: Full Verification And Commit

**Files:**
- Modify: `docs/2026-05-04-frontend-mock-audit.md`
- Modify: `docs/superpowers/plans/2026-05-04-cockpit-real-backend-semantics.md`
- Modify: code/test files changed above

- [ ] **Step 1: Run full verification**

```bash
rtk .venv/bin/python -m pytest -q
rtk .venv/bin/python -m py_compile bridge/*.py scripts/*.py
rtk git diff --check
```

- [ ] **Step 2: Restart cockpit service**

```bash
rtk bash -lc 'old=$(cat logs/services/task_console_web.pid 2>/dev/null || true); if [ -n "$old" ]; then kill "$old" 2>/dev/null || true; fi; setsid .venv/bin/python scripts/task_console_web.py --host 127.0.0.1 --port 8765 --ensure-demo --ipv4-only > logs/services/task_console_web.log 2>&1 < /dev/null & echo $! > logs/services/task_console_web.pid'
```

- [ ] **Step 3: Commit and push**

```bash
rtk git add bridge/cockpit_console_html.py bridge/task_console_web.py tests/test_task_console_web.py docs/2026-05-04-frontend-mock-audit.md docs/superpowers/plans/2026-05-04-cockpit-real-backend-semantics.md
rtk git commit -m "fix: connect cockpit conversation to task protocol"
rtk git push origin main
```

## Self-Review

- Spec coverage: central conversation, flash behavior, append provenance, top title rename, and full mock audit are covered. Search, fake controls, and product copy remain explicit next tasks.
- Placeholder scan: no `TBD` or vague implementation placeholders; incomplete tasks include exact tests and code targets.
- Type consistency: functions use existing `TaskSummary`, `Path`, `control.jsonl`, and `request.md` concepts already present in the codebase.
