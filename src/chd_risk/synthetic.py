from __future__ import annotations

import csv
import random
from pathlib import Path

from .assessment import assess_patient
from .schema import PatientSnapshot


FIELDNAMES = [
    "patient_id", "age", "sex", "bmi", "sbp", "dbp", "total_chol", "ldl_c",
    "hdl_c", "fasting_glucose", "smoker", "diabetes", "hypertension", "ckd",
    "family_history_chd", "chest_pain_visit_last_year", "ecg_abnormal",
    "antihypertensive_use", "lipid_lowering_use", "statin_adherence_gap",
    "follow_up_interrupted", "outpatient_visits_12m", "emergency_visits_12m",
    "sbp_trend_6m", "ldl_trend_6m", "medication_adherence_rate", "synthetic_event",
]


def _yes_no(probability: float) -> bool:
    return random.random() < probability


def generate_synthetic_records(n: int = 200, seed: int = 42) -> list[dict]:
    random.seed(seed)
    records = []
    for index in range(n):
        age = int(min(max(random.gauss(59, 12), 35), 90))
        male = _yes_no(0.48)
        diabetes = _yes_no(0.10 + max(age - 55, 0) * 0.006)
        hypertension = _yes_no(0.18 + max(age - 50, 0) * 0.012)
        adherence = round(min(max(random.gauss(0.82, 0.16), 0.25), 1.0), 2)
        row = {
            "patient_id": f"SYN-{index + 1:05d}",
            "age": age,
            "sex": "男" if male else "女",
            "bmi": round(min(max(random.gauss(25.2, 3.6), 17.5), 38.0), 1),
            "sbp": round(random.gauss(118 + (age - 45) * 0.55 + (9 if hypertension else 0), 12), 0),
            "dbp": round(random.gauss(76 + (3 if hypertension else 0), 7), 0),
            "total_chol": round(random.gauss(4.8, 0.9), 2),
            "ldl_c": round(random.gauss(2.7 + (0.2 if diabetes else 0), 0.65), 2),
            "hdl_c": round(min(max(random.gauss(1.18 if male else 1.34, 0.24), 0.4), 3.0), 2),
            "fasting_glucose": round(random.gauss(6.4 if diabetes else 5.3, 0.8), 2),
            "smoker": _yes_no(0.30 if male else 0.08),
            "diabetes": diabetes,
            "hypertension": hypertension,
            "ckd": _yes_no(0.04 + max(age - 65, 0) * 0.004),
            "family_history_chd": _yes_no(0.12),
            "chest_pain_visit_last_year": _yes_no(0.06 + max(age - 65, 0) * 0.003),
            "ecg_abnormal": _yes_no(0.08 + max(age - 60, 0) * 0.004),
            "antihypertensive_use": hypertension and _yes_no(0.74),
            "lipid_lowering_use": _yes_no(0.18),
            "statin_adherence_gap": adherence < 0.70,
            "follow_up_interrupted": _yes_no(0.12),
            "outpatient_visits_12m": int(max(random.gauss(3.5, 3.0), 0)),
            "emergency_visits_12m": int(max(random.gauss(0.35, 0.8), 0)),
            "sbp_trend_6m": round(random.gauss(1.0 if hypertension else 0.0, 5.0), 1),
            "ldl_trend_6m": round(random.gauss(0.04, 0.25), 2),
            "medication_adherence_rate": adherence,
        }
        row["synthetic_event"] = _yes_no(assess_patient(PatientSnapshot.from_mapping(row)).probability * 0.65)
        records.append(row)
    return records


def write_synthetic_csv(path: str | Path, n: int = 200, seed: int = 42) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(generate_synthetic_records(n=n, seed=seed))
    return path
