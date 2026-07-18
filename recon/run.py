"""Orchestrate: ingest -> match -> evaluate -> report.

Usage:
    python3 -m recon.run --plan data/plan.json --actual data/actual.json --out sample_output
"""
from __future__ import annotations

import argparse
import os

from recon.ingest import load_actual, load_plan
from recon.match import match_items
from recon.report import build_deviations, build_markdown_report, write_deviations_csv, write_matches_csv
from recon.tolerance import (
    STATUS_BORDERLINE,
    STATUS_MATERIAL_MATCH,
    STATUS_MATERIAL_MISMATCH,
    STATUS_NO_DATA,
    STATUS_OUT_OF_TOL,
    STATUS_UNIT_MISMATCH,
    STATUS_WITHIN,
)


def run(plan_path: str, actual_path: str, out_dir: str) -> dict:
    plan_items = load_plan(plan_path)
    actual_records = load_actual(actual_path)

    match_result = match_items(plan_items, actual_records)
    deviations = build_deviations(match_result)

    os.makedirs(out_dir, exist_ok=True)

    report_md = build_markdown_report(deviations, len(plan_items), len(actual_records))
    with open(os.path.join(out_dir, "reconciliation_report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report_md)

    write_matches_csv(os.path.join(out_dir, "matches.csv"), deviations)
    write_deviations_csv(os.path.join(out_dir, "deviations.csv"), deviations)

    counts = {}
    for d in deviations:
        counts[d.status] = counts.get(d.status, 0) + 1

    summary_lines = [
        "Plan vs Actual Reconciliation - run summary",
        f"plan_items={len(plan_items)}",
        f"actual_records={len(actual_records)}",
        f"matched={len(match_result.matched)}",
        f"missing={len(match_result.missing)}",
        f"extra={len(match_result.extra)}",
        f"ambiguous={len(match_result.ambiguous)}",
    ]
    for status in sorted(counts):
        summary_lines.append(f"status.{status}={counts[status]}")
    summary_text = "\n".join(summary_lines) + "\n"
    with open(os.path.join(out_dir, "run_summary.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(summary_text)

    return {
        "plan_items": len(plan_items),
        "actual_records": len(actual_records),
        "matched": len(match_result.matched),
        "missing": len(match_result.missing),
        "extra": len(match_result.extra),
        "ambiguous": len(match_result.ambiguous),
        "counts": counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Path to plan/spec file (.json or .csv)")
    parser.add_argument("--actual", required=True, help="Path to actual/inspection log file (.json or .csv)")
    parser.add_argument("--out", required=True, help="Output directory for the reconciliation report")
    args = parser.parse_args()
    result = run(args.plan, args.actual, args.out)
    print(f"Reconciliation complete: {result}")


if __name__ == "__main__":
    main()
