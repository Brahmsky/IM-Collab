from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_extract_group_briefing_evidence_script_can_render_source_without_api(tmp_path: Path) -> None:
    output_path = tmp_path / "source.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/extract_group_briefing_evidence.py",
            "--context-fixture",
            "examples/scenarios/group_briefing/course_project_conflict/context.json",
            "--output",
            str(output_path),
            "--render-source",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert "source_messages=16" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "[om_course_001]" in payload["text"]
    assert payload["spans"][0]["message_id"] == "om_course_001"


def test_extract_group_briefing_evidence_script_can_render_selected_context(tmp_path: Path) -> None:
    output_path = tmp_path / "selected-source.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/extract_group_briefing_evidence.py",
            "--context-fixture",
            "examples/scenarios/group_briefing/grant_application_ultra_long_context/context.json",
            "--output",
            str(output_path),
            "--render-source",
            "--select-context",
            "--max-context-messages",
            "45",
            "--recent-tail",
            "12",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert "source_messages=29" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "[om_grant_001]" not in payload["text"]
    assert "[om_grant_008]" in payload["text"]
    assert "[om_grant_064]" in payload["text"]
    assert "[om_grant_071]" in payload["text"]
