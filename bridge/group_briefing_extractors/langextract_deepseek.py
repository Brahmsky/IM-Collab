from __future__ import annotations

import importlib
from typing import Any

DEFAULT_MODEL_ID = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
EXTRACTOR_NAME = "langextract-deepseek-v4-flash"

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
        spans.append({"message_id": message_id, "start": start, "end": cursor - 1})
    return "\n".join(lines), spans


def convert_annotated_document_to_evidence(
    annotated_document: Any,
    message_spans: list[dict[str, Any]],
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
        message_ids = _message_ids_for_interval(interval, message_spans)
        if not message_ids:
            continue
        attributes = getattr(extraction, "attributes", None)
        if not isinstance(attributes, dict):
            attributes = {}
        source_text = str(getattr(extraction, "extraction_text", ""))
        evidence.append(
            {
                "kind": kind,
                "claim": str(attributes.get("claim") or source_text),
                "source_text": source_text,
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
            "temperature": 0.0,
        },
    )
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
    )
    return convert_annotated_document_to_evidence(annotated_document, message_spans)


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


def _prompt_description() -> str:
    return """Extract source-grounded group-chat evidence for an office assistant.

Only extract information explicitly supported by the source text. Use exact source text spans.
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
                    extraction_text="在课程平台提交",
                    attributes={"claim": "提交方式为课程平台", "confidence": "high"},
                ),
                lx.data.Extraction(
                    extraction_class="document_requirement",
                    extraction_text="PDF 文档",
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
