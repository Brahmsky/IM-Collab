# Group Briefing Evidence Evaluation

Date: 2026-05-01

## Purpose

This records the first quantitative evaluation of the optional LangExtract + DeepSeek V4 Flash extractor against source-grounded group-chat oracle files.

The goal is not to prove that the extractor should replace the default `group_briefing` path. The goal is to measure where it helps and where it fails on realistic long-context data.

## Ultra-Long Scenario

`examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json`

- 71 group messages
- 8+ speakers
- 24 attachment references
- More than one week of conversation
- Funding application package with seven final electronic files plus a paper signature page
- Multiple material versions: application document, budget sheet, budget note, team table, adviser recommendation, partner proof letter, slides
- Several conflicts: deadline change, old/new budget template, 29000 vs 28000 budget, project-name mismatch

Oracle:

`examples/scenarios/group_briefing/grant_application_ultra_long_context/expected_brief.json`

- 9 facts
- 4 conflicts
- 3 open questions

## Commands

```bash
rtk .venv/bin/python scripts/extract_group_briefing_evidence.py \
  --context-fixture examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json \
  --output /tmp/im-collab-grant-evidence.json

rtk .venv/bin/python scripts/score_group_briefing_evidence.py \
  --expected examples/scenarios/group_briefing/grant_application_ultra_long_context/expected_brief.json \
  --evidence /tmp/im-collab-grant-evidence.json \
  --output /tmp/im-collab-grant-score.json
```

For two extraction passes:

```bash
rtk .venv/bin/python scripts/extract_group_briefing_evidence.py \
  --context-fixture examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json \
  --output /tmp/im-collab-grant-evidence-pass2.json \
  --extraction-passes 2
```

## Results

| Setting | Evidence Items | Matched Oracle Items | Recall |
| --- | ---: | ---: | ---: |
| `extraction_passes=1` | 40 | 8 / 16 | 0.50 |
| `extraction_passes=2` | 46 | 9 / 16 | 0.56 |

Two passes improved recall slightly but increased latency substantially. This suggests pass count should not be increased blindly.

## Interpretation

DeepSeek V4 Flash through LangExtract is useful for extracting source-grounded facts, deadlines, requirements, assignments, and attachment references.

The weak areas are:

- final-version synthesis across many messages
- multi-message budget evolution
- distinguishing resolved open questions from still-open questions
- recognizing that one oracle item may require several evidence items
- recall on late final-file package lists

The score script now supports aggregate matching, so one expected oracle item can be matched by multiple evidence items. This better reflects how long group-chat briefing works.

## Product Judgment

This is a good evaluation demo:

- The project can generate a realistic long-context fixture.
- It can run a real extractor with DeepSeek V4 Flash.
- It can score evidence against a source-grounded oracle.
- It can show measured limitations instead of hand-waving about quality.

It is not yet enough to make LangExtract the default briefing path. The next useful step is to add a context selector that prioritizes final versions, formal notices, corrections, attachments, and unresolved questions before extraction.
