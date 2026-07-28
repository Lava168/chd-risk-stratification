import unittest

from chd_risk import PatientSnapshot, assess_patient
from chd_risk.metrics import binary_classification_metrics, roc_auc_score
from chd_risk.risk import classify_risk


class AssessmentTests(unittest.TestCase):
    def test_assess_patient_returns_closed_loop_fields(self) -> None:
        patient = PatientSnapshot(
            patient_id="T001",
            age=68,
            sex="male",
            systolic_bp=152,
            total_cholesterol=5.9,
            hdl_cholesterol=1.0,
            ldl_cholesterol=3.7,
            diabetes=True,
            smoker=True,
            hypertension=True,
        )

        result = assess_patient(patient)

        self.assertEqual(result.patient_id, "T001")
        self.assertGreater(result.risk_score, 0)
        self.assertIn(result.risk_tier, {"low", "medium", "high", "very_high"})
        self.assertTrue(result.actions)
        self.assertTrue(result.explanations)

    def test_classify_risk_thresholds(self) -> None:
        self.assertEqual(classify_risk(0.02), "low")
        self.assertEqual(classify_risk(0.07), "medium")
        self.assertEqual(classify_risk(0.16), "high")
        self.assertEqual(classify_risk(0.32), "very_high")

    def test_roc_auc_score(self) -> None:
        auc = roc_auc_score([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8])
        self.assertAlmostEqual(auc, 0.75)

    def test_binary_metrics(self) -> None:
        metrics = binary_classification_metrics([0, 1, 1, 0], [0.1, 0.8, 0.3, 0.4], threshold=0.5)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["tn"], 2)
        self.assertEqual(metrics["fp"], 0)
        self.assertEqual(metrics["fn"], 1)


if __name__ == "__main__":
    unittest.main()
