"""Evaluate a matched (plan_item, actual_record) pair: is the recorded
actual value within the plan's specified expected value +/- tolerance?

This module trusts the numbers it is given. It does not measure
anything itself and does not know whether the measurement was taken
correctly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from recon.ingest import ActualRecord, PlanItem
from recon.util import UnitError, convert, fmt_num, norm_category

# Once a value uses this fraction (or more) of its available tolerance,
# it is flagged "borderline" even though it is still technically within
# spec -- a signal to a human reviewer that it's a close call.
BORDERLINE_FRACTION = 0.9

STATUS_WITHIN = "within"
STATUS_BORDERLINE = "borderline"
STATUS_OUT_OF_TOL = "out_of_tol"
STATUS_MATERIAL_MATCH = "material_match"
STATUS_MATERIAL_MISMATCH = "material_mismatch"
STATUS_UNIT_MISMATCH = "unit_mismatch"
STATUS_NO_DATA = "no_data"


@dataclass
class Deviation:
    item_id: str
    location: str
    description: str
    category: str
    status: str
    expected: Optional[object] = None
    actual: Optional[object] = None
    unit: Optional[str] = None
    tol_plus: Optional[float] = None
    tol_minus: Optional[float] = None
    delta: Optional[float] = None
    note: str = ""


def _evaluate_dimension(plan: PlanItem, actual: ActualRecord) -> Deviation:
    if actual.measured_value is None:
        return Deviation(
            item_id=plan.item_id, location=plan.location, description=plan.description,
            category=plan.category, status=STATUS_NO_DATA,
            expected=plan.expected_value, unit=plan.unit,
            tol_plus=plan.tol_plus, tol_minus=plan.tol_minus,
            note="actual record has no measured_value",
        )

    tol_plus = plan.tol_plus if plan.tol_plus is not None else 0.0
    tol_minus = plan.tol_minus if plan.tol_minus is not None else 0.0

    try:
        actual_value = convert(actual.measured_value, actual.unit, plan.unit)
    except UnitError as exc:
        return Deviation(
            item_id=plan.item_id, location=plan.location, description=plan.description,
            category=plan.category, status=STATUS_UNIT_MISMATCH,
            expected=plan.expected_value, actual=actual.measured_value,
            unit=plan.unit, tol_plus=tol_plus, tol_minus=tol_minus,
            note=str(exc),
        )

    delta = actual_value - plan.expected_value
    tol = tol_plus if delta >= 0 else tol_minus
    tol = tol if tol is not None else 0.0

    if abs(delta) > tol:
        status = STATUS_OUT_OF_TOL
    else:
        ratio = (abs(delta) / tol) if tol > 0 else (0.0 if delta == 0 else float("inf"))
        status = STATUS_BORDERLINE if ratio >= BORDERLINE_FRACTION else STATUS_WITHIN

    return Deviation(
        item_id=plan.item_id, location=plan.location, description=plan.description,
        category=plan.category, status=status,
        expected=plan.expected_value, actual=actual_value, unit=plan.unit,
        tol_plus=tol_plus, tol_minus=tol_minus, delta=delta,
    )


def _evaluate_material(plan: PlanItem, actual: ActualRecord) -> Deviation:
    if actual.material is None:
        return Deviation(
            item_id=plan.item_id, location=plan.location, description=plan.description,
            category=plan.category, status=STATUS_NO_DATA,
            expected=plan.expected_material,
            note="actual record has no material recorded",
        )
    match = norm_category(plan.expected_material) == norm_category(actual.material)
    status = STATUS_MATERIAL_MATCH if match else STATUS_MATERIAL_MISMATCH
    return Deviation(
        item_id=plan.item_id, location=plan.location, description=plan.description,
        category=plan.category, status=status,
        expected=plan.expected_material, actual=actual.material,
    )


def evaluate(plan: PlanItem, actual: ActualRecord) -> Deviation:
    """Evaluate one matched pair; category-aware dispatch."""
    if plan.category in ("dimension", "count"):
        return _evaluate_dimension(plan, actual)
    if plan.category == "material":
        return _evaluate_material(plan, actual)
    raise ValueError(f"unknown plan category {plan.category!r}")


def is_deviation_status(status: str) -> bool:
    """True for any status that is NOT a clean match."""
    return status not in (STATUS_WITHIN, STATUS_MATERIAL_MATCH)
