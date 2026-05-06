from __future__ import annotations

import importlib
from typing import Any

DEFAULT_MODEL_ID = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://api.deepseek.com"
EXTRACTOR_NAME = "langextract-deepseek-v4-pro-high"

SUPPORTED_KINDS = {
    "deadline",
    "submission_method",
    "document_requirement",
    "slides_requirement",
    "whiteboard_requirement",
    "assignment",
    "conflict",
    "open_question",
    "attachment_reference",
}


def build_source_text(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    lines: list[str] = []
    spans: list[dict[str, Any]] = []
    cursor = 0
    for index, message in enumerate(messages, start=1):
        message_id = str(message.get("message_id") or message.get("id") or f"msg_{index:03d}")
        sender = str(message.get("sender") or message.get("sender_id") or "unknown")
        sent_at = str(message.get("sent_at") or "")
        content = str(message.get("content") or "")
        attachments = _attachment_text(message.get("attachments"))
        line = f"[{message_id}] {sender}"
        if sent_at:
            line += f" {sent_at}"
        line += f": {content}"
        if attachments:
            line += f" {attachments}"
        start = cursor
        lines.append(line)
        cursor += len(line) + 1
        spans.append({"message_id": message_id, "start": start, "end": cursor - 1, "text": line})
    return "\n".join(lines), spans


def convert_annotated_document_to_evidence(
    annotated_document: Any,
    message_spans: list[dict[str, Any]],
    source_text: str | None = None,
    extractor_name: str = EXTRACTOR_NAME,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for extraction in getattr(annotated_document, "extractions", []) or []:
        interval = getattr(extraction, "char_interval", None)
        if interval is None:
            continue
        kind = str(getattr(extraction, "extraction_class", ""))
        if kind not in SUPPORTED_KINDS:
            continue
        extraction_text = str(getattr(extraction, "extraction_text", ""))
        message_ids = _message_ids_for_exact_text(extraction_text, message_spans)
        if not message_ids:
            interval = _prefer_exact_source_interval(extraction_text, interval, source_text)
            message_ids = _message_ids_for_interval(interval, message_spans)
        if not message_ids:
            continue
        attributes = getattr(extraction, "attributes", None)
        if not isinstance(attributes, dict):
            attributes = {}
        evidence.append(
            {
                "kind": kind,
                "claim": str(attributes.get("claim") or extraction_text),
                "source_text": extraction_text,
                "source_message_ids": message_ids,
                "confidence": str(attributes.get("confidence") or "medium"),
                "extractor": extractor_name,
            }
        )
    return evidence


def extract_evidence(
    messages: list[dict[str, Any]],
    *,
    langextract_module: Any | None = None,
    api_key: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
    model_id: str = DEFAULT_MODEL_ID,
    max_char_buffer: int = 3000,
    extraction_passes: int = 1,
) -> list[dict[str, Any]]:
    lx = langextract_module or _load_langextract()
    source_text, message_spans = build_source_text(messages)
    config = lx.factory.ModelConfig(
        model_id=model_id,
        provider="OpenAILanguageModel",
        provider_kwargs={
            "api_key": api_key,
            "base_url": base_url,
            "reasoning_effort": "high",
            "temperature": 0.0,
            "timeout": 60,
        },
    )
    extract_kwargs = _prompt_validation_kwargs(lx)
    annotated_document = lx.extract(
        text_or_documents=source_text,
        prompt_description=_prompt_description(),
        examples=_examples(lx),
        config=config,
        use_schema_constraints=True,
        max_char_buffer=max_char_buffer,
        extraction_passes=extraction_passes,
        show_progress=False,
        resolver_params={"suppress_parse_errors": True},
        **extract_kwargs,
    )
    return convert_annotated_document_to_evidence(annotated_document, message_spans, source_text=source_text)


def _message_ids_for_interval(interval: Any, message_spans: list[dict[str, Any]]) -> list[str]:
    start = getattr(interval, "start_pos", None)
    end = getattr(interval, "end_pos", None)
    if start is None or end is None:
        return []
    matches = [
        str(span["message_id"])
        for span in message_spans
        if int(span["start"]) < int(end) and int(start) < int(span["end"])
    ]
    return list(dict.fromkeys(matches))


def _message_ids_for_exact_text(extraction_text: str, message_spans: list[dict[str, Any]]) -> list[str]:
    if not extraction_text:
        return []
    return [
        str(span["message_id"])
        for span in message_spans
        if extraction_text in str(span.get("text") or "")
    ]


def _prefer_exact_source_interval(extraction_text: str, interval: Any, source_text: str | None) -> Any:
    if not source_text or not extraction_text:
        return interval
    starts: list[int] = []
    cursor = source_text.find(extraction_text)
    while cursor >= 0:
        starts.append(cursor)
        cursor = source_text.find(extraction_text, cursor + 1)
    if not starts:
        return interval
    original_start = getattr(interval, "start_pos", None)
    original_end = getattr(interval, "end_pos", None)
    original_mid = (
        (int(original_start) + int(original_end)) / 2
        if original_start is not None and original_end is not None
        else starts[0]
    )
    best_start = min(starts, key=lambda start: abs((start + len(extraction_text) / 2) - original_mid))
    return _CharInterval(best_start, best_start + len(extraction_text))


class _CharInterval:
    def __init__(self, start_pos: int, end_pos: int) -> None:
        self.start_pos = start_pos
        self.end_pos = end_pos


def _attachment_text(attachments: Any) -> str:
    if not isinstance(attachments, list) or not attachments:
        return ""
    parts = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        name = attachment.get("name") or attachment.get("url") or attachment.get("file_key") or attachment.get("image_key")
        attachment_type = attachment.get("type") or "attachment"
        parts.append(f"[附件:{attachment_type}:{name or 'unnamed'}]")
    return " ".join(parts)


def _load_langextract() -> Any:
    try:
        return importlib.import_module("langextract")
    except ImportError as exc:
        raise RuntimeError(
            "LangExtract extractor is optional. Install it with `pip install 'langextract[openai]'` "
            "before using the DeepSeek evidence extractor."
        ) from exc


def _prompt_validation_kwargs(lx: Any) -> dict[str, Any]:
    prompt_validation = getattr(lx, "prompt_validation", None)
    if prompt_validation is None:
        return {}
    level = getattr(getattr(prompt_validation, "PromptValidationLevel", None), "OFF", None)
    if level is None:
        return {}
    return {"prompt_validation_level": level}


def _prompt_description() -> str:
    return """Extract source-grounded group-chat evidence for an office assistant.

Only extract information explicitly supported by the source text. Use exact source text spans.
Do not upgrade a teammate's interpretation into a teacher/client requirement. Keep the speaker and authority level clear in the claim.
Classes:
- deadline
- submission_method
- document_requirement
- slides_requirement
- whiteboard_requirement
- assignment
- conflict
- open_question
- attachment_reference

For each extraction, add attributes:
- claim: concise Chinese claim grounded in the extracted text
- confidence: high, medium, or low

Do not infer missing project names, owners, or deadlines. If information is missing, extract an open_question only when the source text itself shows uncertainty.
"""


def _examples(lx: Any) -> list[Any]:
    return [
        lx.data.ExampleData(
            text=(
                "[om_1] 老师: 4 月 30 日 18:00 前在课程平台提交 PDF 文档。\n"
                "[om_2] 同学: PPT 原来 10 页，但老师更正为 6-8 页。"
            ),
            extractions=[
                lx.data.Extraction(
                    extraction_class="deadline",
                    extraction_text="4 月 30 日 18:00 前在课程平台提交 PDF 文档",
                    attributes={"claim": "正式提交截止为 4 月 30 日 18:00", "confidence": "high"},
                ),
                lx.data.Extraction(
                    extraction_class="submission_method",
                    extraction_text="4 月 30 日 18:00 前在课程平台提交 PDF 文档",
                    attributes={"claim": "提交方式为课程平台", "confidence": "high"},
                ),
                lx.data.Extraction(
                    extraction_class="document_requirement",
                    extraction_text="4 月 30 日 18:00 前在课程平台提交 PDF 文档",
                    attributes={"claim": "文档需要以 PDF 形式提交", "confidence": "high"},
                ),
                lx.data.Extraction(
                    extraction_class="conflict",
                    extraction_text="PPT 原来 10 页，但老师更正为 6-8 页",
                    attributes={"claim": "PPT 页数要求出现更正，应保留冲突证据", "confidence": "high"},
                ),
            ],
        )
    ]
