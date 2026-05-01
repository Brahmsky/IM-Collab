# Group Briefing Scenarios

These fixtures use the backend group-chat message format consumed by `bridge.group_context`.

Use them directly with the event consumer:

```bash
rtk .venv/bin/python scripts/run_event_consumer.py \
  --event-dir events/im \
  --dispatch golembot \
  --publish \
  --execute \
  --context-fixture examples/scenarios/group_briefing/course_project_conflict/context.json
```

## Scenarios

- `course_project_conflict`: medium-size course project discussion with a formal notice, later corrections, file/image attachments, assignments, and deadline ambiguity.
- `client_launch_review_long_context`: longer client launch retrospective context with stale metrics, corrections, client-sensitive wording, noise, attachments, and a final bot request.
- `grant_application_ultra_long_context`: 71-message project funding application workflow across more than one week, with research office notices, adviser guidance, finance/budget versions, partner proof letters, seven final electronic files, PPT versions, paper signature timing, and several conflicts.

The long-context scenario includes `long_context_hook` metadata. It is not used by the current default path, which still selects the latest window, but it gives future context selectors stable signals to test against.

## Evidence Evaluation

Scenarios with `expected_brief.json` can be scored against LangExtract/DeepSeek evidence:

```bash
rtk .venv/bin/python scripts/extract_group_briefing_evidence.py \
  --context-fixture examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json \
  --output /tmp/im-collab-grant-evidence.json

rtk .venv/bin/python scripts/score_group_briefing_evidence.py \
  --expected examples/scenarios/group_briefing/grant_application_ultra_long_context/expected_brief.json \
  --evidence /tmp/im-collab-grant-evidence.json \
  --output /tmp/im-collab-grant-score.json
```

Observed DeepSeek V4 Flash results on 2026-05-01:

- `extraction_passes=1`: 40 evidence items, matched 8/16 oracle items, recall 0.50.
- `extraction_passes=2`: 46 evidence items, matched 9/16 oracle items, recall 0.56.
- `--select-context --max-context-messages 45 --recent-tail 12`: 21 evidence items, matched 7/16, recall 0.44.
- `--select-context --max-context-messages 60 --recent-tail 16`: 50 evidence items, matched 13/16, recall 0.81.

The 60-message selector result is the current best setting. It keeps the prompt smaller than full history while preserving formal notices, corrections, final files, attachments, and recent messages.
