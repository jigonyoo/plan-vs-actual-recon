# Plan vs Actual Reconciliation Report

This report reconciles a structured plan/spec against a structured inspection/actual log. It does not read drawings or images; see README.md Limitations.

## Summary

- Plan items: 9
- Actual records: 10
- AMBIGUOUS (multiple actual records): 1
- Borderline (within tolerance, near limit): 1
- EXTRA (in actual, not in plan): 1
- Material match: 1
- MATERIAL MISMATCH: 1
- MISSING (in plan, not in actual): 1
- OUT OF TOLERANCE: 1
- Within tolerance: 3

## Item-by-item status

| item_id | location | category | status | expected | actual | unit | delta |
|---|---|---|---|---|---|---|---|
| P-001 | Room-101-DoorA | dimension | Within tolerance | 900 | 900 | mm | 0 |
| P-002 | Room-101-WallN | dimension | OUT OF TOLERANCE | 2400 | 2415 | mm | 15 |
| P-003 | Room-102-WindowA | dimension | Borderline (within tolerance, near limit) | 1200 | 1207.5 | mm | 7.5 |
| P-005 | Room-103-Floor | material | MATERIAL MISMATCH | oak | laminate |  |  |
| P-006 | Room-103-DoorB | material | Material match | steel | steel |  |  |
| P-007 | Room-104-PanelA | dimension | Within tolerance | 500 | 502 | mm | 2 |
| P-008 | Room-104-Fixtures | count | Within tolerance | 4 | 4 | count | 0 |
| P-004 | Room-102-BeamA | dimension | MISSING (in plan, not in actual) | 3000 |  | mm |  |
| A-999 | Room-106-Shelf |  | EXTRA (in actual, not in plan) |  | 450 | mm |  |
| P-009 | Room-105-ColumnA | dimension | AMBIGUOUS (multiple actual records) | 800 |  | mm |  |

## Deviations requiring attention

| item_id | location | status | expected | actual | tol_plus | tol_minus | delta | note |
|---|---|---|---|---|---|---|---|---|
| P-002 | Room-101-WallN | OUT OF TOLERANCE | 2400 | 2415 | 10 | 10 | 15 |  |
| P-003 | Room-102-WindowA | Borderline (within tolerance, near limit) | 1200 | 1207.5 | 8 | 8 | 7.5 |  |
| P-005 | Room-103-Floor | MATERIAL MISMATCH | oak | laminate |  |  |  |  |
| P-004 | Room-102-BeamA | MISSING (in plan, not in actual) | 3000 |  | 15 | 15 |  | plan item has no corresponding actual record |
| A-999 | Room-106-Shelf | EXTRA (in actual, not in plan) |  | 450 |  |  |  | actual record has no corresponding plan item |
| P-009 | Room-105-ColumnA | AMBIGUOUS (multiple actual records) | 800 |  | 5 | 5 |  | 2 actual records match this plan item (source rows [7, 8]); needs human review |

