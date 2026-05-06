# Codex-Direct Feishu Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Codex directly execute Feishu office operations through `lark-cli`/real tool surfaces, with the task directory acting as protocol and audit storage instead of a mandatory local markdown staging area.

**Architecture:** Keep `request.md` / `status.json` / `artifacts.json` as the stable boundary, but shift the default generator and delivery contract to remote-first semantics. Remove legacy local-smoke defaults, make Feishu delivery remote-aware, and align both frontend trigger surfaces to the same real backend behavior.

**Tech Stack:** Python 3.11, Codex app-server, `lark-cli`, Feishu task protocol files, server-rendered cockpit, Flask API.

---

## File Map

- Modify: `bridge/codex_task_runner.py`
- Modify: `bridge/feishu_delivery.py`
- Modify: `bridge/golembot_office_loop.py`
- Modify: `bridge/server_app.py`
- Modify: `bridge/task_console_web.py`
- Modify: `scripts/task_console_web.py`
- Create: `scripts/create_feishu_whiteboard.py`
- Delete: `bridge/codex_runner.py`
- Delete: `bridge/local_codex_smoke.py`
- Delete: `scripts/smoke_demo.py`
- Modify: `scripts/process_feishu_event.py`
- Modify: `tests/test_codex_task_runner.py`
- Modify: `tests/test_feishu_delivery.py`
- Modify: `tests/test_golembot_office_loop.py`
- Modify: `tests/test_task_console_web.py`
- Modify: `tests/test_task_console_web_script.py`

### Task 1: Redesign Codex Execution Contract

**Files:**
- Modify: `bridge/codex_task_runner.py`
- Modify: `tests/test_codex_task_runner.py`

- [ ] Step 1: Replace prompt language so it explicitly instructs Codex to prefer real Feishu execution paths and remote-first artifacts.
- [ ] Step 2: Update tests to assert the new prompt semantics: remote execution allowed, `artifacts.json` can carry `remote`-first items, no requirement that a local markdown file must exist first.
- [ ] Step 3: Keep output validation compatible with both local `path` items and remote-only `remote` items.
- [ ] Step 4: Verify with a focused Python assertion script against `build_codex_task_prompt()` and `run_codex_task()` contract expectations.

### Task 2: Make Feishu Delivery Remote-Aware

**Files:**
- Modify: `bridge/feishu_delivery.py`
- Modify: `tests/test_feishu_delivery.py`

- [ ] Step 1: Add helper logic that detects `remote.provider=feishu` items and skips duplicate creation when the remote object already exists.
- [ ] Step 2: Allow the document/slides/whiteboard branches to reuse existing `remote` metadata instead of requiring a local publish source every time.
- [ ] Step 3: Add compatibility behavior so local `path` items still publish correctly when Codex did not create the remote object directly.
- [ ] Step 4: Add tests covering three cases: remote-only reuse, mixed local+remote compatibility, and whiteboard continuation with an existing document remote.
- [ ] Step 5: Run a focused Python verification script against `publish_task_artifacts_to_feishu()` with fake runners.

### Task 3: Shift Main Loop Defaults Off Local Smoke

**Files:**
- Modify: `bridge/golembot_office_loop.py`
- Modify: `scripts/process_feishu_event.py`
- Modify: `tests/test_golembot_office_loop.py`

- [ ] Step 1: Change main-path default generator selection from `local` to `app-server` or `codex`, keeping `local` only as explicit smoke/debug fallback.
- [ ] Step 2: Remove assumptions in the office loop that successful task generation means local markdown artifacts were created first.
- [ ] Step 3: Update tests that currently assert `local` defaults so they now assert the remote-first default execution mode.
- [ ] Step 4: Verify with focused test/fixture scripts or direct Python assertions that new tasks choose the new default generator and still preserve `waiting_for_user` / follow-up semantics.

### Task 4: Remove Legacy Local-Smoke Main-Path Code

**Files:**
- Delete: `bridge/codex_runner.py`
- Delete: `bridge/local_codex_smoke.py`
- Delete: `scripts/smoke_demo.py`
- Modify: tests or references that still import them

- [ ] Step 1: Find remaining imports and references to the legacy local-smoke modules.
- [ ] Step 2: Remove the deleted modules and rewrite or delete dependent tests and references so the repo no longer treats them as part of the main architecture.
- [ ] Step 3: Ensure any still-needed demo behavior is either removed or explicitly marked legacy/non-main-path elsewhere, not through these deleted modules.
- [ ] Step 4: Run a repo-wide search to confirm the removed files are no longer referenced from the main execution path.

### Task 5: Add Direct Whiteboard Script Surface

**Files:**
- Create: `scripts/create_feishu_whiteboard.py`
- Possibly modify: `bridge/lark_whiteboard.py`
- Add/modify tests near `tests/test_lark_whiteboard.py`

- [ ] Step 1: Create a script wrapper for whiteboard creation/update that mirrors the existing `create_feishu_doc.py` and `create_feishu_slides.py` entry surfaces.
- [ ] Step 2: Support the two-step whiteboard flow cleanly: append/create board context, then update from Mermaid/DSL input.
- [ ] Step 3: Add tests or direct invocation coverage so this whiteboard path is callable by Codex just like doc/slides scripts.
- [ ] Step 4: Verify the script help/argument flow using a direct shell invocation.

### Task 6: Align Frontend Trigger Semantics

**Files:**
- Modify: `bridge/server_app.py`
- Modify: `bridge/task_console_web.py`
- Modify: `scripts/task_console_web.py`
- Modify: `tests/test_task_console_web.py`
- Modify: `tests/test_task_console_web_script.py`

- [ ] Step 1: Make append/retry/follow-up actions trigger the same real backend semantics in both server-rendered cockpit and Flask API paths.
- [ ] Step 2: Remove `_noop_retry`-style placeholder behavior from the SPA/API path so it no longer diverges from the cockpit path.
- [ ] Step 3: Keep chat transcript semantics stable while the execution behavior becomes real and unified.
- [ ] Step 4: Update tests so both frontends assert actual trigger behavior instead of “writes control only”.
- [ ] Step 5: Verify with a focused Python or HTTP harness script that append from each surface results in the same backend action and stream contract.

### Task 7: Final Regression Sweep

**Files:**
- Modify as needed from earlier tasks

- [ ] Step 1: Run targeted verification scripts for prompt, delivery, office-loop default generator, and frontend trigger semantics.
- [ ] Step 2: Run any available repository test commands that exist in this environment; if `pytest` is unavailable, use Python assertion harnesses and state that explicitly.
- [ ] Step 3: Re-read the design spec and confirm each success criterion maps to a completed code change.
- [ ] Step 4: Summarize residual risks, especially any remaining `lark-cli` expression-layer sharp edges in Docs/Slides/Whiteboard.
