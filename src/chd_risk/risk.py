from __future__ import annotations

from .config import DEFAULT_THRESHOLDS, MANAGEMENT_PLANS, RISK_LABELS, RiskThresholds


def clamp_probability(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def classify_risk(probability: float, thresholds: RiskThresholds = DEFAULT_THRESHOLDS) -> str:
    probability = clamp_probability(probability)
    if probability < thresholds.low_max:
        return "low"
    if probability < thresholds.medium_max:
        return "medium"
    if probability < thresholds.high_max:
        return "high"
    return "very_high"


def tier_label(tier: str) -> str:
    return RISK_LABELS.get(tier, tier)


def management_plan(tier: str):
    return MANAGEMENT_PLANS[tier]

