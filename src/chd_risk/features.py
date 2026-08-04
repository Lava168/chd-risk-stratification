from __future__ import annotations

from .schema import PatientSnapshot

FEATURE_LABELS = {
    "age": "年龄",
    "male": "男性",
    "bmi": "BMI",
    "sbp": "收缩压",
    "pulse_pressure": "脉压",
    "total_chol": "总胆固醇",
    "ldl_c": "LDL-C",
    "hdl_c_low": "HDL-C偏低",
    "triglyceride": "甘油三酯",
    "fasting_glucose": "空腹血糖",
    "glucose": "血糖",
    "hba1c": "糖化血红蛋白",
    "creatinine": "肌酐",
    "uric_acid": "尿酸",
    "bun": "尿素氮",
    "has_lipids": "有血脂检验",
    "has_glucose": "有血糖检验",
    "has_renal": "有肾功能检验",
    "has_any_lab": "有任一检验",
    "smoker": "吸烟",
    "diabetes": "糖尿病",
    "hypertension": "高血压",
    "ckd": "慢性肾病",
    "atrial_fibrillation": "房颤",
    "family_history_chd": "冠心病家族史",
    "chest_pain_visit_last_year": "近1年胸痛就诊记录",
    "ecg_abnormal": "心电图异常",
    "carotid_ultrasound_abnormal": "颈动脉超声异常",
    "antihypertensive_use": "降压药使用",
    "lipid_lowering_use": "降脂药使用",
    "antiplatelet_use": "抗血小板药使用",
    "statin_adherence_gap": "他汀用药不连续",
    "follow_up_interrupted": "随访中断",
    "outpatient_visits_12m": "近12个月门诊频次",
    "emergency_visits_12m": "近12个月急诊频次",
    "sbp_trend_6m": "6个月收缩压趋势",
    "ldl_trend_6m": "6个月LDL-C趋势",
    "medication_adherence_rate": "用药依从率",
}


def _bool_feature(value: bool | None) -> float | None:
    if value is None:
        return None
    return 1.0 if value else 0.0


def _is_male(sex: str) -> float | None:
    normalized = sex.strip().lower()
    if normalized in {"male", "m", "man", "男"}:
        return 1.0
    if normalized in {"female", "f", "woman", "女"}:
        return 0.0
    return None


def build_feature_vector(snapshot: PatientSnapshot) -> dict[str, float | None]:
    pulse_pressure = None
    if snapshot.sbp is not None and snapshot.dbp is not None:
        pulse_pressure = snapshot.sbp - snapshot.dbp

    hdl_c_low = None
    if snapshot.hdl_c is not None:
        hdl_c_low = 1.0 if snapshot.hdl_c < 1.0 else 0.0

    return {
        "age": float(snapshot.age),
        "male": _is_male(snapshot.sex),
        "bmi": snapshot.bmi,
        "sbp": snapshot.sbp,
        "pulse_pressure": pulse_pressure,
        "total_chol": snapshot.total_chol,
        "ldl_c": snapshot.ldl_c,
        "hdl_c_low": hdl_c_low,
        "triglyceride": snapshot.triglyceride,
        "fasting_glucose": snapshot.fasting_glucose,
        "glucose": snapshot.glucose,
        "hba1c": snapshot.hba1c,
        "creatinine": snapshot.creatinine,
        "uric_acid": snapshot.uric_acid,
        "bun": snapshot.bun,
        "has_lipids": _bool_feature(
            snapshot.total_chol is not None or snapshot.ldl_c is not None
            or snapshot.hdl_c is not None or snapshot.triglyceride is not None
        ),
        "has_glucose": _bool_feature(
            snapshot.fasting_glucose is not None or snapshot.glucose is not None
            or snapshot.hba1c is not None
        ),
        "has_renal": _bool_feature(
            snapshot.creatinine is not None or snapshot.uric_acid is not None
            or snapshot.bun is not None
        ),
        "has_any_lab": _bool_feature(
            snapshot.total_chol is not None or snapshot.ldl_c is not None
            or snapshot.hdl_c is not None or snapshot.triglyceride is not None
            or snapshot.fasting_glucose is not None or snapshot.glucose is not None
            or snapshot.hba1c is not None or snapshot.creatinine is not None
            or snapshot.uric_acid is not None or snapshot.bun is not None
        ),
        "smoker": _bool_feature(snapshot.smoker),
        "diabetes": _bool_feature(snapshot.diabetes),
        "hypertension": _bool_feature(snapshot.hypertension),
        "ckd": _bool_feature(snapshot.ckd),
        "atrial_fibrillation": _bool_feature(snapshot.atrial_fibrillation),
        "family_history_chd": _bool_feature(snapshot.family_history_chd),
        "chest_pain_visit_last_year": _bool_feature(snapshot.chest_pain_visit_last_year),
        "ecg_abnormal": _bool_feature(snapshot.ecg_abnormal),
        "carotid_ultrasound_abnormal": _bool_feature(snapshot.carotid_ultrasound_abnormal),
        "antihypertensive_use": _bool_feature(snapshot.antihypertensive_use),
        "lipid_lowering_use": _bool_feature(snapshot.lipid_lowering_use),
        "antiplatelet_use": _bool_feature(snapshot.antiplatelet_use),
        "statin_adherence_gap": _bool_feature(snapshot.statin_adherence_gap),
        "follow_up_interrupted": _bool_feature(snapshot.follow_up_interrupted),
        "outpatient_visits_12m": float(snapshot.outpatient_visits_12m)
        if snapshot.outpatient_visits_12m is not None
        else None,
        "emergency_visits_12m": float(snapshot.emergency_visits_12m)
        if snapshot.emergency_visits_12m is not None
        else None,
        "sbp_trend_6m": snapshot.sbp_trend_6m,
        "ldl_trend_6m": snapshot.ldl_trend_6m,
        "medication_adherence_rate": snapshot.medication_adherence_rate,
    }

