"""Leakage, persistence and inference contract tests for the exported estimators."""
import hashlib
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from ml.features import FEATURES, FORBIDDEN_FEATURES, duplicate_group, feature_frame
from ml.predict import PricePredictor, PredictionInputError
from ml.train import ROOT, pipeline, split_rows


class MLBoundaryTests(unittest.TestCase):
    def test_group_key_ignores_price_source_and_punctuation(self):
        original = {"vehicle_type": "Bike", "brand": "Yamaha", "model": "MT-15", "manufacture_year": 2020,
                    "km_driven": 30200, "price": 200000, "source_id": "one"}
        relisted = {**original, "model": "mt 15", "km_driven": 30300, "price": 220000, "source_id": "two"}
        self.assertEqual(duplicate_group(original), duplicate_group(relisted))

    def test_group_partitions_are_disjoint_and_deterministic(self):
        rows = pd.DataFrame({"source_id": ["source_a", "source_b"] * 50,
                             "group_id": [f"group_{i // 2}" for i in range(100)]})
        result = split_rows(rows)
        self.assertEqual(set(result), {"train", "validation", "test"})
        self.assertTrue(np.array_equal(result, split_rows(rows)))
        rows["partition"] = result
        self.assertTrue(rows.groupby("group_id").partition.nunique().eq(1).all())

    def test_feature_frame_excludes_targets_and_recomputes_age(self):
        rows = pd.DataFrame([{"manufacture_year": 2020, "reference_year": 2025, "km_driven": 10000,
                              "engine_capacity_cc": 150, "brand": "Bajaj", "model": "Pulsar 150",
                              "price": 999, "log_price": 999, "vehicle_age": 999, "km_per_year": 999,
                              "source_id": "do-not-use", "record_id": "do-not-use"}])
        frame = feature_frame(rows, "Bike")
        self.assertFalse(FORBIDDEN_FEATURES.intersection(frame.columns))
        self.assertEqual(frame.iloc[0].vehicle_age, 5)
        self.assertEqual(frame.iloc[0].km_per_year, 2000)

    def test_imputer_and_encoder_do_not_learn_from_prediction_rows(self):
        base = {"manufacture_year": 2020, "reference_year": 2025, "km_driven": 10000,
                "engine_capacity_cc": 150, "brand": "Bajaj", "model": "Pulsar 150"}
        rows = pd.DataFrame([base, {**base, "km_driven": 20000, "engine_capacity_cc": 200}])
        model = pipeline("Bike", Ridge()).fit(feature_frame(rows, "Bike"), [100000, 150000])
        preprocess = model.regressor_.named_steps["preprocess"]
        numeric = preprocess.named_transformers_["numeric"].named_steps["imputer"]
        categories = preprocess.named_transformers_["categorical"].named_steps["onehot"].categories_
        before = numeric.statistics_.copy()
        test = feature_frame(pd.DataFrame([{**base, "brand": "NeverSeen", "km_driven": 900000, "engine_capacity_cc": None}]), "Bike")
        self.assertTrue(np.isfinite(model.predict(test)).all())
        np.testing.assert_array_equal(before, numeric.statistics_)
        self.assertNotIn("neverseen", categories[0])
        self.assertEqual(before[FEATURES["Bike"]["numeric"].index("engine_capacity_cc")], 175)


@unittest.skipUnless((ROOT / "models/current.json").exists(), "Train exported artifacts first")
class ExportedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PricePredictor()
        cls.version = cls.predictor.version
        cls.manifest = cls.predictor.manifest
        cls.data = pd.concat([pd.read_csv(ROOT / path) for path in cls.manifest["input_sha256"]], ignore_index=True)
        cls.splits = pd.read_csv(ROOT / f"reports/phase2/{cls.version}/split_assignments.csv")

    def test_all_approved_rows_accounted_and_groups_do_not_cross_splits(self):
        self.assertEqual(len(self.splits), 3316)
        self.assertEqual(set(self.splits.record_id), set(self.data.record_id))
        self.assertTrue(self.splits.groupby("group_id").partition.nunique().eq(1).all())
        self.assertFalse(self.manifest["fit_includes_test"])

    def test_manifest_input_hashes_match(self):
        for name, expected in self.manifest["input_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_reload_predictions_match_reported_test_predictions(self):
        expected = pd.read_csv(ROOT / f"reports/phase2/{self.version}/test_predictions.csv")
        for kind in FEATURES:
            subset = expected.loc[expected.vehicle_type == kind]
            rows = self.data.set_index("record_id").loc[subset.record_id]
            model, metadata = self.predictor._load(kind)
            actual = model.predict(feature_frame(rows, kind))
            np.testing.assert_allclose(actual, subset.predicted_price_npr.to_numpy(), rtol=1e-10)
            self.assertEqual(metadata["fit_rows"], int(((self.splits.vehicle_type == kind) & (self.splits.partition != "test")).sum()))

    def test_known_examples_are_finite_positive_and_warn_about_source(self):
        for kind in FEATURES:
            payload = json.loads((ROOT / f"examples/predict-{kind.lower()}.json").read_text())
            prediction = self.predictor.predict(payload, valuation_year=2026)
            self.assertTrue(math.isfinite(prediction["predicted_price"]))
            self.assertGreater(prediction["predicted_price"], 0)
            self.assertIn("unverified_source", {w["code"] for w in prediction["warnings"]})
            self.assertEqual(prediction["currency"], "NPR")
            json.dumps(prediction, allow_nan=False)

    def test_missing_optional_features_use_fitted_defaults(self):
        result = self.predictor.predict({"vehicle_type": "Bike", "brand": "Bajaj", "model": "Pulsar 150",
                                         "manufacture_year": 2020, "km_driven": 10000}, valuation_year=2026)
        self.assertIn("imputed_features", {w["code"] for w in result["warnings"]})

    def test_invalid_values_unknown_fields_and_target_injection_rejected(self):
        base = json.loads((ROOT / "examples/predict-bike.json").read_text())
        for change in ({"price": 100000}, {"source_id": "one"}, {"manufacture_year": 2076},
                       {"km_driven": -1}, {"km_driven": True}, {"km_driven": float("nan")},
                       {"brand": ""}, {"vehicle_type": "Truck"}, {"owner_count": 1.5},
                       {"fuel_type": "Electric", "engine_capacity_cc": 150}):
            with self.subTest(change=change), self.assertRaises(PredictionInputError):
                self.predictor.predict({**base, **change}, valuation_year=2026)

    def test_unseen_model_and_ignored_features_are_explicit(self):
        base = json.loads((ROOT / "examples/predict-bike.json").read_text())
        with self.assertRaises(PredictionInputError):
            self.predictor.predict({**base, "model": "Unknown 999"}, valuation_year=2026)
        result = self.predictor.predict({**base, "insurance_status": "insured"}, valuation_year=2026)
        self.assertEqual(result["ignored_input_fields"], ["insurance_status"])

    def test_ignored_specification_does_not_change_price(self):
        base = json.loads((ROOT / "examples/predict-bike.json").read_text())
        one = self.predictor.predict(base, valuation_year=2026)
        two = self.predictor.predict({**base, "insurance_status": "insured", "owner_count": 3}, valuation_year=2026)
        self.assertEqual(one["predicted_price"], two["predicted_price"])

    def test_tampered_artifact_fails_before_deserialization(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = ROOT / "models" / self.version
            target = base / self.version
            target.mkdir()
            for name in ("manifest.json", "car.json"):
                shutil.copyfile(source / name, target / name)
            (target / "car.joblib").write_bytes(b"not a trusted artifact")
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                PricePredictor(model_dir=base, version=self.version)._load("Car")


if __name__ == "__main__":
    unittest.main()
