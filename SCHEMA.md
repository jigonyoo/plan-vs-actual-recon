# Schema

Both the plan/spec file and the actual/inspection-log file are either a
JSON array of flat objects, or a CSV file with a header row. File
extension (`.json` / `.csv`) determines which parser is used.

## Plan / spec record

| Field              | Required | Type   | Notes |
|--------------------|----------|--------|-------|
| `item_id`          | yes      | string | Unique across the plan file. |
| `location`         | yes      | string | Used as a fallback match key when `item_id` is absent on the actual side. |
| `description`      | no       | string | Free text. |
| `category`          | yes      | string | One of `dimension`, `material`, `count`. |
| `expected_value`   | for `dimension`/`count` | number | The specified value. |
| `unit`             | for `dimension`/`count` | string | One of `mm`, `cm`, `m`, `in`, `ft`, or `count`. |
| `tol_plus`         | for `dimension`/`count` | number | Allowed positive deviation (in `unit`). Defaults to 0 if omitted. |
| `tol_minus`        | for `dimension`/`count` | number | Allowed negative deviation (in `unit`). Defaults to 0 if omitted. |
| `expected_material`| for `material` | string | Compared case-insensitively. |

`category="count"` is handled identically to `dimension` numerically
(expected value +/- tolerance), it's just a semantic label for counts
of items rather than a physical dimension.

## Actual / inspection-log record

| Field            | Required | Type   | Notes |
|------------------|----------|--------|-------|
| `location`       | yes      | string | Match key fallback. |
| `item_id`        | no       | string | Preferred match key when present. |
| `measured_value` | no       | number | Required for `dimension`/`count` items to be evaluated. |
| `unit`           | no       | string | Unit the `measured_value` was recorded in; converted to the plan's unit before comparison. |
| `material`       | no       | string | Required for `material` items to be evaluated. |
| `notes`          | no       | string | Free text, carried through to reports for context only. |

## Matching rules

1. If both a plan item and one or more actual records share the same
   non-empty `item_id`, they are candidates.
2. Otherwise, plan item `location` is matched against actual record
   `location`.
3. Zero candidates -> plan item is **missing**.
4. Exactly one candidate -> **matched** pair, evaluated by `tolerance.py`.
5. Two or more candidates -> **ambiguous**; none of them are
   auto-matched. All candidates are listed in the report for a human
   to resolve.
6. Any actual record not consumed by a matched or ambiguous group is
   reported as **extra**.

## Tolerance / deviation status values

| Status              | Meaning |
|---------------------|---------|
| `within`            | `abs(actual - expected) <= tolerance`, and not close to the edge. |
| `borderline`        | Within tolerance, but using >= 90% of the available tolerance band. |
| `out_of_tol`        | `abs(actual - expected) > tolerance`. |
| `material_match`    | Actual material equals expected material (case/space-insensitive). |
| `material_mismatch` | Actual material differs from expected material. |
| `unit_mismatch`     | Actual unit could not be converted to the plan's unit. |
| `no_data`           | Matched, but the actual record has no usable value/material recorded. |
| `missing`           | Plan item has no actual record at all. |
| `extra`             | Actual record has no corresponding plan item. |
| `ambiguous`         | Multiple actual records map to one plan item; unresolved. |

## Units understood

Length only: `mm`, `cm`, `m`, `in`, `ft`. `count` is treated as a
dimensionless unit that must match itself exactly (no conversion). Any
other unit string, or a unit not present in the plan/actual pair's
matching family, produces `unit_mismatch` rather than a guessed value.
