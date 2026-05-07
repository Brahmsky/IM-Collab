from __future__ import annotations

import json
from pathlib import Path

from bridge.lark_slides import build_create_slides_args, create_slides_from_markdown, create_slides_from_path, create_slides_from_xml, markdown_to_slide_xml


def test_markdown_to_slide_xml_extracts_up_to_ten_slides(tmp_path: Path) -> None:
    slides_md = tmp_path / "slides.md"
    slides_md.write_text(
        "# Deck\n\n## Slide 1: Cover\nIntro\n\n## Slide 2: Plan\n- A\n- B\n",
        encoding="utf-8",
    )

    slides = markdown_to_slide_xml(slides_md)

    assert len(slides) == 2
    assert 'xmlns="http://www.larkoffice.com/sml/2.0"' in slides[0]
    assert "Slide 1: Cover" in slides[0]
    assert "Intro" in slides[0]


def test_build_create_slides_args_passes_json_array() -> None:
    args = build_create_slides_args(["<slide/>"], title="Demo Deck", dry_run=True)

    assert args[:6] == ["lark-cli", "slides", "+create", "--as", "user", "--title"]
    assert args[6] == "Demo Deck"
    assert args[7] == "--slides"
    assert json.loads(args[8]) == ["<slide/>"]
    assert args[-1] == "--dry-run"


def test_create_slides_from_markdown_runs_cli_and_extracts_json(tmp_path: Path) -> None:
    slides_md = tmp_path / "slides.md"
    slides_md.write_text("# Deck\n\n## Slide 1: Cover\nIntro\n", encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/slides/v1/presentations"}]})

    result = create_slides_from_markdown(slides_md, title="Demo Deck", dry_run=True, runner=fake_run)

    assert seen_args[-1] == "--dry-run"
    assert result["ok"] is True
    assert result["response"]["api"][0]["url"] == "/open-apis/slides/v1/presentations"


def test_create_slides_from_xml_passes_xml_verbatim() -> None:
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/slides/v1/presentations"}]})

    slides = ['<slide xmlns="http://www.larkoffice.com/sml/2.0"><data/></slide>']
    result = create_slides_from_xml(slides, title="XML Deck", dry_run=True, runner=fake_run)

    assert json.loads(seen_args[seen_args.index("--slides") + 1]) == slides
    assert result["response"]["api"][0]["url"] == "/open-apis/slides/v1/presentations"


def test_create_slides_from_path_supports_slides_xml_json_file(tmp_path: Path) -> None:
    slides_path = tmp_path / "deck.json"
    slides = ['<slide xmlns="http://www.larkoffice.com/sml/2.0"><data/></slide>']
    slides_path.write_text(json.dumps(slides), encoding="utf-8")
    seen_args: list[str] = []

    def fake_run(args: list[str]) -> str:
        seen_args.extend(args)
        return "=== Dry Run ===\n" + json.dumps({"api": [{"url": "/open-apis/slides/v1/presentations"}]})

    result = create_slides_from_path(slides_path, title="XML Deck", input_format="slides_xml", dry_run=True, runner=fake_run)

    assert json.loads(seen_args[seen_args.index("--slides") + 1]) == slides
    assert result["response"]["api"][0]["url"] == "/open-apis/slides/v1/presentations"
