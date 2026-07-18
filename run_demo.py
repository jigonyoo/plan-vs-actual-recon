#!/usr/bin/env python3
"""Generate synthetic plan/actual data and run the reconciliation demo.

Writes sample_output/{reconciliation_report.md, matches.csv,
deviations.csv, run_summary.txt}.

Safe to re-run: this script only ever creates the output directory
with os.makedirs(exist_ok=True) and overwrites individual files. It
never deletes the output directory or any file within it.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.generate_plan_actual import main as generate_data  # noqa: E402
from recon.run import run  # noqa: E402


def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "data")
    out_dir = os.path.join(base, "sample_output")

    os.makedirs(out_dir, exist_ok=True)

    generate_data()

    plan_path = os.path.join(data_dir, "plan.json")
    actual_path = os.path.join(data_dir, "actual.json")

    result = run(plan_path, actual_path, out_dir)
    print("Demo reconciliation complete.")
    print(result)
    print(f"Output written to: {out_dir}")


if __name__ == "__main__":
    main()
