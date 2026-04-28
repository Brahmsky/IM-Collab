---
name: group-briefing
description: Use when an IM-Collab task needs to turn group chat records into a source-grounded brief with message-level citations, side annotations, conflicts, and open questions before generating documents, slides, or whiteboards.
---

# Group Briefing

Create a source-grounded brief from group chat records. Do not write the final office document here; produce an evidence layer that downstream document, slides, and whiteboard generation can use.

## Hard Rules

- Every claim must cite one or more original `message_id` values.
- Do not invent missing requirements. If the chat does not say it, put it in `open_questions` or omit it.
- If messages conflict, output a `conflict` annotation. Do not silently merge or choose a winner.
- Teacher, owner, or manager messages may be marked as `authority_note`, but they still need citations.
- Attachments may be cited as files, images, or links. Do not infer attachment contents unless the chat text describes them.
- Preserve ambiguous or unresolved items as `open_question`.

## Workflow

1. Read the formatted group chat record.
2. Normalize each message into `message_id`, `sender`, `sent_at`, `content`, and `attachments`.
3. Create side annotations for task-relevant facts:
   - `task_goal`
   - `deadline`
   - `submission_method`
   - `document_requirement`
   - `slides_requirement`
   - `whiteboard_requirement`
   - `assignment`
   - `authority_note`
   - `attachment_reference`
   - `conflict`
   - `open_question`
4. Build a summary section only from the annotations.
5. Write both:
   - `brief.json` for machine use.
   - `brief.md` for human review.

## Output Contract

Use `references/schema.md` for the exact JSON shape. Use `references/examples.md` when you need a compact model of the side-annotation style.
