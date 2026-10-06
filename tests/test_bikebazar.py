import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_bikebazar import RAW_COLUMNS, normalize_external


class PublicSourceTests(unittest.TestCase):
    def clean(self, **changes):
        raw = dict(zip(RAW_COLUMNS, ["1", "Royal Enfield Classic 350", "2020", "Rs. ",
                                    "350000", "350", "", "Cruiser", "12000", "Used", "Kathmandu"]))
        raw.update(changes)
        return normalize_external(raw, 2, "test", 2025, {})

    def test_multiword_brand_preserved_without_guessing_missing_specs(self):
        row, errors = self.clean()
        self.assertEqual(errors, [])
        self.assertEqual((row["brand"], row["model"]), ("Royal Enfield", "Classic 350"))
        self.assertEqual(row["vehicle_age"], 5)
        self.assertIsNone(row["fuel_type"])
        self.assertIsNone(row["city"])
        self.assertIsNone(row["condition"])
        self.assertEqual(row["listing_condition"], "used")

    def test_brand_new_records_are_excluded(self):
        self.assertIn("brand_new_not_resale", self.clean(condition="Brand new")[1])

    def test_ambiguous_calendar_is_not_automatically_converted(self):
        row, errors = self.clean(bike_model_year="2076")
        self.assertIn("year_out_of_range_or_calendar_ambiguous", errors)
        self.assertEqual(row["manufacture_year"], 2076)

    def test_negative_distance_is_excluded(self):
        self.assertIn("negative_km_driven", self.clean(bike_distance="-2")[1])

    def test_electric_power_is_not_engine_displacement(self):
        row, errors = self.clean(Bike_Name="Ather 450X", bike_power_cc="", bike_power_watt="6000", bike_type="Scooter")
        self.assertEqual(errors, [])
        self.assertEqual(row["motor_power_kw"], 6)
        self.assertIsNone(row["engine_capacity_cc"])
        self.assertEqual(row["vehicle_type"], "Scooter")


if __name__ == "__main__":
    unittest.main()
