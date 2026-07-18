"""Generate a deterministic synthetic plan + actual pair with planted
reconciliation cases.

No randomness is used (no `random` module, no seeds to manage) -- the
data is simply hand-authored below, so re-running this script always
produces byte-identical plan.json / actual.json files.

Planted cases (by plan item_id):
  P-001  dimension  exact match             (delta = 0)
  P-002  dimension  out-of-tolerance        (delta > tol)
  P-003  dimension  borderline              (delta just under tol)
  P-004  dimension  MISSING                 (no actual record at all)
  P-005  material   material mismatch       (oak planned, laminate actual)
  P-006  material   material match          (steel == steel)
  P-007  dimension  unit conversion         (plan mm, actual cm, within tol)
  P-008  count      exact count match       (4 == 4)
  P-009  dimension  AMBIGUOUS               (two actual records, one plan item)
  (actual only) A-999  EXTRA               (no plan item claims it)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recon.util import write_json  # noqa: E402

PLAN = [
    {
        "item_id": "P-001", "location": "Room-101-DoorA", "description": "Door width",
        "category": "dimension", "expected_value": 900.0, "unit": "mm",
        "tol_plus": 5.0, "tol_minus": 5.0,
    },
    {
        "item_id": "P-002", "location": "Room-101-WallN", "description": "Wall height",
        "category": "dimension", "expected_value": 2400.0, "unit": "mm",
        "tol_plus": 10.0, "tol_minus": 10.0,
    },
    {
        "item_id": "P-003", "location": "Room-102-WindowA", "description": "Window width",
        "category": "dimension", "expected_value": 1200.0, "unit": "mm",
        "tol_plus": 8.0, "tol_minus": 8.0,
    },
    {
        "item_id": "P-004", "location": "Room-102-BeamA", "description": "Beam length",
        "category": "dimension", "expected_value": 3000.0, "unit": "mm",
        "tol_plus": 15.0, "tol_minus": 15.0,
    },
    {
        "item_id": "P-005", "location": "Room-103-Floor", "description": "Floor finish material",
        "category": "material", "expected_material": "oak",
    },
    {
        "item_id": "P-006", "location": "Room-103-DoorB", "description": "Door material",
        "category": "material", "expected_material": "steel",
    },
    {
        "item_id": "P-007", "location": "Room-104-PanelA", "description": "Panel width",
        "category": "dimension", "expected_value": 500.0, "unit": "mm",
        "tol_plus": 5.0, "tol_minus": 5.0,
    },
    {
        "item_id": "P-008", "location": "Room-104-Fixtures", "description": "Light fixture count",
        "category": "count", "expected_value": 4, "unit": "count",
        "tol_plus": 0.0, "tol_minus": 0.0,
    },
    {
        "item_id": "P-009", "location": "Room-105-ColumnA", "description": "Column diameter",
        "category": "dimension", "expected_value": 800.0, "unit": "mm",
        "tol_plus": 5.0, "tol_minus": 5.0,
    },
]

ACTUAL = [
    {
        "item_id": "P-001", "location": "Room-101-DoorA",
        "measured_value": 900.0, "unit": "mm", "notes": "exact match",
    },
    {
        "item_id": "P-002", "location": "Room-101-WallN",
        "measured_value": 2415.0, "unit": "mm", "notes": "15mm over tolerance",
    },
    {
        "item_id": "P-003", "location": "Room-102-WindowA",
        "measured_value": 1207.5, "unit": "mm", "notes": "close to tolerance edge",
    },
    # P-004 (Beam length) intentionally has NO actual record -> "missing".
    {
        "item_id": "P-005", "location": "Room-103-Floor",
        "material": "laminate", "notes": "spec called for oak",
    },
    {
        "item_id": "P-006", "location": "Room-103-DoorB",
        "material": "steel", "notes": "matches spec",
    },
    {
        "item_id": "P-007", "location": "Room-104-PanelA",
        "measured_value": 50.2, "unit": "cm", "notes": "recorded in cm, plan is mm",
    },
    {
        "item_id": "P-008", "location": "Room-104-Fixtures",
        "measured_value": 4, "unit": "count", "notes": "counted on site",
    },
    # P-009 (Column diameter) has TWO actual records -> "ambiguous".
    {
        "item_id": "P-009", "location": "Room-105-ColumnA",
        "measured_value": 799.0, "unit": "mm", "notes": "first reading",
    },
    {
        "item_id": "P-009", "location": "Room-105-ColumnA",
        "measured_value": 803.0, "unit": "mm", "notes": "second, conflicting reading",
    },
    # A-999 is not in the plan at all -> "extra".
    {
        "item_id": "A-999", "location": "Room-106-Shelf",
        "measured_value": 450.0, "unit": "mm", "notes": "found on site, not in plan",
    },
]


def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    write_json(os.path.join(out_dir, "plan.json"), PLAN)
    write_json(os.path.join(out_dir, "actual.json"), ACTUAL)
    print(f"Wrote {len(PLAN)} plan items and {len(ACTUAL)} actual records to {out_dir}")


if __name__ == "__main__":
    main()
