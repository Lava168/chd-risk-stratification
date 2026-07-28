from __future__ import annotations

from dataclasses import dataclass

from .china_par import BaselineEstimate, china_par_proxy, normalize_china_par_score
from .config import ManagementPlan
from .features import FEATURE_LABELS, build_feature_vector
from .model import WeightedRiskModel
from .risk import classify_risk, management_plan, tier_label
from .schema import PatientSnapshot


@dataclass(frozen=True)
class RiskReason:
    feature: str
    label: str
    contribution: float


@dataclass(frozen=True)
class RiskAssessment:
    patient_id: str
    probability: float
    local_model_probability: float
    baseline_probability: float
    baseline_source: str
    baseline_note: str
    tier: str
    tier_label: str
    reasons: tuple[RiskReason, ...]
    plan: ManagementPlan

    def to_dict(self) -> dict:
        return {
            "patient_id": self.patient_id,
            "probability": round(self.probability, 4),
            "local_model_probability": round(self.local_model_probability, 4),
            "baseline_probability": round(self.baseline_probability, 4),
            "baseline_source": self.baseline_source,
            "baseline_note": self.baseline_note,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "reasons": [
                {
                    "feature": reason.feature,
                    "label": reason.label,
                    "contribution": round(reason.contribution, 4),
                }
                for reason in self.reasons
            ],
            "management_plan": {
                "owner": self.plan.owner,
                "follow_up_days": self.plan.follow_up_days,
                "actions": list(self.plan.actions),
                "referral": self.plan.referral,
            },
        }


def _baseline_estimate(snapshot: PatientSnapshot) -> BaselineEstimate:
    if snapshot.china_par_score is not None:
        return BaselineEstimate(
            probability=normalize_china_par_score(snapshot.china_par_score),
            source="china_par_input",
            note="Externally supplied China-PAR or locally recalibrated baseline score.",
        )
    return china_par_proxy(snapshot)


def assess_patient(
    snapshot: PatientSnapshot,
    model: WeightedRiskModel | None = None,
    blend_baseline_weight: float = 0.30,
) -> RiskAssessment:
    model = model or WeightedRiskModel()
    features = build_feature_vector(snapshot)
    local_probability = model.predict_proba(features)
    baseline = _baseline_estimate(snapshot)
    blend_baseline_weight = min(max(blend_baseline_weight, 0.0), 1.0)
    probability = (
        (1.0 - blend_baseline_weight) * local_probability
        + blend_baseline_weight * baseline.probability
    )

    tier = classify_risk(probability)
    contributors = model.top_positive_contributors(features)
    reasons = tuple(
        RiskReason(feature=name, label=FEATURE_LABELS.get(name, name), contribution=value)
        for name, value in contributors
    )
    return RiskAssessment(
        patient_id=snapshot.patient_id,
        probability=probability,
        local_model_probability=local_probability,
        baseline_probability=baseline.probability,
        baseline_source=baseline.source,
        baseline_note=baseline.note,
        tier=tier,
        tier_label=tier_label(tier),
        reasons=reasons,
        plan=management_plan(tier),
    )

