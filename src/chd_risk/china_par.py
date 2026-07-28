from __future__ import annotations

from dataclasses import dataclass

from .features import build_feature_vector
from .model import FeatureRule, WeightedRiskModel
from .schema import PatientSnapshot


CHINA_PAR_PROXY_RULES = (
    FeatureRule("age", 0.85, center=50.0, scale=10.0),
    FeatureRule("male", 0.25),
    FeatureRule("sbp", 0.45, center=120.0, scale=20.0, positive_only=True),
    FeatureRule("total_chol", 0.25, center=4.8, scale=1.0, positive_only=True),
    FeatureRule("hdl_c_low", 0.25),
    FeatureRule("smoker", 0.50),
    FeatureRule("diabetes", 0.60),
    FeatureRule("hypertension", 0.35),
    FeatureRule("bmi", 0.15, center=24.0, scale=4.0, positive_only=True),
    FeatureRule("family_history_chd", 0.25),
)


@dataclass(frozen=True)
class BaselineEstimate:
    probability: float
    source: str
    note: str


def normalize_china_par_score(score: float) -> float:
    """Accept China-PAR values entered as either 0-1 or 0-100."""
    if score > 1.0:
        score = score / 100.0
    return min(max(score, 0.0), 1.0)


def china_par_proxy(snapshot: PatientSnapshot) -> BaselineEstimate:
    """Return a transparent placeholder when official coefficients are absent.

    The grant proposal names China-PAR as a clinical baseline. This repository
    keeps that as an adapter boundary. Until the authorized equation and local
    recalibration coefficients are supplied, the proxy is only for software
    smoke tests and workflow demonstrations.
    """

    features = build_feature_vector(snapshot)
    features["total_chol"] = snapshot.total_chol
    probability = WeightedRiskModel(
        intercept=-5.50,
        feature_rules=CHINA_PAR_PROXY_RULES,
        version="china-par-adapter-proxy",
    ).predict_proba(features)
    return BaselineEstimate(
        probability=probability,
        source="china_par_proxy",
        note="Placeholder adapter for development; not a validated China-PAR calculation.",
    )
