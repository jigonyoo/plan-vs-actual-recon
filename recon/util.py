"""Shared helpers: unit conversion, number parsing, deterministic I/O.

Stdlib only. No network. No wall-clock timestamps are ever embedded in
any output file, so outputs are byte-identical across runs given the
same inputs.
"""
from __future__ import annotations

import csv
import json
from typing import Any, Iterable, Optional


class SchemaError(ValueError):
    """Raised when an input plan/actual record fails validation."""


class UnitError(ValueError):
    """Raised when a unit is unknown or two units are not comparable."""


# Length-unit conversion table: factor to convert TO millimetres.
# This is the only unit family this sample understands. Anything else
# (or a unit missing from this table) is treated as non-convertible.
_MM_PER_UNIT = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "ft": 304.8,
}


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    if unit is None:
        return None
    u = unit.strip().lower()
    return u if u else None


def convert(value: float, from_unit: Optional[str], to_unit: Optional[str]) -> float:
    """Convert `value` from from_unit to to_unit (length units only).

    Raises UnitError if either unit is unknown or the units are not
    both in the supported length-unit table.
    """
    fu = normalize_unit(from_unit)
    tu = normalize_unit(to_unit)
    if fu == tu:
        return value
    if fu not in _MM_PER_UNIT or tu not in _MM_PER_UNIT:
        raise UnitError(f"cannot convert unit {from_unit!r} -> {to_unit!r}")
    mm = value * _MM_PER_UNIT[fu]
    return mm / _MM_PER_UNIT[tu]


def to_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion; returns None for blank/None input."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError as exc:
        raise SchemaError(f"expected a number, got {value!r}") from exc


def norm_text(value: Any) -> Optional[str]:
    """Normalize a text field: strip whitespace, blank -> None."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def norm_category(value: Any) -> Optional[str]:
    """Case/space-insensitive normalization for categorical comparisons."""
    s = norm_text(value)
    return s.lower() if s is not None else None


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(path: str) -> list:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [dict(row) for row in reader]


def write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_csv(path: str, fieldnames: Iterable[str], rows: Iterable[dict]) -> None:
    fieldnames = list(fieldnames)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})


def fmt_num(value: Optional[float]) -> str:
    """Deterministic, stable number formatting for reports/CSVs."""
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    # Round to 4 decimals, strip trailing zeros, keep it deterministic.
    rounded = round(float(value), 4)
    if rounded == int(rounded):
        return str(int(rounded))
    s = f"{rounded:.4f}".rstrip("0").rstrip(".")
    return s
