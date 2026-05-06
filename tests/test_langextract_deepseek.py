from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bridge.group_briefing_extractors.langextract_deepseek import (
    DEFAULT_MODEL_ID,
    build_source_text,
    convert_annotated_document_to_evidence,
    extract_evidence,
)
from bridge.group_context import build_standard_group_context


@dataclass
class FakeInterval:
    start_pos: int
    end_pos: int


@dataclass
class FakeExtraction:
    extraction_class: str
    extraction_text: str
    attributes: dict
    char_interval: FakeInterval | None


@dataclass
class FakeDocument:
    extractions: list[FakeExtraction]


class FakeFactory:
    def __init__(self) -> None:
        self.config_kwargs: dict | None = None

    def ModelConfig(self, **kwargs):
        self.config_kwargs = kwargs
        return {"model_config": kwargs}


class FakeLangExtract:
    def __init__(self, document: FakeDocument) -> None:
        self.data = self
        self.factory = FakeFactory()
        self.document = document
        self.extract_kwargs: dict | None = None

    def ExampleData(self, **kwargs):
        return {"example": kwargs}

    def Extraction(self, **kwargs):
        return {"extraction": kwargs}

    def extract(self, **kwargs):
        self.extract_kwargs = kwargs
        return self.document


def test_build_source_text_marks_message_boundaries() -> None:
    text, spans = build_source_text(
        [
            {
                "message_id": "om_1",
                "sender": "老师",
                "sent_at": "2026-04-30T10:00:00+08:00",
                "content": "周五 18:00 前提交文档。",
            },
            {
                "message_id": "om_2",
                "sender": "同学",
                "sent_at": "2026-04-30T10:05:00+08:00",
                "content": "PPT 改成 6-8 页。",
            },
        ]
    )

    assert "[om_1]" in text
    assert "[om_2]" in text
    assert spans[0]["message_id"] == "om_1"
    assert spans[1]["message_id"] == "om_2"
    assert spans[0]["start"] < text.index("周五 18:00")
    assert spans[0]["end"] > text.index("提交文档")


def test_convert_annotated_document_to_evidence_maps_char_interval_to_message_id() -> None:
    text, spans = build_source_text(
        [
            {"message_id": "om_1", "sender": "老师", "content": "周五 18:00 前提交文档。"},
            {"message_id": "om_2", "sender": "同学", "content": "PPT 改成 6-8 页。"},
        ]
    )
    start = text.index("PPT")
    end = text.index("。", start) + 1
    document = FakeDocument(
        [
            FakeExtraction(
                extraction_class="slides_requirement",
                extraction_text="PPT 改成 6-8 页。",
                attributes={"claim": "PPT 页数要求改为 6-8 页", "confidence": "high"},
                char_interval=FakeInterval(start, end),
            ),
            FakeExtraction(
                extraction_class="deadline",
                extraction_text="不存在的示例污染",
                attributes={"claim": "这条不应该进入 evidence"},
                char_interval=None,
            ),
        ]
    )

    evidence = convert_annotated_document_to_evidence(document, spans)

    assert evidence == [
        {
            "kind": "slides_requirement",
            "claim": "PPT 页数要求改为 6-8 页",
            "source_text": "PPT 改成 6-8 页。",
            "source_message_ids": ["om_2"],
            "confidence": "high",
            "extractor": "langextract-deepseek-v4-pro-high",
        }
    ]


def test_convert_annotated_document_prefers_exact_source_text_match_over_fuzzy_interval() -> None:
    text, spans = build_source_text(
        [
            {
                "message_id": "om_1",
                "sender": "同学",
                "content": "我发模板。",
                "attachments": [{"type": "file", "name": "模板.pptx"}],
            },
            {"message_id": "om_2", "sender": "老师", "content": "PPT 控制在 6-8 页即可。"},
        ]
    )
    wrong_start = text.index("PPT 控制")
    wrong_end = text.index("。", wrong_start) + 1
    document = FakeDocument(
        [
            FakeExtraction(
                extraction_class="attachment_reference",
                extraction_text="[附件:file:模板.pptx]",
                attributes={"claim": "同学分享了 PPT 模板附件"},
                char_interval=FakeInterval(wrong_start, wrong_end),
            )
        ]
    )

    evidence = convert_annotated_document_to_evidence(document, spans, source_text=text)

    assert evidence[0]["source_message_ids"] == ["om_1"]


def test_default_deepseek_model_is_v4_pro() -> None:
    assert DEFAULT_MODEL_ID == "deepseek-v4-pro"


def test_extract_evidence_uses_openai_provider_with_deepseek_v4_pro_high_reasoning() -> None:
    document = FakeDocument(
        [
            FakeExtraction(
                extraction_class="deadline",
                extraction_text="4 月 30 日 18:00",
                attributes={"claim": "正式截止为 4 月 30 日 18:00"},
                char_interval=FakeInterval(10, 25),
            )
        ]
    )
    fake_lx = FakeLangExtract(document)

    extract_evidence(
        [{"message_id": "om_1", "sender": "老师", "content": "4 月 30 日 18:00 截止。"}],
        langextract_module=fake_lx,
        api_key="sk-test",
        base_url="https://api.deepseek.com",
    )

    assert fake_lx.factory.config_kwargs == {
        "model_id": "deepseek-v4-pro",
        "provider": "OpenAILanguageModel",
        "provider_kwargs": {
            "api_key": "sk-test",
            "base_url": "https://api.deepseek.com",
            "reasoning_effort": "high",
            "temperature": 0.0,
            "timeout": 60,
        },
    }
    assert fake_lx.extract_kwargs["config"] == {"model_config": fake_lx.factory.config_kwargs}
    assert fake_lx.extract_kwargs["use_schema_constraints"] is True
    assert fake_lx.extract_kwargs["max_char_buffer"] == 3000


def test_course_scenario_can_be_rendered_for_langextract() -> None:
    messages = build_standard_group_context(
        Path("examples/scenarios/group_briefing/course_project_conflict/context.json")
    )

    text, spans = build_source_text(messages)

    assert "om_course_001" in text
    assert "om_course_016" in text
    assert len(spans) == len(messages)
