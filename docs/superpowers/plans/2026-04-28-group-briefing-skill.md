# Group Briefing Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-grounded group chat briefing layer that produces traceable `brief.json` and `brief.md` before office artifact generation.

**Architecture:** Keep the skill instructions in `skills/group-briefing/`, and put deterministic schema/format helpers in focused Python modules under `bridge/`. The office loop writes the briefing artifacts into each task directory when group context exists, and Codex is instructed to use those artifacts as the evidence layer for document, slides, and whiteboard generation.

**Tech Stack:** Python standard library, local Codex skills, existing task directory protocol, pytest.

---

### Task 1: Skill Scaffold

**Files:**
- Create: `skills/group-briefing/SKILL.md`
- Create: `skills/group-briefing/references/schema.md`
- Create: `skills/group-briefing/references/examples.md`

- [ ] Write the skill with hard rules: no unsupported claims, every annotation has `message_id` evidence, conflicts stay conflicts, uncertain information becomes open questions.
- [ ] Include the JSON shape in `references/schema.md`.
- [ ] Include one compact example in `references/examples.md`.

### Task 2: Briefing Builder

**Files:**
- Create: `bridge/group_briefing.py`
- Test: `tests/test_group_briefing.py`

- [ ] Write failing tests for normalized chat messages, evidence-backed annotations, conflict detection, and Markdown output.
- [ ] Implement minimal deterministic extraction for deadlines, document requirements, slide/PPT requirements, assignments, attachments, conflicts, and open questions.
- [ ] Verify every summary item has message references.

### Task 3: Office Loop Integration

**Files:**
- Modify: `bridge/golembot_office_loop.py`
- Modify: `bridge/codex_task_runner.py`
- Test: `tests/test_golembot_office_loop.py`
- Test: `tests/test_codex_task_runner.py`

- [ ] Write failing tests that group context creates `brief.json` and `brief.md`.
- [ ] Update request generation to mention the briefing artifacts.
- [ ] Update Codex prompt to require using `brief.json` first when present.

### Task 4: Docs and Verification

**Files:**
- Modify: `README.md`

- [ ] Document that office tasks first create a source-grounded group brief.
- [ ] Run full tests.
- [ ] Commit only tracked project files.
