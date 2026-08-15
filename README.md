# Plan-vs-Actual Reconciliation & Tolerance Check

Reconciles a **plan/spec** (the items that were supposed to be there, with
expected values and tolerances) against an **actual/inspection log** (what
was actually recorded on site), and produces a report of what matched,
what's missing, what's extra, and what's out of tolerance. Records match by
`item_id` first and `location` as a fallback; units are converted before
comparison, a value using 90% or more of its available tolerance is flagged
`borderline` even though it's technically within spec, and a plan item with
more than one matching actual record is flagged `ambiguous` and left for a
human rather than silently resolved. It consumes numbers that someone (or
some other system) already measured and recorded: it does not read drawings,
PDFs, or CAD files, does no computer vision, and measures nothing itself.

This is a portfolio sample for structured-data reconciliation work —
the kind of task that shows up as "does the inspection log match the
spec sheet" across construction punch lists, manufacturing QA,
equipment audits, or fulfillment checks.

## What this is honestly

This is a **structured reconciliation tool**. It consumes two lists of
records that someone (or some other system) has already measured and
recorded, and checks them against each other. That's it.

## What this is NOT

- It does **not** read drawings, PDFs, or CAD files.
- It does **not** do any computer vision or extract dimensions from
  photos or images.
- It does **not** measure anything itself. It trusts the numbers it's
  given in the actual/inspection log.
- It is **not** a substitute for a qualified reviewer resolving
  ambiguous or conflicting records — see Limitations below.

If your real need is "read a drawing and tell me if the built thing
matches it," that requires a drawing-parsing / CAD / CV pipeline this
sample does not attempt. This sample answers a narrower, honest
question: *given a spec and a set of recorded measurements, do they
reconcile?*

## Quick start

```bash
python3 run_demo.py
python3 -m unittest discover -s tests -v
```

`run_demo.py` generates a deterministic synthetic plan + actual pair
(via `data/generate_plan_actual.py`) and writes a reconciliation
report to `sample_output/`:

- `reconciliation_report.md` — human-readable summary + item-by-item
  status + a deviations table.
- `matches.csv` — one row per plan item / actual record outcome.
- `deviations.csv` — only the rows that need attention (missing,
  extra, ambiguous, out-of-tolerance, borderline, mismatched).
- `run_summary.txt` — plain-text counts.

### Run your own data

```bash
python3 -m recon.run --plan your_plan.json --actual your_actual.json --out out_dir
```

Plan and actual files can be `.json` (array of objects) or `.csv`
(header row). See `SCHEMA.md` for the exact fields.

### Docker

```bash
docker compose up --build
```

Runs with `network_mode: none` — no network access, by design.

## How matching and tolerance work

- Actual records are matched to plan items by `item_id` first, falling
  back to `location`.
- If more than one actual record matches a single plan item, that's
  flagged **ambiguous** and left for a human to resolve — it is never
  silently resolved by picking "the first" or "the closest" reading.
- Numeric items (`dimension`, `count`) are checked against
  `expected_value +/- tol_plus/tol_minus`. A value using 90% or more of
  its available tolerance is flagged `borderline` even though it's
  technically within spec.
- Units are converted (mm/cm/m/in/ft) before comparison. An
  unconvertible or unknown unit is flagged `unit_mismatch`, not
  silently coerced or ignored.
- Categorical items (`material`) are compared case/space-insensitively;
  any difference is a `material_mismatch`.

## Determinism

No wall-clock timestamps, random values, or non-deterministic
iteration order appear in any output file. Given the same input files,
`run_demo.py` (and `recon.run.run`) produce byte-identical output on
every run — verified by an md5 comparison test in the test suite.

## Repository layout

```
recon/            core library (ingest, match, tolerance, report, run, util)
data/             deterministic synthetic plan/actual generator
tests/            15+ unittest tests
sample_output/    output of the last `run_demo.py` run
SCHEMA.md         field-level schema for plan/actual files
```

## Limitations

- **Structured input only.** This tool reconciles JSON/CSV records. It
  does not read drawings, PDFs, images, or CAD files, and does not
  perform any computer vision or dimension extraction.
- **Trusts its inputs.** It has no way to know whether a recorded
  `measured_value` or `material` in the actual log is itself correct —
  it only checks whether the recorded value matches the plan within
  tolerance.
- **Ambiguity is surfaced, not resolved.** When more than one actual
  record maps to a single plan item, this tool lists all candidates
  and stops — it does not guess which one is "the real" reading.
  Resolving that is a human decision.
- **Tolerances and units must be specified in the plan.** If a plan
  item omits `tol_plus`/`tol_minus`, they default to 0 (exact match
  required). If a unit can't be converted (not in the mm/cm/m/in/ft
  table, or mismatched families), the item is flagged `unit_mismatch`
  rather than compared.
- **Answers a narrow question.** This tool answers "does the recorded
  actual match the specified plan, within tolerance?" It does not
  answer "is the plan/drawing itself correct?" or "was the
  measurement taken correctly?"
- **No network, no external services.** Everything runs offline,
  stdlib-only, by design — there's no OCR, no LLM extraction, and
  no API calls in this sample.
