from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_score_group_briefing_evidence_reports_expected_item_recall(tmp_path: Path) -> None:
    expected_path = tmp_path / "expected.json"
    evidence_path = tmp_path / "evidence.json"
    expected_path.write_text(
        json.dumps(
            {
                "scenario_id": "demo",
                "facts": [
                    {"kind": "deadline", "summary": "4 月 30 日截止", "source_message_ids": ["om_1"]},
                    {"kind": "assignment", "summary": "李飞负责汇总", "source_message_ids": ["om_2"]},
                ],
                "conflicts": [
                    {"kind": "budget_conflict", "summary": "预算口径冲突", "source_message_ids": ["om_3"]}
                ],
                "open_questions": [
                    {"kind": "invoice", "summary": "发票抬头待确认", "source_message_ids": ["om_4"]}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            {
                "evidence": [
                    {"kind": "deadline", "claim": "4 月 30 日截止", "source_message_ids": ["om_1"]},
                    {"kind": "conflict", "claim": "预算口径冲突", "source_message_ids": ["om_3"]},
                    {"kind": "attachment_reference", "claim": "无关附件", "source_message_ids": ["om_9"]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "score.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/score_group_briefing_evidence.py",
            "--expected",
            str(expected_path),
            "--evidence",
            str(evidence_path),
            "--output",
            str(output_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert "matched=2/4" in result.stdout
    score = json.loads(output_path.read_text(encoding="utf-8"))
    assert score["expected_total"] == 4
    assert score["matched_total"] == 2
    assert score["recall"] == 0.5
    assert score["items"][0]["matched"] is True
    assert score["items"][1]["matched"] is False


def test_score_group_briefing_evidence_allows_aggregate_evidence_for_one_expected_item(tmp_path: Path) -> None:
    expected_path = tmp_path / "expected.json"
    evidence_path = tmp_path / "evidence.json"
    expected_path.write_text(
        json.dumps(
            {
                "scenario_id": "demo",
                "facts": [
                    {
                        "kind": "assignment",
                        "summary": "周岚负责预算表，余舟负责申请书，林澈负责PPT",
                        "source_message_ids": ["om_1", "om_2", "om_3"],
                    }
                ],
                "conflicts": [],
                "open_questions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            {
                "evidence": [
                    {"kind": "assignment", "claim": "周岚负责预算表", "source_message_ids": ["om_1"]},
                    {"kind": "assignment", "claim": "余舟负责申请书", "source_message_ids": ["om_2"]},
                    {"kind": "assignment", "claim": "林澈负责PPT", "source_message_ids": ["om_3"]},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "score.json"

    subprocess.run(
        [
            sys.executable,
            "scripts/score_group_briefing_evidence.py",
            "--expected",
            str(expected_path),
            "--evidence",
            str(evidence_path),
            "--output",
            str(output_path),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    score = json.loads(output_path.read_text(encoding="utf-8"))
    assert score["matched_total"] == 1
    assert score["items"][0]["matched"] is True
    assert score["items"][0]["reason"].startswith("aggregate:")
