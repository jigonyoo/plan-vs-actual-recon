"""Match actual (inspection) records to plan (spec) items.

Matching key preference:
  1. item_id, if both plan item and actual record carry one and they
     are equal.
  2. location, as a fallback.

Outcomes per plan item:
  - matched:   exactly one actual record found for that plan item.
  - missing:   zero actual records found.
  - ambiguous: two or more actual records map to the same plan item.
               These are surfaced for human review, never silently
               auto-matched to "the first one" or "the closest one".

Any actual record that isn't consumed by a matched or ambiguous group
is reported as "extra" (present in the log, not called for by the plan).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple

from recon.ingest import ActualRecord, PlanItem


@dataclass
class MatchResult:
    matched: List[Tuple[PlanItem, ActualRecord]] = field(default_factory=list)
    missing: List[PlanItem] = field(default_factory=list)
    extra: List[ActualRecord] = field(default_factory=list)
    ambiguous: List[Tuple[PlanItem, List[ActualRecord]]] = field(default_factory=list)


def match_items(plan_items: List[PlanItem], actual_records: List[ActualRecord]) -> MatchResult:
    by_id = defaultdict(list)
    by_location = defaultdict(list)
    for rec in actual_records:
        if rec.item_id:
            by_id[rec.item_id].append(rec)
        by_location[rec.location].append(rec)

    result = MatchResult()
    consumed = set()  # id() of ActualRecord objects already accounted for

    # Sort plan items by item_id for deterministic processing order.
    for plan in sorted(plan_items, key=lambda p: p.item_id):
        candidates = list(by_id.get(plan.item_id, []))
        if not candidates:
            candidates = list(by_location.get(plan.location, []))

        if len(candidates) == 0:
            result.missing.append(plan)
        elif len(candidates) == 1:
            result.matched.append((plan, candidates[0]))
            consumed.add(id(candidates[0]))
        else:
            # Deterministic ordering of ambiguous candidates.
            candidates_sorted = sorted(candidates, key=lambda r: r.source_row)
            result.ambiguous.append((plan, candidates_sorted))
            for c in candidates_sorted:
                consumed.add(id(c))

    extra = [rec for rec in actual_records if id(rec) not in consumed]
    extra.sort(key=lambda r: r.source_row)
    result.extra = extra
    return result
