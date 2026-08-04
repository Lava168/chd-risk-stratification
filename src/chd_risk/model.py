from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class FeatureRule:
    name: str
    weight: float
    center: float = 0.0
    scale: float = 1.0
    positive_only: bool = False

    def contribution(self, value: float | None) -> float:
        if value is None:
            return 0.0
        scaled = (value - self.center) / self.scale
        if self.positive_only:
            scaled = max(scaled, 0.0)
        return self.weight * scaled


DEFAULT_FEATURE_RULES = (
    FeatureRule("age", 0.70, center=50.0, scale=10.0),
    FeatureRule("male", 0.35),
    FeatureRule("bmi", 0.25, center=24.0, scale=4.0, positive_only=True),
    FeatureRule("sbp", 0.45, center=120.0, scale=20.0, positive_only=True),
    FeatureRule("pulse_pressure", 0.15, center=40.0, scale=15.0, positive_only=True),
    FeatureRule("total_chol", 0.30, center=4.8, scale=1.0, positive_only=True),
    FeatureRule("ldl_c", 0.40, center=2.6, scale=0.8, positive_only=True),
    FeatureRule("hdl_c_low", 0.25),
    FeatureRule("triglyceride", 0.20, center=1.7, scale=0.6, positive_only=True),
    FeatureRule("fasting_glucose", 0.25, center=5.6, scale=1.5, positive_only=True),
    FeatureRule("glucose", 0.20, center=6.1, scale=1.5, positive_only=True),
    FeatureRule("hba1c", 0.25, center=6.5, scale=1.0, positive_only=True),
    FeatureRule("creatinine", 0.20, center=80.0, scale=30.0, positive_only=True),
    FeatureRule("uric_acid", 0.10, center=360.0, scale=60.0, positive_only=True),
    FeatureRule("bun", 0.10, center=6.0, scale=2.0, positive_only=True),
    FeatureRule("smoker", 0.60),
    FeatureRule("diabetes", 0.70),
    FeatureRule("hypertension", 0.45),
    FeatureRule("ckd", 0.55),
    FeatureRule("atrial_fibrillation", 0.30),
    FeatureRule("family_history_chd", 0.35),
    FeatureRule("chest_pain_visit_last_year", 0.65),
    FeatureRule("ecg_abnormal", 0.65),
    FeatureRule("carotid_ultrasound_abnormal", 0.35),
    FeatureRule("antihypertensive_use", 0.10),
    FeatureRule("lipid_lowering_use", 0.05),
    FeatureRule("antiplatelet_use", 0.10),
    FeatureRule("statin_adherence_gap", 0.45),
    FeatureRule("follow_up_interrupted", 0.35),
    FeatureRule("outpatient_visits_12m", 0.08, center=3.0, scale=4.0, positive_only=True),
    FeatureRule("emergency_visits_12m", 0.25, center=0.0, scale=2.0, positive_only=True),
    FeatureRule("sbp_trend_6m", 0.15, center=0.0, scale=5.0, positive_only=True),
    FeatureRule("ldl_trend_6m", 0.10, center=0.0, scale=0.3, positive_only=True),
    FeatureRule("medication_adherence_rate", -0.40, center=0.80, scale=0.20),
)


@dataclass
class WeightedRiskModel:
    """Transparent score model used as a runnable prototype.

    This is not a clinically validated model. Replace the rules with fitted
    coefficients or a trained estimator after local data governance, validation,
    calibration, and ethics review are complete.
    """

    intercept: float = -8.00
    feature_rules: tuple[FeatureRule, ...] = DEFAULT_FEATURE_RULES
    version: str = "prototype-weighted-risk-v0.1"

    def logit(self, features: dict[str, float | None]) -> float:
        return self.intercept + sum(rule.contribution(features.get(rule.name)) for rule in self.feature_rules)

    def predict_proba(self, features: dict[str, float | None]) -> float:
        z = self.logit(features)
        return 1.0 / (1.0 + math.exp(-z))

    def contributions(self, features: dict[str, float | None]) -> list[tuple[str, float]]:
        values = [(rule.name, rule.contribution(features.get(rule.name))) for rule in self.feature_rules]
        return sorted(values, key=lambda item: item[1], reverse=True)

    def top_positive_contributors(self, features: dict[str, float | None], limit: int = 6) -> list[tuple[str, float]]:
        return [(name, value) for name, value in self.contributions(features) if value > 0][:limit]

    def save(self, path: str | Path) -> None:
        payload = {
            "intercept": self.intercept,
            "version": self.version,
            "feature_rules": [asdict(rule) for rule in self.feature_rules],
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> WeightedRiskModel:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        rules = tuple(FeatureRule(**item) for item in payload["feature_rules"])
        return cls(
            intercept=float(payload["intercept"]),
            feature_rules=rules,
            version=str(payload.get("version", "loaded-weighted-risk-model")),
        )
