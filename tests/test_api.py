import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from chd_risk.api import app


class RecordingBundle:
    tier_thresholds = None

    def __init__(self):
        self.snapshot = None

    def predict_proba(self, snapshot):
        self.snapshot = snapshot
        return 0.72

    def top_contributors(self, snapshot, limit=6):
        return [("creatinine", 0.5)]

    def describe(self):
        return "trained:test-model"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_assess_preserves_all_laboratory_fields(self):
        bundle = RecordingBundle()
        payload = {
            "patient_id": "API-1",
            "age": 68,
            "sex": "男",
            "triglyceride": 1.9,
            "glucose": 8.1,
            "hba1c": 7.2,
            "creatinine": 92,
            "uric_acid": 430,
            "bun": 6.8,
        }

        with patch("chd_risk.api.load_bundle", return_value=bundle):
            response = self.client.post("/assess", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(bundle.snapshot.triglyceride, 1.9)
        self.assertEqual(bundle.snapshot.glucose, 8.1)
        self.assertEqual(bundle.snapshot.hba1c, 7.2)
        self.assertEqual(bundle.snapshot.creatinine, 92)
        self.assertEqual(bundle.snapshot.uric_acid, 430)
        self.assertEqual(bundle.snapshot.bun, 6.8)
        self.assertEqual(response.json()["model_source"], "trained:test-model")

    def test_health_reports_trained_model_readiness(self):
        with patch("chd_risk.api.load_bundle", return_value=RecordingBundle()):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["model_ready"])
        self.assertEqual(response.json()["model_status"], "trained")

    def test_health_reports_model_load_failure_without_leaking_details(self):
        with patch("chd_risk.api.load_bundle", side_effect=RuntimeError("private path")):
            response = self.client.get("/health")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(body["model_ready"])
        self.assertEqual(body["model_status"], "error")
        self.assertEqual(body["model_error"], "RuntimeError")
        self.assertNotIn("private path", str(body))


if __name__ == "__main__":
    unittest.main()
