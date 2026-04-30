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

The long-context scenario includes `long_context_hook` metadata. It is not used by the current default path, which still selects the latest window, but it gives future context selectors stable signals to test against.
