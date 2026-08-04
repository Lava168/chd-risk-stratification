import tempfile
import unittest
from pathlib import Path

from chd_risk.china_par import china_par_proxy, normalize_china_par_score
from chd_risk.features import build_feature_vector
from chd_risk.model import WeightedRiskModel
from chd_risk.quality import completeness, range_violations
from chd_risk.schema import PatientSnapshot, parse_bool, parse_int
from chd_risk.synthetic import generate_synthetic_records


class SchemaTests(unittest.TestCase):
    def test_age_required(self):
        with self.assertRaises(ValueError):
            PatientSnapshot.from_mapping({"sex": "男"})

    def test_parse_bool_variants(self):
        for truthy in ("1", "true", "yes", "是", "有", "阳性", True, 1):
            self.assertTrue(parse_bool(truthy), msg=repr(truthy))
        for falsy in ("0", "false", "no", "否", "无", "阴性", False, 0):
            self.assertFalse(parse_bool(falsy), msg=repr(falsy))
        self.assertIsNone(parse_bool("maybe"))
        self.assertIsNone(parse_bool(None))

    def test_parse_int_rounds(self):
        self.assertEqual(parse_int("72.9"), 73)
        self.assertEqual(parse_int("3.2"), 3)
        self.assertIsNone(parse_int(""))

    def test_nan_treated_as_missing(self):
        import math
        self.assertIsNone(parse_bool(math.nan))
        self.assertIsNone(parse_bool("NaN"))


class FeatureTests(unittest.TestCase):
    def test_derived_features(self):
        snapshot = PatientSnapshot.from_mapping(
            {
                "patient_id": "F-1",
                "age": 60,
                "sex": "男",
                "sbp": 140,
                "dbp": 90,
                "hdl_c": 0.9,
                "total_chol": 5.5,
            }
        )
        features = build_feature_vector(snapshot)
        self.assertEqual(features["male"], 1.0)
        self.assertEqual(features["pulse_pressure"], 50.0)
        self.assertEqual(features["hdl_c_low"], 1.0)
        self.assertEqual(features["total_chol"], 5.5)

    def test_unknown_sex_yields_none_male(self):
        snapshot = PatientSnapshot.from_mapping({"patient_id": "F-2", "age": 50, "sex": "unknown"})
        self.assertIsNone(build_feature_vector(snapshot)["male"])


class ChinaParTests(unittest.TestCase):
    def test_normalize_score(self):
        # Values in 0-1 are kept; values > 1 are treated as 0-100 percentage scale.
        self.assertAlmostEqual(normalize_china_par_score(0.12), 0.12)
        self.assertAlmostEqual(normalize_china_par_score(12.0), 0.12)
        self.assertAlmostEqual(normalize_china_par_score(150.0), 1.0)
        self.assertAlmostEqual(normalize_china_par_score(-0.1), 0.0)

    def test_proxy_runs(self):
        snapshot = PatientSnapshot.from_mapping(
            {"patient_id": "C-1", "age": 55, "sex": "男", "sbp": 135, "total_chol": 5.2}
        )
        estimate = china_par_proxy(snapshot)
        self.assertGreaterEqual(estimate.probability, 0.0)
        self.assertLessEqual(estimate.probability, 1.0)
        self.assertEqual(estimate.source, "china_par_proxy")


class ModelPersistenceTests(unittest.TestCase):
    def test_save_load_roundtrip(self):
        model = WeightedRiskModel()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.json"
            model.save(path)
            loaded = WeightedRiskModel.load(path)
        self.assertEqual(loaded.intercept, model.intercept)
        self.assertEqual(len(loaded.feature_rules), len(model.feature_rules))
        self.assertEqual(loaded.version, model.version)


class QualityTests(unittest.TestCase):
    def test_completeness(self):
        rows = [
            {"age": 50, "sex": "男", "sbp": 120},
            {"age": "", "sex": "女", "sbp": None},
        ]
        result = completeness(rows, fields=("age", "sex", "sbp"))
        self.assertEqual(result["age"], 0.5)
        self.assertEqual(result["sex"], 1.0)
        self.assertEqual(result["sbp"], 0.5)

    def test_range_violations(self):
        rows = [{"age": 300, "sbp": 80, "bmi": 20}, {"age": 50, "sbp": 500, "bmi": 99}]
        result = range_violations(rows)
        self.assertEqual(result.get("age"), 1)
        self.assertEqual(result.get("sbp"), 1)
        self.assertEqual(result.get("bmi"), 1)


class SyntheticTests(unittest.TestCase):
    def test_synthetic_records_have_expected_columns(self):
        records = generate_synthetic_records(n=5, seed=1)
        self.assertEqual(len(records), 5)
        self.assertIn("outcome_chd", records[0])
        self.assertIn("atrial_fibrillation", records[0])
        self.assertIn("carotid_ultrasound_abnormal", records[0])
        self.assertIn("antiplatelet_use", records[0])


if __name__ == "__main__":
    unittest.main()
