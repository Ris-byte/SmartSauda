"""Check data-integrity boundaries and row accounting, without training any model."""
import copy
import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_data import ROOT, RAW_COLUMNS, build, normalize, read_json


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.source = read_json(ROOT / "data/sources.json")["local_source"]
        self.raw = dict(zip(RAW_COLUMNS, [
            "Bagmati", "Bike", "Bajaj", "Pulsar 220", "2022", "25000",
            "220", "1", "Petrol", "Manual", "Good", "160000",
        ]))
        self.rules = {("byd", "dolphin"): {"year": 2021}}

    def clean(self, **updates):
        raw = {**self.raw, **updates}
        original = copy.deepcopy(raw)
        result = normalize(raw, 2, self.source, "sample-sha", 2026, self.rules)
        self.assertEqual(raw, original, "Cleaning must never mutate the source row")
        return result

    def test_plausible_row_preserves_price_and_has_traceable_features(self):
        row, errors = self.clean()
        self.assertEqual(errors, [])
        self.assertEqual(row["price"], 160000)
        self.assertEqual(row["vehicle_age"], 4)
        self.assertEqual(row["km_per_year"], 6250)
        self.assertAlmostEqual(math.exp(row["log_price"]), row["price"], places=4)
        self.assertFalse(row["training_eligible"])
        self.assertEqual(row["record_id"], "nepal_user_2000:2")

    def test_suv_maps_to_car_and_retains_body_type(self):
        row, _ = self.clean(vehicle_type="SUV")
        self.assertEqual((row["vehicle_type"], row["body_type"]), ("Car", "SUV"))

    def test_missing_features_are_not_invented(self):
        row, _ = self.clean()
        for field in ("city", "insurance_status", "power_bhp", "seats", "mileage_kmpl", "gears"):
            self.assertIsNone(row[field])

    def test_pre_introduction_year_is_not_clamped(self):
        row, errors = self.clean(brand="BYD", model="Dolphin", year="2013", fuel_type="Electric", engine_capacity="0")
        self.assertIn("year_before_documented_model_introduction", errors)
        self.assertEqual(row["manufacture_year"], 2013)

    def test_electric_displacement_conflict_is_not_silently_repaired(self):
        row, errors = self.clean(fuel_type="Electric", engine_capacity="1200")
        self.assertIn("electric_engine_displacement_conflict", errors)
        self.assertEqual(row["engine_capacity_cc"], 1200)

    def test_new_vehicle_does_not_divide_by_zero(self):
        row, errors = self.clean(year="2026")
        self.assertEqual(errors, [])
        self.assertIsNone(row["km_per_year"])

    def test_future_year_and_nonpositive_price_are_quarantined(self):
        _, errors = self.clean(year="2027", price="0")
        self.assertIn("out_of_range_manufacture_year", errors)
        self.assertIn("out_of_range_price", errors)

    def test_nan_infinity_fractional_year_and_owners_fail_validation(self):
        for updates, expected in [
            ({"price": "NaN"}, "invalid_price"),
            ({"km_driven": "inf"}, "invalid_km_driven"),
            ({"year": "2020.5"}, "invalid_manufacture_year"),
            ({"owners": "1.5"}, "invalid_owner_count"),
            ({"km_driven": "-1"}, "out_of_range_km_driven"),
        ]:
            with self.subTest(updates=updates):
                self.assertIn(expected, self.clean(**updates)[1])

    def test_unknown_vehicle_or_category_requires_review(self):
        self.assertIn("missing_or_unknown_vehicle_type", self.clean(vehicle_type="Truck")[1])
        self.assertIn("missing_or_unknown_fuel_type", self.clean(fuel_type="Something else")[1])

    def test_full_pipeline_accounts_for_rows_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            config = read_json(ROOT / "data/sources.json")
            config["local_source"]["input_path"] = "input.tsv"
            (root / "data/sources.json").write_text(json.dumps(config), encoding="utf-8")
            (root / "data/model_year_rules.json").write_text('{"rules": []}', encoding="utf-8")
            with (root / "input.tsv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS, delimiter="\t")
                writer.writeheader()
                writer.writerows([self.raw, self.raw, {**self.raw, "price": "-1"}])
            before = (root / "input.tsv").read_bytes()
            report = build(root)
            self.assertEqual((report["raw_rows"], report["retained"], report["duplicates"], report["quarantined"]), (3, 1, 1, 1))
            first = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            build(root)
            self.assertEqual(first, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            self.assertEqual(before, (root / "input.tsv").read_bytes())
            (root / "input.tsv").write_bytes(before + b"\n")
            with self.assertRaisesRegex(ValueError, "immutable snapshot"):
                build(root)


if __name__ == "__main__":
    unittest.main()
