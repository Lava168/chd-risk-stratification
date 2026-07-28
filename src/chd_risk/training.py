from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .features import FEATURE_LABELS


BASE_FEATURES = [
    "age",
    "male",
    "bmi",
    "sbp",
    "pulse_pressure",
    "ldl_c",
    "hdl_c_low",
    "fasting_glucose",
    "smoker",
    "diabetes",
    "hypertension",
    "ckd",
    "atrial_fibrillation",
    "family_history_chd",
    "chest_pain_visit_last_year",
    "ecg_abnormal",
    "carotid_ultrasound_abnormal",
    "statin_adherence_gap",
    "follow_up_interrupted",
    "outpatient_visits_12m",
    "emergency_visits_12m",
    "sbp_trend_6m",
    "ldl_trend_6m",
    "medication_adherence_rate",
]


def _require_ml() -> dict[str, Any]:
    try:
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import brier_score_loss, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError("Install ML dependencies with: pip install -e '.[ml]'") from exc

    return {
        "pd": pd,
        "ColumnTransformer": ColumnTransformer,
        "RandomForestClassifier": RandomForestClassifier,
        "SimpleImputer": SimpleImputer,
        "LogisticRegression": LogisticRegression,
        "brier_score_loss": brier_score_loss,
        "roc_auc_score": roc_auc_score,
        "train_test_split": train_test_split,
        "Pipeline": Pipeline,
        "StandardScaler": StandardScaler,
    }


def train_tabular_models(
    csv_path: str | Path,
    outcome_col: str = "outcome_chd",
    output_report: str | Path = "outputs/training_report.json",
    test_size: float = 0.15,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train baseline sklearn models for research comparison.

    This function intentionally keeps the first implementation conservative.
    XGBoost, LightGBM, SHAP, DCA, NRI/IDI, and Cox modeling should be added after
    the team finalizes the research database and validation protocol.
    """

    ml = _require_ml()
    pd = ml["pd"]
    df = pd.read_csv(csv_path)
    if outcome_col not in df.columns:
        raise ValueError(f"Missing outcome column: {outcome_col}")

    available_features = [name for name in BASE_FEATURES if name in df.columns]
    if not available_features:
        raise ValueError("No recognized feature columns were found")

    X = df[available_features]
    y = df[outcome_col].astype(int)
    X_train, X_test, y_train, y_test = ml["train_test_split"](
        X, y, test_size=test_size, random_state=random_state, stratify=y if y.nunique() > 1 else None
    )

    preprocessor = ml["ColumnTransformer"](
        transformers=[
            (
                "numeric",
                ml["Pipeline"](
                    steps=[
                        ("imputer", ml["SimpleImputer"](strategy="median")),
                        ("scaler", ml["StandardScaler"]()),
                    ]
                ),
                available_features,
            )
        ]
    )

    candidates = {
        "logistic_regression": ml["Pipeline"](
            steps=[
                ("preprocessor", preprocessor),
                ("model", ml["LogisticRegression"](max_iter=1000, class_weight="balanced")),
            ]
        ),
        "random_forest": ml["Pipeline"](
            steps=[
                ("preprocessor", preprocessor),
                (
                    "model",
                    ml["RandomForestClassifier"](
                        n_estimators=300,
                        min_samples_leaf=20,
                        class_weight="balanced_subsample",
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }

    report = {
        "input": str(csv_path),
        "outcome_col": outcome_col,
        "features": [{"name": name, "label": FEATURE_LABELS.get(name, name)} for name in available_features],
        "models": {},
        "limitations": [
            "Internal demo split only; prefer temporal external validation for deployment.",
            "Calibration, DCA, NRI/IDI, SHAP, and clinical review are required before use.",
        ],
    }
    for name, pipeline in candidates.items():
        pipeline.fit(X_train, y_train)
        probabilities = pipeline.predict_proba(X_test)[:, 1]
        report["models"][name] = {
            "auc": float(ml["roc_auc_score"](y_test, probabilities)) if len(set(y_test)) > 1 else None,
            "brier_score": float(ml["brier_score_loss"](y_test, probabilities)),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
        }

    output_report = Path(output_report)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

