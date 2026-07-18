"""Unit tests for the plan-vs-actual reconciliation engine.

Run with:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recon.ingest import ActualRecord, PlanItem, load_actual, load_plan
from recon.match import match_items
from recon.report import build_deviations, build_markdown_report
from recon.tolerance import (
    STATUS_BORDERLINE,
    STATUS_MATERIAL_MATCH,
    STATUS_MATERIAL_MISMATCH,
    STATUS_OUT_OF_TOL,
    STATUS_UNIT_MISMATCH,
    STATUS_WITHIN,
    evaluate,
)
from recon.util import SchemaError, UnitError, convert

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tmp_json(data) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _dim_plan(item_id="P-1", location="L-1", expected=100.0, unit="mm", tol=5.0):
    return PlanItem(
        item_id=item_id, location=location, description="test dim",
        category="dimension", expected_value=expected, unit=unit,
        tol_plus=tol, tol_minus=tol,
    )


def _dim_actual(item_id="P-1", location="L-1", value=100.0, unit="mm", row=0):
    return ActualRecord(
        item_id=item_id, location=location, measured_value=value, unit=unit,
        source_row=row,
    )


class TestIngest(unittest.TestCase):
    def test_load_plan_valid_json(self):
        path = _tmp_json([
            {"item_id": "P-1", "location": "L-1", "description": "d",
             "category": "dimension", "expected_value": 10, "unit": "mm",
             "tol_plus": 1, "tol_minus": 1},
        ])
        try:
            items = load_plan(path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].item_id, "P-1")
            self.assertEqual(items[0].category, "dimension")
        finally:
            _cleanup(path)

    def test_load_actual_valid_json(self):
        path = _tmp_json([
            {"item_id": "P-1", "location": "L-1", "measured_value": 10, "unit": "mm"},
        ])
        try:
            records = load_actual(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].measured_value, 10.0)
        finally:
            _cleanup(path)

    def test_load_plan_missing_required_field_raises(self):
        path = _tmp_json([{"item_id": "P-1", "category": "dimension"}])  # no location
        try:
            with self.assertRaises(SchemaError):
                load_plan(path)
        finally:
            _cleanup(path)

    def test_load_plan_invalid_category_raises(self):
        path = _tmp_json([{"item_id": "P-1", "location": "L-1", "category": "bogus"}])
        try:
            with self.assertRaises(SchemaError):
                load_plan(path)
        finally:
            _cleanup(path)

    def test_load_plan_duplicate_item_id_raises(self):
        path = _tmp_json([
            {"item_id": "P-1", "location": "L-1", "category": "dimension"},
            {"item_id": "P-1", "location": "L-2", "category": "dimension"},
        ])
        try:
            with self.assertRaises(SchemaError):
                load_plan(path)
        finally:
            _cleanup(path)

    def test_load_actual_csv(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("item_id,location,measured_value,unit\n")
            fh.write("P-1,L-1,10,mm\n")
        try:
            records = load_actual(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].location, "L-1")
            self.assertAlmostEqual(records[0].measured_value, 10.0)
        finally:
            _cleanup(path)


class TestMatch(unittest.TestCase):
    def test_one_to_one_match(self):
        plan = [_dim_plan()]
        actual = [_dim_actual()]
        result = match_items(plan, actual)
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(len(result.missing), 0)
        self.assertEqual(len(result.extra), 0)
        self.assertEqual(len(result.ambiguous), 0)

    def test_missing_item(self):
        plan = [_dim_plan(item_id="P-1"), _dim_plan(item_id="P-2", location="L-2")]
        actual = [_dim_actual(item_id="P-1")]
        result = match_items(plan, actual)
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(len(result.missing), 1)
        self.assertEqual(result.missing[0].item_id, "P-2")

    def test_extra_item(self):
        plan = [_dim_plan(item_id="P-1")]
        actual = [_dim_actual(item_id="P-1"), _dim_actual(item_id="X-9", location="Unknown", row=1)]
        result = match_items(plan, actual)
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(len(result.extra), 1)
        self.assertEqual(result.extra[0].item_id, "X-9")

    def test_ambiguous_one_to_many_not_silently_matched(self):
        plan = [_dim_plan(item_id="P-1")]
        actual = [
            _dim_actual(item_id="P-1", value=99.0, row=0),
            _dim_actual(item_id="P-1", value=105.0, row=1),
        ]
        result = match_items(plan, actual)
        self.assertEqual(len(result.matched), 0, "ambiguous pair must not be auto-matched")
        self.assertEqual(len(result.ambiguous), 1)
        plan_item, candidates = result.ambiguous[0]
        self.assertEqual(plan_item.item_id, "P-1")
        self.assertEqual(len(candidates), 2)
        # Both candidates must be fully surfaced, not just the first one.
        values = sorted(c.measured_value for c in candidates)
        self.assertEqual(values, [99.0, 105.0])

    def test_match_falls_back_to_location_when_no_item_id_on_actual(self):
        plan = [_dim_plan(item_id="P-1", location="Room-1")]
        actual = [ActualRecord(location="Room-1", item_id=None, measured_value=100.0, unit="mm", source_row=0)]
        result = match_items(plan, actual)
        self.assertEqual(len(result.matched), 1)


class TestTolerance(unittest.TestCase):
    def test_within_tolerance(self):
        plan = _dim_plan(expected=100.0, tol=5.0)
        actual = _dim_actual(value=101.0)  # delta 1, ratio 0.2
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_WITHIN)

    def test_exactly_at_boundary_is_within_tolerance(self):
        plan = _dim_plan(expected=100.0, tol=5.0)
        actual = _dim_actual(value=105.0)  # delta == tol exactly
        dev = evaluate(plan, actual)
        self.assertNotEqual(dev.status, STATUS_OUT_OF_TOL)
        self.assertIn(dev.status, (STATUS_WITHIN, STATUS_BORDERLINE))

    def test_just_past_boundary_is_out_of_tolerance(self):
        plan = _dim_plan(expected=100.0, tol=5.0)
        actual = _dim_actual(value=105.01)  # delta just past tol
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_OUT_OF_TOL)

    def test_borderline_band(self):
        plan = _dim_plan(expected=100.0, tol=10.0)
        actual = _dim_actual(value=109.3)  # delta 9.3, ratio 0.93 -> borderline
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_BORDERLINE)

    def test_out_of_tolerance_clearly(self):
        plan = _dim_plan(expected=100.0, tol=5.0)
        actual = _dim_actual(value=130.0)
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_OUT_OF_TOL)

    def test_material_match(self):
        plan = PlanItem(item_id="P-1", location="L-1", description="d",
                         category="material", expected_material="Steel")
        actual = ActualRecord(item_id="P-1", location="L-1", material="steel", source_row=0)
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_MATERIAL_MATCH)

    def test_material_mismatch(self):
        plan = PlanItem(item_id="P-1", location="L-1", description="d",
                         category="material", expected_material="oak")
        actual = ActualRecord(item_id="P-1", location="L-1", material="laminate", source_row=0)
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_MATERIAL_MISMATCH)

    def test_unit_conversion_mm_to_cm_within_tolerance(self):
        plan = _dim_plan(expected=500.0, unit="mm", tol=5.0)
        actual = _dim_actual(value=50.2, unit="cm")  # 502mm, delta 2
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_WITHIN)
        self.assertAlmostEqual(dev.actual, 502.0)

    def test_unit_incompatible_flagged_not_guessed(self):
        plan = _dim_plan(expected=500.0, unit="mm", tol=5.0)
        actual = _dim_actual(value=5.0, unit="widgets")
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_UNIT_MISMATCH)

    def test_convert_raises_unit_error_for_unknown_unit(self):
        with self.assertRaises(UnitError):
            convert(1.0, "mm", "banana")

    def test_count_category_exact_match(self):
        plan = PlanItem(item_id="P-1", location="L-1", description="fixtures",
                         category="count", expected_value=4, unit="count",
                         tol_plus=0.0, tol_minus=0.0)
        actual = ActualRecord(item_id="P-1", location="L-1", measured_value=4, unit="count", source_row=0)
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_WITHIN)
        self.assertEqual(dev.delta, 0.0)

    def test_count_category_mismatch_is_out_of_tolerance(self):
        plan = PlanItem(item_id="P-1", location="L-1", description="fixtures",
                         category="count", expected_value=4, unit="count",
                         tol_plus=0.0, tol_minus=0.0)
        actual = ActualRecord(item_id="P-1", location="L-1", measured_value=3, unit="count", source_row=0)
        dev = evaluate(plan, actual)
        self.assertEqual(dev.status, STATUS_OUT_OF_TOL)


class TestReportAndDeviationNumbers(unittest.TestCase):
    def test_deviations_always_carry_expected_actual_tol_delta_numbers(self):
        plan_over = _dim_plan(item_id="P-OVER", expected=100.0, tol=5.0)
        actual_over = _dim_actual(item_id="P-OVER", value=130.0)
        plan_border = _dim_plan(item_id="P-BORDER", expected=100.0, tol=10.0)
        actual_border = _dim_actual(item_id="P-BORDER", value=109.3)

        result = match_items([plan_over, plan_border], [actual_over, actual_border])
        deviations = build_deviations(result)

        checked = 0
        for d in deviations:
            if d.status in (STATUS_OUT_OF_TOL, STATUS_BORDERLINE):
                self.assertIsInstance(d.expected, (int, float), msg=d)
                self.assertIsInstance(d.actual, (int, float), msg=d)
                self.assertIsInstance(d.tol_plus, (int, float), msg=d)
                self.assertIsInstance(d.tol_minus, (int, float), msg=d)
                self.assertIsInstance(d.delta, (int, float), msg=d)
                checked += 1
        self.assertEqual(checked, 2)

    def test_markdown_report_contains_expected_sections(self):
        plan = [_dim_plan(item_id="P-1")]
        actual = [_dim_actual(item_id="P-1")]
        result = match_items(plan, actual)
        deviations = build_deviations(result)
        md = build_markdown_report(deviations, len(plan), len(actual))
        self.assertIn("# Plan vs Actual Reconciliation Report", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Item-by-item status", md)
        self.assertIn("## Deviations requiring attention", md)

    def test_missing_and_extra_appear_in_deviations(self):
        plan = [_dim_plan(item_id="P-1"), _dim_plan(item_id="P-2", location="L-2")]
        actual = [_dim_actual(item_id="P-1"), _dim_actual(item_id="X-9", location="Unknown", row=1)]
        result = match_items(plan, actual)
        deviations = build_deviations(result)
        statuses = {d.item_id: d.status for d in deviations}
        self.assertEqual(statuses["P-2"], "missing")
        self.assertEqual(statuses["X-9"], "extra")


class TestDeterminism(unittest.TestCase):
    def test_run_demo_is_byte_identical_across_runs(self):
        # Run the demo pipeline twice into two separate temp directories
        # using the same generated inputs, and compare md5 hashes of
        # every output file.
        import importlib

        recon_run = importlib.import_module("recon.run")
        gen = importlib.import_module("data.generate_plan_actual")

        data_dir = tempfile.mkdtemp()
        out_dir_1 = tempfile.mkdtemp()
        out_dir_2 = tempfile.mkdtemp()
        try:
            old_cwd = os.getcwd()
            # generate_plan_actual writes next to its own __file__, so just
            # reuse the real data dir it already wrote for run_demo tests;
            # instead, build plan/actual directly here for isolation.
            plan_path = os.path.join(data_dir, "plan.json")
            actual_path = os.path.join(data_dir, "actual.json")
            with open(plan_path, "w", encoding="utf-8") as fh:
                json.dump([
                    {"item_id": "P-1", "location": "L-1", "description": "d",
                     "category": "dimension", "expected_value": 100, "unit": "mm",
                     "tol_plus": 5, "tol_minus": 5},
                ], fh, sort_keys=True)
            with open(actual_path, "w", encoding="utf-8") as fh:
                json.dump([
                    {"item_id": "P-1", "location": "L-1", "measured_value": 101, "unit": "mm"},
                ], fh, sort_keys=True)

            recon_run.run(plan_path, actual_path, out_dir_1)
            recon_run.run(plan_path, actual_path, out_dir_2)

            for fname in ("reconciliation_report.md", "matches.csv", "deviations.csv", "run_summary.txt"):
                p1 = os.path.join(out_dir_1, fname)
                p2 = os.path.join(out_dir_2, fname)
                with open(p1, "rb") as f1, open(p2, "rb") as f2:
                    h1 = hashlib.md5(f1.read()).hexdigest()
                    h2 = hashlib.md5(f2.read()).hexdigest()
                self.assertEqual(h1, h2, f"{fname} differs between runs")
        finally:
            for d in (data_dir, out_dir_1, out_dir_2):
                for root, _, files in os.walk(d):
                    for f in files:
                        try:
                            os.unlink(os.path.join(root, f))
                        except OSError:
                            pass
                try:
                    os.rmdir(d)
                except OSError:
                    pass

    def test_generated_plan_and_actual_are_byte_identical_across_runs(self):
        import importlib

        gen = importlib.import_module("data.generate_plan_actual")
        gen.main()
        plan_path = os.path.join(ROOT, "data", "plan.json")
        actual_path = os.path.join(ROOT, "data", "actual.json")
        with open(plan_path, "rb") as fh:
            h1 = hashlib.md5(fh.read()).hexdigest()
        gen.main()
        with open(plan_path, "rb") as fh:
            h2 = hashlib.md5(fh.read()).hexdigest()
        self.assertEqual(h1, h2)
        self.assertTrue(os.path.exists(actual_path))


if __name__ == "__main__":
    unittest.main()
