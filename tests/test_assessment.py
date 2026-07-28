import unittest

from chd_risk import PatientSnapshot, assess_patient
from chd_risk.metrics import binary_classification_metrics, roc_auc_score
from chd_risk.risk import classify_risk


class AssessmentTests(unittest.TestCase):
    def test_high_risk_patient_receives_actionable_plan(self):
        snapshot = PatientSnapshot.from_mapping(
            {
                "patient_id": "T-1",
                "age": 72,
                "sex": "男",
                "bmi": 29.5,
                "sbp": 165,
                "dbp": 91,
                "ldl_c": 4.1,
                "hdl_c": 0.9,
                "fasting_glucose": 8.2,
                "smoker": True,
                "diabetes": True,
                "hypertension": True,
                "chest_pain_visit_last_year": True,
                "ecg_abnormal": True,
                "statin_adherence_gap": True,
                "follow_up_interrupted": True,
            }
        )

        assessment = assess_patient(snapshot)

        self.assertIn(assessment.tier, {"high", "very_high"})
        self.assertGreaterEqual(len(assessment.reasons), 3)
        self.assertGreater(assessment.plan.follow_up_days, 0)

    def test_low_risk_patient_stays_low_or_medium(self):
        snapshot = PatientSnapshot.from_mapping(
            {
                "patient_id": "T-2",
                "age": 39,
                "sex": "女",
                "bmi": 21.8,
                "sbp": 112,
                "dbp": 70,
                "ldl_c": 2.2,
                "hdl_c": 1.5,
                "fasting_glucose": 5.1,
                "smoker": False,
                "diabetes": False,
                "hypertension": False,
            }
        )

        assessment = assess_patient(snapshot)

        self.assertIn(assessment.tier, {"low", "medium"})

    def test_threshold_classifier(self):
        self.assertEqual(classify_risk(0.01), "low")
        self.assertEqual(classify_risk(0.07), "medium")
        self.assertEqual(classify_risk(0.14), "high")
        self.assertEqual(classify_risk(0.22), "very_high")

    def test_metrics_are_computable(self):
        auc = roc_auc_score([0, 0, 1, 1], [0.1, 0.3, 0.6, 0.9])
        self.assertAlmostEqual(auc, 1.0)
        metrics = binary_classification_metrics([0, 1, 1], [0.2, 0.8, 0.4], threshold=0.5)
        self.assertEqual(metrics["sensitivity"], 0.5)


if __name__ == "__main__":
    unittest.main()
