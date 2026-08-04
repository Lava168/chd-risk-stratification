from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TRUE_VALUES = {"1", "true", "t", "yes", "y", "是", "有", "阳性"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "否", "无", "阴性"}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return not text or text in {"nan", "null", "none", "na", "n/a"}
    return False


def parse_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_int(value: Any) -> int | None:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return round(parsed)


def parse_bool(value: Any) -> bool | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    return None


def parse_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class PatientSnapshot:
    """One de-identified patient snapshot for risk assessment."""

    patient_id: str
    age: int
    sex: str
    bmi: float | None = None
    sbp: float | None = None
    dbp: float | None = None
    total_chol: float | None = None
    ldl_c: float | None = None
    hdl_c: float | None = None
    fasting_glucose: float | None = None
    smoker: bool | None = None
    diabetes: bool | None = None
    hypertension: bool | None = None
    ckd: bool | None = None
    atrial_fibrillation: bool | None = None
    family_history_chd: bool | None = None
    chest_pain_visit_last_year: bool | None = None
    ecg_abnormal: bool | None = None
    carotid_ultrasound_abnormal: bool | None = None
    antihypertensive_use: bool | None = None
    lipid_lowering_use: bool | None = None
    antiplatelet_use: bool | None = None
    statin_adherence_gap: bool | None = None
    follow_up_interrupted: bool | None = None
    outpatient_visits_12m: int | None = None
    emergency_visits_12m: int | None = None
    sbp_trend_6m: float | None = None
    ldl_trend_6m: float | None = None
    medication_adherence_rate: float | None = None
    china_par_score: float | None = None
    reference_date: str | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> PatientSnapshot:
        patient_id = parse_text(payload.get("patient_id")) or "unknown"
        age = parse_int(payload.get("age"))
        if age is None:
            raise ValueError("age is required")
        sex = parse_text(payload.get("sex")) or "unknown"
        return cls(
            patient_id=patient_id,
            age=age,
            sex=sex,
            bmi=parse_float(payload.get("bmi")),
            sbp=parse_float(payload.get("sbp")),
            dbp=parse_float(payload.get("dbp")),
            total_chol=parse_float(payload.get("total_chol")),
            ldl_c=parse_float(payload.get("ldl_c")),
            hdl_c=parse_float(payload.get("hdl_c")),
            fasting_glucose=parse_float(payload.get("fasting_glucose")),
            smoker=parse_bool(payload.get("smoker")),
            diabetes=parse_bool(payload.get("diabetes")),
            hypertension=parse_bool(payload.get("hypertension")),
            ckd=parse_bool(payload.get("ckd")),
            atrial_fibrillation=parse_bool(payload.get("atrial_fibrillation")),
            family_history_chd=parse_bool(payload.get("family_history_chd")),
            chest_pain_visit_last_year=parse_bool(payload.get("chest_pain_visit_last_year")),
            ecg_abnormal=parse_bool(payload.get("ecg_abnormal")),
            carotid_ultrasound_abnormal=parse_bool(payload.get("carotid_ultrasound_abnormal")),
            antihypertensive_use=parse_bool(payload.get("antihypertensive_use")),
            lipid_lowering_use=parse_bool(payload.get("lipid_lowering_use")),
            antiplatelet_use=parse_bool(payload.get("antiplatelet_use")),
            statin_adherence_gap=parse_bool(payload.get("statin_adherence_gap")),
            follow_up_interrupted=parse_bool(payload.get("follow_up_interrupted")),
            outpatient_visits_12m=parse_int(payload.get("outpatient_visits_12m")),
            emergency_visits_12m=parse_int(payload.get("emergency_visits_12m")),
            sbp_trend_6m=parse_float(payload.get("sbp_trend_6m")),
            ldl_trend_6m=parse_float(payload.get("ldl_trend_6m")),
            medication_adherence_rate=parse_float(payload.get("medication_adherence_rate")),
            china_par_score=parse_float(payload.get("china_par_score")),
            reference_date=parse_text(payload.get("reference_date")),
        )

