# Group Briefing Schema

`brief.json` must be a JSON object:

```json
{
  "chat_id": "oc_xxx",
  "source_messages": [
    {
      "message_id": "om_001",
      "sender": "张老师",
      "sent_at": "2026-04-28T10:15:00+08:00",
      "content": "PPT 不超过 8 页，周五 18:00 前提交。",
      "attachments": [
        {"type": "file", "name": "模板.pptx", "url": "https://..."}
      ]
    }
  ],
  "annotations": [
    {
      "annotation_id": "ann_001",
      "type": "deadline",
      "claim": "提交截止时间为周五 18:00 前。",
      "evidence_message_ids": ["om_001"],
      "confidence": "high",
      "needs_confirmation": false
    }
  ],
  "summary": {
    "source_message_count": 1,
    "annotation_count": 1,
    "task_goal": [],
    "deadlines": [],
    "deliverables": [],
    "format_requirements": [],
    "assignments": [],
    "risks": [],
    "open_questions": []
  }
}
```

Required invariant: every `annotations[].evidence_message_ids` entry must point to an existing `source_messages[].message_id`.

Audit fields:

- `annotations[].confidence`: confidence label for the extraction. Current heuristic extraction uses `high` for direct matches and `medium` for questions/conflicts that need confirmation.
- `summary.source_message_count`: number of normalized source messages used to build the brief.
- `summary.annotation_count`: number of generated side annotations.
