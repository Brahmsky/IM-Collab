from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Score extracted evidence against an expected group-briefing oracle.")
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    evidence_payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    score = score_evidence(expected, evidence_payload.get("evidence", []))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"matched={score['matched_total']}/{score['expected_total']} recall={score['recall']:.2f} output={args.output}")
    return 0


def score_evidence(expected: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    expected_items = _expected_items(expected)
    scored_items = [_score_expected_item(item, evidence_items) for item in expected_items]
    matched_total = sum(1 for item in scored_items if item["matched"])
    expected_total = len(scored_items)
    return {
        "scenario_id": expected.get("scenario_id", ""),
        "expected_total": expected_total,
        "matched_total": matched_total,
        "recall": round(matched_total / expected_total, 4) if expected_total else 0.0,
        "by_section": _section_scores(scored_items),
        "items": scored_items,
    }


def _expected_items(expected: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for section in ("facts", "conflicts", "open_questions"):
        for item in expected.get(section, []):
            items.append(
                {
                    "section": section,
                    "kind": str(item.get("kind", "")),
                    "summary": str(item.get("summary", "")),
                    "source_message_ids": [str(message_id) for message_id in item.get("source_message_ids", [])],
                }
            )
    return items


def _score_expected_item(expected_item: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [_match_score(expected_item, evidence) for evidence in evidence_items]
    best = max(candidates, key=lambda item: item["score"], default={"score": 0.0, "evidence": None, "reason": "no_evidence"})
    aggregate = _aggregate_match_score(expected_item, evidence_items)
    if aggregate["score"] > best["score"]:
        best = aggregate
    matched = best["score"] >= 0.5
    return {
        **expected_item,
        "matched": matched,
        "score": best["score"],
        "matched_evidence": best["evidence"],
        "reason": best["reason"],
    }


def _aggregate_match_score(expected_item: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    compatible = [
        evidence
        for evidence in evidence_items
        if _kind_matches(expected_item["section"], expected_item["kind"], str(evidence.get("kind", ""))) > 0
    ]
    if not compatible:
        return {"score": 0.0, "evidence": None, "reason": "aggregate:no_compatible_evidence"}
    expected_ids = set(expected_item["source_message_ids"])
    covered_ids: set[str] = set()
    claims: list[str] = []
    kinds: set[str] = set()
    for evidence in compatible:
        covered_ids |= {str(message_id) for message_id in evidence.get("source_message_ids", [])}
        claims.append(str(evidence.get("claim", "")))
        kinds.add(str(evidence.get("kind", "")))
    id_overlap = len(expected_ids & covered_ids) / len(expected_ids) if expected_ids else 0.0
    summary_terms = _content_terms(expected_item["summary"])
    term_overlap = len(summary_terms & _content_terms(" ".join(claims))) / len(summary_terms) if summary_terms else 0.0
    score = 0.75 * id_overlap + 0.25 * term_overlap
    return {
        "score": round(score, 4),
        "evidence": {
            "kind": "+".join(sorted(kinds)),
            "claim": " | ".join(claim for claim in claims if claim)[:300],
            "source_message_ids": sorted(covered_ids),
        },
        "reason": f"aggregate:id_overlap={id_overlap:.2f},terms={term_overlap:.2f}",
    }


def _match_score(expected_item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    expected_ids = set(expected_item["source_message_ids"])
    evidence_ids = {str(message_id) for message_id in evidence.get("source_message_ids", [])}
    id_overlap = len(expected_ids & evidence_ids) / len(expected_ids) if expected_ids else 0.0
    kind_match = _kind_matches(expected_item["section"], expected_item["kind"], str(evidence.get("kind", "")))
    summary_terms = _content_terms(expected_item["summary"])
    evidence_text = f"{evidence.get('kind', '')} {evidence.get('claim', '')} {evidence.get('source_text', '')}"
    term_overlap = len(summary_terms & _content_terms(evidence_text)) / len(summary_terms) if summary_terms else 0.0
    score = max(
        0.7 * id_overlap + 0.2 * kind_match + 0.1 * term_overlap,
        0.45 * id_overlap + 0.15 * kind_match + 0.4 * term_overlap,
    )
    reason = f"id_overlap={id_overlap:.2f},kind={kind_match:.2f},terms={term_overlap:.2f}"
    return {
        "score": round(score, 4),
        "evidence": {
            "kind": evidence.get("kind", ""),
            "claim": evidence.get("claim", ""),
            "source_message_ids": list(evidence_ids),
        },
        "reason": reason,
    }


def _kind_matches(section: str, expected_kind: str, evidence_kind: str) -> float:
    if expected_kind == evidence_kind:
        return 1.0
    if section == "conflicts" and evidence_kind == "conflict":
        return 1.0
    if section == "open_questions" and evidence_kind == "open_question":
        return 1.0
    aliases = {
        "submission_package": {"submission_method", "document_requirement", "attachment_reference"},
        "final_files": {"attachment_reference", "document_requirement", "slides_requirement"},
        "document_version": {"document_requirement", "attachment_reference"},
        "budget_total": {"document_requirement", "conflict"},
        "budget_rule": {"document_requirement", "open_question"},
        "project_name": {"document_requirement", "conflict"},
    }
    return 0.75 if evidence_kind in aliases.get(expected_kind, set()) else 0.0


def _content_terms(text: str) -> set[str]:
    terms = set()
    for token in [
        "截止",
        "预算",
        "28000",
        "29000",
        "30000",
        "申请书",
        "预算表",
        "预算说明",
        "团队成员",
        "导师",
        "合作",
        "PPT",
        "签字",
        "纸质",
        "电子",
        "社区服务智能助手",
        "4 月 28 日",
        "4 月 29 日",
        "20:00",
        "12:00",
        "v0.2",
        "v0.3",
        "v0.4",
    ]:
        if token in text:
            terms.add(token)
    return terms


def _section_scores(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for section in ("facts", "conflicts", "open_questions"):
        section_items = [item for item in items if item["section"] == section]
        matched = sum(1 for item in section_items if item["matched"])
        total = len(section_items)
        result[section] = {"matched": matched, "total": total, "recall": round(matched / total, 4) if total else 0.0}
    return result


if __name__ == "__main__":
    raise SystemExit(main())
