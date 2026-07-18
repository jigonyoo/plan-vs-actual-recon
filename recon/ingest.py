"""Ingest plan-spec and actual-log records from JSON or CSV, with schema
validation.

This module only ever reads structured records (JSON arrays of objects,
or CSV rows). It never opens a drawing, image, or CAD file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from recon.util import SchemaError, load_csv, load_json, norm_text, to_float

VALID_CATEGORIES = {"dimension", "material", "count"}

_PLAN_REQUIRED = ("item_id", "location", "category")
_ACTUAL_REQUIRED = ("location",)


@dataclass
class PlanItem:
    item_id: str
    location: str
    description: str
    category: str  # "dimension" | "material" | "count"
    expected_value: Optional[float] = None
    unit: Optional[str] = None
    tol_plus: Optional[float] = None
    tol_minus: Optional[float] = None
    expected_material: Optional[str] = None


@dataclass
class ActualRecord:
    location: str
    item_id: Optional[str] = None
    measured_value: Optional[float] = None
    unit: Optional[str] = None
    material: Optional[str] = None
    notes: str = ""
    source_row: int = -1


def _require(d: dict, keys, kind: str, idx: int) -> None:
    for k in keys:
        if k not in d or norm_text(d.get(k)) is None:
            raise SchemaError(f"{kind} record #{idx} missing required field {k!r}: {d!r}")


def _parse_plan_row(row: dict, idx: int) -> PlanItem:
    _require(row, _PLAN_REQUIRED, "plan", idx)
    category = norm_text(row.get("category"))
    if category not in VALID_CATEGORIES:
        raise SchemaError(
            f"plan record #{idx} has invalid category {category!r}; "
            f"expected one of {sorted(VALID_CATEGORIES)}"
        )
    return PlanItem(
        item_id=norm_text(row.get("item_id")),
        location=norm_text(row.get("location")),
        description=norm_text(row.get("description")) or "",
        category=category,
        expected_value=to_float(row.get("expected_value")),
        unit=norm_text(row.get("unit")),
        tol_plus=to_float(row.get("tol_plus")),
        tol_minus=to_float(row.get("tol_minus")),
        expected_material=norm_text(row.get("expected_material")),
    )


def _parse_actual_row(row: dict, idx: int) -> ActualRecord:
    _require(row, _ACTUAL_REQUIRED, "actual", idx)
    return ActualRecord(
        location=norm_text(row.get("location")),
        item_id=norm_text(row.get("item_id")),
        measured_value=to_float(row.get("measured_value")),
        unit=norm_text(row.get("unit")),
        material=norm_text(row.get("material")),
        notes=norm_text(row.get("notes")) or "",
        source_row=idx,
    )


def _load_rows(path: str) -> list:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        data = load_json(path)
        if not isinstance(data, list):
            raise SchemaError(f"{path}: expected a JSON array of records")
        return data
    if ext == ".csv":
        return load_csv(path)
    raise SchemaError(f"{path}: unsupported file extension {ext!r} (use .json or .csv)")


def load_plan(path: str) -> list:
    """Load and validate a plan/spec file. Returns list[PlanItem]."""
    rows = _load_rows(path)
    items = [_parse_plan_row(row, i) for i, row in enumerate(rows)]
    ids = [p.item_id for p in items]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SchemaError(f"plan has duplicate item_id(s): {sorted(dupes)}")
    return items


def load_actual(path: str) -> list:
    """Load and validate an actual/inspection log file. Returns list[ActualRecord]."""
    rows = _load_rows(path)
    return [_parse_actual_row(row, i) for i, row in enumerate(rows)]
