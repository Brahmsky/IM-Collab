# Codex Superpowers Local MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local smoke-testable Agent Pilot workspace using Codex + superpowers as the only orchestration layer.

**Architecture:** Python owns the bridge/file protocol only. Codex + superpowers owns planning and execution. The first implementation uses deterministic local output to validate the protocol before binding real Feishu, Presenton, or Gateway services.

**Tech Stack:** Python 3.11+, pytest, JSON file protocol, Markdown project skills.

---

### Task 1: Project Instructions And Skills

**Files:**
- Create: `AGENTS.md`
- Create: `skills/feishu-office/SKILL.md`
- Create: `skills/presenton-slides/SKILL.md`
- Create: `skills/delivery-archive/SKILL.md`

- [ ] Write concise project instructions that require `rtk` for shell commands and Codex + superpowers as the only orchestration layer.
- [ ] Write project-local office skills as thin routing layers over Feishu CLI skills, lark-openapi-mcp, and Presenton.
- [ ] Verify skill metadata has `name` and `description`.

### Task 2: Task Protocol Tests

**Files:**
- Create: `tests/test_task_protocol.py`

- [ ] Write failing tests for task creation, status transition, and artifact validation.
- [ ] Run `python -m pytest tests/test_task_protocol.py -q` and confirm it fails because implementation is missing.

### Task 3: Task Protocol Implementation

**Files:**
- Create: `bridge/__init__.py`
- Create: `bridge/task_protocol.py`

- [ ] Implement `create_task`, `write_status`, `read_status`, `write_artifacts`, and `read_artifacts`.
- [ ] Run `python -m pytest tests/test_task_protocol.py -q` and confirm it passes.

### Task 4: Local Smoke Runner Tests

**Files:**
- Create: `tests/test_local_codex_smoke.py`

- [ ] Write failing tests that run the local smoke agent against a demo request and assert completed artifacts.
- [ ] Run `python -m pytest tests/test_local_codex_smoke.py -q` and confirm it fails because implementation is missing.

### Task 5: Local Smoke Runner

**Files:**
- Create: `bridge/local_codex_smoke.py`
- Create: `examples/demo_request.md`
- Create: `scripts/smoke_demo.py`

- [ ] Implement deterministic artifact generation for the local MVP.
- [ ] Run `python -m pytest tests/test_local_codex_smoke.py -q` and confirm it passes.
- [ ] Run `python scripts/smoke_demo.py` and confirm it writes a completed task.

### Task 6: Full Verification

**Files:**
- Modify only if verification exposes a defect.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python scripts/smoke_demo.py`.
- [ ] Inspect `tasks/demo-local-smoke/artifacts.json`.

### Task 7: Existing Tool Integration Scaffold

**Files:**
- Create: `bridge/external_tools.py`
- Create: `bridge/codex_runner.py`
- Create: `bridge/tool_check.py`
- Create: `scripts/check_tools.py`
- Create: `docs/references/existing-office-wheels.md`
- Test: `tests/test_external_tools.py`
- Test: `tests/test_codex_runner.py`
- Test: `tests/test_tool_check.py`

- [ ] Write failing tests for external tool catalog, Codex prompt construction, and tool availability checks.
- [ ] Implement minimal modules.
- [ ] Install Feishu CLI and its bundled skills.
- [ ] Run `python scripts/check_tools.py`.
- [ ] Run `lark-cli doctor` and record whether auth/config remains pending.
