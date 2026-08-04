import tempfile
import unittest
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from chd_risk.model_registry import TrainedModelBundle, load_bundle
from chd_risk.schema import PatientSnapshot


def _make_bundle() -> TrainedModelBundle:
    X = np.array(
        [
            [50.0, 1.0, 5.0],
            [60.0, 0.0, 6.0],
            [70.0, 1.0, 7.0],
            [45.0, 0.0, 4.0],
        ]
    )
    y = np.array([0, 0, 1, 0])
    preprocessor = ColumnTransformer(
        [
            (
                "num",
                Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]),
                [0, 1, 2],
            )
        ]
    )
    model = LogisticRegression().fit(preprocessor.fit_transform(X), y)
    return TrainedModelBundle(
        preprocessor=preprocessor,
        model=model,
        feature_names=["age", "male", "total_chol"],
        model_name="logistic_regression",
        metadata={
            "outcome_col": "outcome_hospitalized",
            "data_provenance": "test",
            "tier_thresholds": [0.2, 0.4, 0.6],
            "tier_method": "score_quantiles",
        },
    )


class ModelRegistryTests(unittest.TestCase):
    def test_save_load_roundtrip(self):
        bundle = _make_bundle()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.joblib"
            bundle.save(path)
            loaded = TrainedModelBundle.load(path)
        self.assertEqual(loaded.model_name, "logistic_regression")
        self.assertEqual(loaded.feature_names, ["age", "male", "total_chol"])
        self.assertEqual(loaded.tier_thresholds, [0.2, 0.4, 0.6])

    def test_predict_proba(self):
        bundle = _make_bundle()
        snapshot = PatientSnapshot.from_mapping(
            {"patient_id": "R-1", "age": 68, "sex": "男", "total_chol": 6.2}
        )
        probability = bundle.predict_proba(snapshot)
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)

    def test_top_contributors_ignore_missing(self):
        bundle = _make_bundle()
        snapshot = PatientSnapshot.from_mapping(
            {"patient_id": "R-2", "age": 55, "sex": "女"}  # total_chol missing
        )
        contributors = bundle.top_contributors(snapshot)
        names = {name for name, _ in contributors}
        self.assertNotIn("total_chol", names)  # missing value must not be a "reason"

    def test_load_bundle_missing_path(self):
        self.assertIsNone(load_bundle("/nonexistent/bundle.joblib", use_cache=False))


if __name__ == "__main__":
    unittest.main()
