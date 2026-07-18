"""Render reconciliation results as Markdown + CSV.

All output is built from sorted, deterministic iteration order so that
running the same inputs twice produces byte-identical files.
"""
from __future__ import annotations

from typing import List

from recon.match import MatchResult
from recon.tolerance import (
    Deviation,
    STATUS_BORDERLINE,
    STATUS_MATERIAL_MATCH,
    STATUS_MATERIAL_MISMATCH,
    STATUS_NO_DATA,
    STATUS_OUT_OF_TOL,
    STATUS_UNIT_MISMATCH,
    STATUS_WITHIN,
    evaluate,
)
from recon.util import fmt_num, write_csv

MATCH_FIELDS = [
    "item_id", "location", "description", "category", "status",
    "expected", "actual", "unit", "tol_plus", "tol_minus", "delta",
]

DEVIATION_FIELDS = MATCH_FIELDS + ["note"]


def build_deviations(match_result: MatchResult) -> List[Deviation]:
    """Evaluate every matched pair; also synthesize Deviation rows for
    missing / extra / ambiguous plan-actual pairings so they show up in
    one unified list."""
    deviations: List[Deviation] = []

    for plan, actual in sorted(match_result.matched, key=lambda pa: pa[0].item_id):
        deviations.append(evaluate(plan, actual))

    for plan in sorted(match_result.missing, key=lambda p: p.item_id):
        deviations.append(Deviation(
            item_id=plan.item_id, location=plan.location, description=plan.description,
            category=plan.category, status="missing",
            expected=plan.expected_value if plan.category != "material" else plan.expected_material,
            unit=plan.unit, tol_plus=plan.tol_plus, tol_minus=plan.tol_minus,
            note="plan item has no corresponding actual record",
        ))

    for actual in sorted(match_result.extra, key=lambda a: a.source_row):
        deviations.append(Deviation(
            item_id=actual.item_id or "(none)", location=actual.location, description="",
            category="", status="extra",
            actual=actual.measured_value if actual.measured_value is not None else actual.material,
            unit=actual.unit,
            note="actual record has no corresponding plan item",
        ))

    for plan, candidates in sorted(match_result.ambiguous, key=lambda pc: pc[0].item_id):
        deviations.append(Deviation(
            item_id=plan.item_id, location=plan.location, description=plan.description,
            category=plan.category, status="ambiguous",
            expected=plan.expected_value if plan.category != "material" else plan.expected_material,
            unit=plan.unit, tol_plus=plan.tol_plus, tol_minus=plan.tol_minus,
            note=(
                f"{len(candidates)} actual records match this plan item "
                f"(source rows {[c.source_row for c in candidates]}); needs human review"
            ),
        ))

    return deviations


def _row(d: Deviation) -> dict:
    return {
        "item_id": d.item_id,
        "location": d.location,
        "description": d.description,
        "category": d.category,
        "status": d.status,
        "expected": fmt_num(d.expected) if isinstance(d.expected, (int, float)) else (d.expected or ""),
        "actual": fmt_num(d.actual) if isinstance(d.actual, (int, float)) else (d.actual or ""),
        "unit": d.unit or "",
        "tol_plus": fmt_num(d.tol_plus),
        "tol_minus": fmt_num(d.tol_minus),
        "delta": fmt_num(d.delta),
        "note": d.note,
    }


def write_matches_csv(path: str, deviations: List[Deviation]) -> None:
    write_csv(path, MATCH_FIELDS, [_row(d) for d in deviations])


def write_deviations_csv(path: str, deviations: List[Deviation]) -> None:
    non_clean = [d for d in deviations if d.status not in (STATUS_WITHIN, STATUS_MATERIAL_MATCH)]
    write_csv(path, DEVIATION_FIELDS, [_row(d) for d in non_clean])


_STATUS_LABEL = {
    STATUS_WITHIN: "Within tolerance",
    STATUS_BORDERLINE: "Borderline (within tolerance, near limit)",
    STATUS_OUT_OF_TOL: "OUT OF TOLERANCE",
    STATUS_MATERIAL_MATCH: "Material match",
    STATUS_MATERIAL_MISMATCH: "MATERIAL MISMATCH",
    STATUS_UNIT_MISMATCH: "UNIT MISMATCH",
    STATUS_NO_DATA: "No data recorded",
    "missing": "MISSING (in plan, not in actual)",
    "extra": "EXTRA (in actual, not in plan)",
    "ambiguous": "AMBIGUOUS (multiple actual records)",
}


def build_markdown_report(deviations: List[Deviation], plan_count: int, actual_count: int) -> str:
    counts = {}
    for d in deviations:
        counts[d.status] = counts.get(d.status, 0) + 1

    lines = []
    lines.append("# Plan vs Actual Reconciliation Report")
    lines.append("")
    lines.append(
        "This report reconciles a structured plan/spec against a structured "
        "inspection/actual log. It does not read drawings or images; see "
        "README.md Limitations."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Plan items: {plan_count}")
    lines.append(f"- Actual records: {actual_count}")
    for status in sorted(counts):
        lines.append(f"- {_STATUS_LABEL.get(status, status)}: {counts[status]}")
    lines.append("")

    lines.append("## Item-by-item status")
    lines.append("")
    lines.append("| item_id | location | category | status | expected | actual | unit | delta |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for d in deviations:
        expected = fmt_num(d.expected) if isinstance(d.expected, (int, float)) else (d.expected or "")
        actual = fmt_num(d.actual) if isinstance(d.actual, (int, float)) else (d.actual or "")
        delta = fmt_num(d.delta)
        lines.append(
            f"| {d.item_id} | {d.location} | {d.category} | {_STATUS_LABEL.get(d.status, d.status)} "
            f"| {expected} | {actual} | {d.unit or ''} | {delta} |"
        )
    lines.append("")

    deviating = [d for d in deviations if d.status not in (STATUS_WITHIN, STATUS_MATERIAL_MATCH)]
    lines.append("## Deviations requiring attention")
    lines.append("")
    if not deviating:
        lines.append("None. All plan items matched within tolerance.")
    else:
        lines.append("| item_id | location | status | expected | actual | tol_plus | tol_minus | delta | note |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for d in deviating:
            expected = fmt_num(d.expected) if isinstance(d.expected, (int, float)) else (d.expected or "")
            actual = fmt_num(d.actual) if isinstance(d.actual, (int, float)) else (d.actual or "")
            lines.append(
                f"| {d.item_id} | {d.location} | {_STATUS_LABEL.get(d.status, d.status)} | {expected} | {actual} "
                f"| {fmt_num(d.tol_plus)} | {fmt_num(d.tol_minus)} | {fmt_num(d.delta)} | {d.note} |"
            )
    lines.append("")

    return "\n".join(lines) + "\n"
