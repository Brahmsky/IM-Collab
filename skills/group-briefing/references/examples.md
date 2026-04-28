# Example

Input messages:

```json
[
  {"message_id": "om_1", "sender": "张老师", "sent_at": "2026-04-28T10:00:00+08:00", "content": "周五 18:00 前交方案和 PPT。"},
  {"message_id": "om_2", "sender": "李同学", "sent_at": "2026-04-28T10:03:00+08:00", "content": "PPT 先按 8 页做。"},
  {"message_id": "om_3", "sender": "王同学", "sent_at": "2026-04-28T10:05:00+08:00", "content": "我记得老师说 10 页也行？"}
]
```

Annotations:

```json
[
  {
    "annotation_id": "ann_001",
    "type": "deadline",
    "claim": "方案和 PPT 需要在周五 18:00 前提交。",
    "evidence_message_ids": ["om_1"],
    "confidence": "high",
    "needs_confirmation": false
  },
  {
    "annotation_id": "ann_002",
    "type": "conflict",
    "claim": "PPT 页数存在 8 页和 10 页两种说法，需要确认。",
    "evidence_message_ids": ["om_2", "om_3"],
    "confidence": "medium",
    "needs_confirmation": true
  }
]
```
