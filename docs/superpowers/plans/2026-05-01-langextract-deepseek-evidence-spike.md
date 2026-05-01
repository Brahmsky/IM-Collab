# LangExtract DeepSeek Evidence Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small optional evidence extraction stage that can use LangExtract with DeepSeek V4 Flash without changing the default IM-Collab runtime path.

**Architecture:** Standard backend group-chat messages remain the input contract. `bridge.group_briefing_extractors.langextract_deepseek` renders messages into source text, calls LangExtract through an OpenAI-compatible DeepSeek config, maps char intervals back to message IDs, and returns project-owned evidence JSON. `build_group_brief_from_evidence()` converts that evidence into the existing `brief.json` shape when explicitly requested.

**Tech Stack:** Python, optional `langextract[openai]`, DeepSeek OpenAI-compatible Chat Completions, existing IM-Collab fixtures and pytest.

---

### Task 1: Optional Extractor Boundary

**Files:**
- Create: `bridge/group_briefing_extractors/langextract_deepseek.py`
- Create: `bridge/group_briefing_extractors/__init__.py`
- Test: `tests/test_langextract_deepseek.py`

- [x] Write failing tests for source text rendering, char interval mapping, DeepSeek OpenAI-provider configuration, and fixture rendering.
- [x] Implement `build_source_text()`, `convert_annotated_document_to_evidence()`, and `extract_evidence()`.
- [x] Keep `langextract` import lazy so default test and runtime paths do not require the optional dependency.

### Task 2: Development Script

**Files:**
- Create: `scripts/extract_group_briefing_evidence.py`
- Test: `tests/test_extract_group_briefing_evidence_script.py`

- [x] Add `--render-source` mode for no-key local inspection.
- [x] Add real extraction mode using `DEEPSEEK_API_KEY`, `deepseek-v4-flash`, and `https://api.deepseek.com`.
- [x] Write JSON output that can be inspected before wiring into production.

### Task 3: Briefing Integration Point

**Files:**
- Modify: `bridge/group_briefing.py`
- Test: `tests/test_group_briefing.py`

- [x] Add `build_group_brief_from_evidence()` as an explicit replacement path.
- [x] Do not merge external evidence with rule-based annotations by default.
- [x] Preserve existing `brief.json` validation, summaries, and confirmation behavior.

### Task 4: Documentation and Dependency Boundary

**Files:**
- Create: `requirements-langextract.txt`
- Modify: `README.md`

- [x] Document optional dependency installation.
- [x] Document source rendering and real extraction commands.
- [x] State that LangExtract does not replace Codex, app-server, task protocol, or Feishu delivery.
