"""Trained-model registry: persist a fitted model bundle and use it for scoring.

A bundle contains the fitted preprocessor, the chosen classifier, the exact
derived-feature list it was trained on, and metadata (outcome, provenance,
threshold). Scoring falls back to the hand-tuned WeightedRiskModel when no
trained bundle is available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib

from .features import FEATURE_LABELS, build_feature_vector
from .schema import PatientSnapshot

DEFAULT_MODEL_PATH = Path("models/trained_model_bundle.joblib")


class TrainedModelBundle:
    """Serializable fitted-model bundle used by the scoring chain."""

    def __init__(
        self,
        preprocessor: Any,
        model: Any,
        feature_names: list[str],
        model_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.preprocessor = preprocessor
        self.model = model
        self.feature_names = list(feature_names)
        self.model_name = model_name
        self.metadata = metadata or {}

    # ---- serialization ----
    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: str | Path) -> TrainedModelBundle:
        return joblib.load(path)

    # ---- scoring ----
    def _feature_row(self, snapshot: PatientSnapshot) -> dict[str, float | None]:
        full = build_feature_vector(snapshot)
        return {name: full.get(name) for name in self.feature_names}

    def predict_proba(self, snapshot: PatientSnapshot) -> float:
        row = self._feature_row(snapshot)
        import pandas as pd

        frame = pd.DataFrame([row], columns=self.feature_names)
        transformed = self.preprocessor.transform(frame)
        return float(self.model.predict_proba(transformed)[0, 1])

    def top_contributors(
        self, snapshot: PatientSnapshot, limit: int = 6
    ) -> list[tuple[str, float]]:
        """Per-patient top positive contributors (SHAP for trees, coef for linear)."""
        import numpy as np
        import pandas as pd

        row = self._feature_row(snapshot)
        frame = pd.DataFrame([row], columns=self.feature_names)
        transformed = self.preprocessor.transform(frame)

        name = self.model_name
        try:
            if name in {"logistic_regression", "logistic"} and hasattr(self.model, "coef_"):
                coefs = np.asarray(self.model.coef_).reshape(-1)
                scaled = np.asarray(transformed).reshape(-1)
                contributions = coefs * scaled
            else:
                import shap

                explainer = shap.TreeExplainer(self.model)
                values = explainer.shap_values(transformed)
                if isinstance(values, list):
                    values = values[1]
                contributions = np.asarray(values).reshape(-1)
        except Exception:  # noqa: BLE001 - fall back to raw coefficients
            if hasattr(self.model, "coef_"):
                contributions = np.asarray(self.model.coef_).reshape(-1)
            else:
                contributions = np.zeros(len(self.feature_names))

        # Do not present features whose raw value is missing as "reasons": their
        # SHAP/contribution comes from median imputation, not patient evidence.
        raw = self._feature_row(snapshot)
        available = {name for name, value in raw.items() if value is not None}
        scored = sorted(
            zip(self.feature_names, contributions.tolist()),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            (name, value) for name, value in scored
            if value > 0 and name in available
        ][:limit]

    @property
    def tier_thresholds(self) -> list[float] | None:
        thresholds = self.metadata.get("tier_thresholds")
        if isinstance(thresholds, (list, tuple)) and len(thresholds) == 3:
            return [float(value) for value in thresholds]
        return None

    def describe(self) -> str:
        meta = self.metadata
        outcome = meta.get("outcome_col", "?")
        provenance = meta.get("data_provenance", "?")
        return (
            f"trained:{self.model_name} (outcome={outcome}, "
            f"provenance={provenance}, features={len(self.feature_names)})"
        )


_bundle_cache: TrainedModelBundle | None = None
_bundle_path_used: str | None = None


def resolve_model_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("CHD_RISK_MODEL_PATH")
    if env:
        return Path(env)
    return DEFAULT_MODEL_PATH


def load_bundle(path: str | Path | None = None, use_cache: bool = True) -> TrainedModelBundle | None:
    """Load the trained bundle; returns None when it does not exist."""
    global _bundle_cache, _bundle_path_used
    resolved = resolve_model_path(str(path) if path else None)
    key = str(resolved)
    if use_cache and _bundle_cache is not None and _bundle_path_used == key:
        return _bundle_cache
    if not resolved.exists():
        _bundle_cache = None
        _bundle_path_used = key
        return None
    _bundle_cache = TrainedModelBundle.load(resolved)
    _bundle_path_used = key
    return _bundle_cache


def feature_label(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature)
