from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .features import FEATURE_LABELS, build_feature_vector
from .model_registry import TrainedModelBundle
from .schema import PatientSnapshot


def _json_safe(value):
    """Recursively convert numpy/pandas scalars to JSON-serializable Python types."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):  # numpy scalars (np.float32/64, np.int64, ...)
        return _json_safe(value.item())
    if isinstance(value, float):
        return float(value)
    if isinstance(value, int):
        return int(value)
    return value


# Raw columns the research table must provide; derived features are computed
# from these in build_feature_vector (male, pulse_pressure, hdl_c_low, total_chol).
RAW_FEATURES = [
    "age",
    "sex",
    "bmi",
    "sbp",
    "dbp",
    "total_chol",
    "ldl_c",
    "hdl_c",
    "triglyceride",
    "fasting_glucose",
    "glucose",
    "hba1c",
    "creatinine",
    "uric_acid",
    "bun",
    "smoker",
    "diabetes",
    "hypertension",
    "ckd",
    "atrial_fibrillation",
    "family_history_chd",
    "chest_pain_visit_last_year",
    "ecg_abnormal",
    "carotid_ultrasound_abnormal",
    "antihypertensive_use",
    "lipid_lowering_use",
    "antiplatelet_use",
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

    extras: dict[str, Any] = {}
    for name, import_name in (
        ("xgboost", "xgboost"),
        ("lightgbm", "lightgbm"),
        ("shap", "shap"),
    ):
        try:
            extras[name] = __import__(import_name)
        except Exception as exc:  # noqa: BLE001 - pragma: no cover - optional extras
            # Not only ModuleNotFoundError: macOS wheels may fail to load their
            # OpenMP runtime (libomp), raising XGBoostError/OSError on import.
            extras[name] = None
            extras[f"{name}_import_error"] = f"{type(exc).__name__}: {exc}"

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
        **extras,
    }


def _derive_feature_frame(pd, records: list[dict], raw_features: list[str]) -> Any:
    """Build a DataFrame of derived model features from raw research-table rows.

    This mirrors build_feature_vector so training uses the exact same feature
    definitions as scoring (male, pulse_pressure, hdl_c_low, total_chol, ...).
    """
    rows = []
    for record in records:
        try:
            snapshot = PatientSnapshot.from_mapping(record)
        except ValueError:
            continue
        rows.append(build_feature_vector(snapshot))
    return pd.DataFrame(rows)


def _optimal_threshold(y_true, probabilities, low=0.02, high=0.98, steps=97):
    """Pick the probability threshold maximizing Youden's J on the TRAIN set."""
    best_t, best_j = 0.5, -1.0
    for step in range(steps):
        threshold = low + (high - low) * step / (steps - 1)
        predicted = [1 if p >= threshold else 0 for p in probabilities]
        tp = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 1)
        tn = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 0)
        fp = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 1)
        fn = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 0)
        sensitivity = tp / (tp + fn) if tp + fn else 0.0
        specificity = tn / (tn + fp) if tn + fp else 0.0
        youden = sensitivity + specificity - 1.0
        if youden > best_j:
            best_j, best_t = youden, threshold
    return round(best_t, 3)


def _binary_metrics(y_true: list[int], probabilities: list[float], threshold: float) -> dict[str, float]:
    predicted = [1 if p >= threshold else 0 for p in probabilities]
    tp = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 0)
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if precision + sensitivity else 0.0
    return {
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
    }


def _calibration_table(y_true: list[int], probabilities: list[float]) -> list[dict[str, Any]]:
    paired = sorted(zip(probabilities, y_true), reverse=True)
    n = len(paired)
    table = []
    bin_size = max(n // 10, 1)
    for index in range(0, n, bin_size):
        chunk = paired[index : index + bin_size]
        if not chunk:
            continue
        mean_pred = sum(p for p, _ in chunk) / len(chunk)
        observed = sum(y for _, y in chunk) / len(chunk)
        table.append(
            {
                "decile": len(table) + 1,
                "n": len(chunk),
                "mean_predicted": round(mean_pred, 4),
                "observed_rate": round(observed, 4),
            }
        )
    return table


def train_tabular_models(
    csv_path: str | Path,
    outcome_col: str = "outcome_chd",
    output_report: str | Path = "outputs/training_report.json",
    test_size: float = 0.15,
    random_state: int = 42,
    split: str = "random",
    threshold: float = 0.10,
    date_col: str = "index_date",
    save_model: str | None = "models/trained_model_bundle.joblib",
) -> dict[str, Any]:
    """Train baseline sklearn models for research comparison.

    Random split is used by default; pass split="temporal" (sorts by date_col,
    default index_date) for a time-external-style validation split. Features are
    derived from raw research-table columns with the same rules as scoring.

    When save_model is set, the best-AUC model on the test split is persisted as
    a TrainedModelBundle (preprocessor + model + feature list + metadata) that the
    scoring chain (score-one/score-csv/API) loads and uses.
    """

    ml = _require_ml()
    pd = ml["pd"]

    df = pd.read_csv(csv_path)
    if outcome_col not in df.columns:
        raise ValueError(f"Missing outcome column: {outcome_col}")

    raw_features = [name for name in RAW_FEATURES if name in df.columns]
    if not raw_features:
        raise ValueError("No recognized feature columns were found")

    # Patient-level one-row-per-person guard.
    if "patient_id" in df.columns and df["patient_id"].duplicated().any():
        raise ValueError("Duplicate patient_id rows found; build one row per patient first.")

    records = df.to_dict("records")
    derived = _derive_feature_frame(pd, records, raw_features)
    derived = derived.reindex(sorted(derived.columns), axis=1)
    # Drop features with no observed values at all (e.g. labs absent from this export);
    # they would otherwise be imputed to a constant and add noise.
    derived = derived.loc[:, derived.notna().any()]
    feature_names = list(derived.columns)

    y = df[outcome_col].astype(int).tolist()
    n_events = int(sum(y))
    n_rows = len(y)

    if split == "temporal":
        if date_col not in df.columns:
            raise ValueError(f"split='temporal' requires a '{date_col}' column")
        order = pd.to_datetime(df[date_col], errors="coerce").argsort(kind="stable")
        n_train = int(n_rows * (1.0 - test_size))
        train_idx = order[:n_train]
        test_idx = order[n_train:]
        X_train, X_test = derived.iloc[train_idx], derived.iloc[test_idx]
        y_train, y_test = [y[i] for i in train_idx], [y[i] for i in test_idx]
        split_desc = f"temporal by {date_col} (earliest {n_train} train / latest {n_rows - n_train} test)"
    else:
        X_train, X_test, y_train, y_test = ml["train_test_split"](
            derived, y, test_size=test_size, random_state=random_state,
            stratify=y if n_events not in (0, n_rows) else None,
        )
        split_desc = f"random split (seed {random_state})"

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
                feature_names,
            )
        ]
    )
    X_train_t = preprocessor.fit_transform(X_train)
    X_test_t = preprocessor.transform(X_test)

    candidates: dict[str, Any] = {
        "logistic_regression": ml["LogisticRegression"](max_iter=1000, class_weight="balanced", random_state=random_state),
        "random_forest": ml["RandomForestClassifier"](
            n_estimators=300, min_samples_leaf=20,
            class_weight="balanced_subsample", random_state=random_state,
        ),
    }
    if ml["xgboost"] is not None:
        candidates["xgboost"] = ml["xgboost"].XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=max(sum(y_train) / max(len(y_train) - sum(y_train), 1), 1.0),
            eval_metric="logloss", random_state=random_state,
        )
    if ml["lightgbm"] is not None:
        candidates["lightgbm"] = ml["lightgbm"].LGBMClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=max(sum(y_train) / max(len(y_train) - sum(y_train), 1), 1.0),
            random_state=random_state, verbose=-1,
        )

    is_synthetic = "synthetic" in str(csv_path).lower()
    report: dict[str, Any] = {
        "input": str(csv_path),
        "outcome_col": outcome_col,
        "data_provenance": "synthetic-demo" if is_synthetic else "research-table",
        "n_rows": n_rows,
        "n_events": n_events,
        "event_rate": round(n_events / n_rows, 4) if n_rows else None,
        "split": split_desc,
        "test_size": test_size,
        "features": [{"name": name, "label": FEATURE_LABELS.get(name, name)} for name in feature_names],
        "models": {},
        "calibration": {},
        "shap_top_features": None,
        "limitations": [
            "Internal split only; external/temporal validation with local data is required before deployment.",
            "Calibration, DCA, NRI/IDI, SHAP, and clinical review are required before clinical use.",
        ],
    }
    if is_synthetic:
        report["limitations"].insert(
            0,
            "SYNTHETIC DEMO ONLY: labels are derived from the prototype model itself, "
            "so all metrics are meaningless for evaluation. Use real de-identified research data.",
        )

    model_names = list(candidates)
    fitted: dict[str, Any] = {}
    for name in model_names:
        try:
            model = candidates[name].fit(X_train_t, y_train)
            fitted[name] = model
        except Exception as exc:  # noqa: BLE001 - fragile single-class fits
            report["models"][name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        probabilities = model.predict_proba(X_test_t)[:, 1]
        train_proba = model.predict_proba(X_train_t)[:, 1]
        # Classification optimization: threshold chosen on TRAIN by Youden's J.
        best_threshold = (
            _optimal_threshold(y_train, train_proba)
            if len(set(y_train)) > 1 else threshold
        )
        metrics: dict[str, Any] = {
            "auc": float(ml["roc_auc_score"](y_test, probabilities))
            if len(set(y_test)) > 1 else None,
            "brier_score": float(ml["brier_score_loss"](y_test, probabilities)),
            "n_train": len(X_train_t),
            "n_test": len(X_test_t),
            "optimal_threshold": best_threshold,
        }
        metrics.update(_binary_metrics(y_test, probabilities, threshold=best_threshold))
        report["models"][name] = metrics

    if fitted and len(set(y_test)) > 1:
        report["calibration"] = {
            name: _calibration_table(y_test, fitted[name].predict_proba(X_test_t)[:, 1])
            for name in fitted
        }

    # Probability calibration (Platt/sigmoid) for the best-AUC model on train;
    # fit on TRAIN only, evaluated on TEST, so there is no leakage.
    try:
        from sklearn.calibration import CalibratedClassifierCV

        best_name = max(
            fitted,
            key=lambda name: (
                report["models"][name].get("auc", 0.0)
                if report["models"][name].get("auc") is not None else 0.0
            ),
        )
        cal_model = CalibratedClassifierCV(
            fitted[best_name], method="sigmoid", cv=3
        ).fit(X_train_t, y_train)
        cal_proba = cal_model.predict_proba(X_test_t)[:, 1]
        report["calibration_evaluation"] = {
            "model": best_name,
            "auc_raw": report["models"][best_name]["auc"],
            "brier_raw": report["models"][best_name]["brier_score"],
            "brier_calibrated": round(
                float(ml["brier_score_loss"](y_test, cal_proba)), 4
            ),
            "auc_calibrated": round(
                float(ml["roc_auc_score"](y_test, cal_proba)), 4
            )
            if len(set(y_test)) > 1 else None,
            "note": "Platt sigmoid calibration fit on train only, evaluated on test.",
        }
    except Exception as exc:  # noqa: BLE001 - calibration may fail on tiny folds
        report["calibration_evaluation"] = {
            "error": f"{type(exc).__name__}: {exc}"
        }

    # SHAP explanation on the first fitted tree model (interpretability demo).
    shap_model = None
    shap_name = None
    for name in ("xgboost", "lightgbm", "random_forest"):
        if name in fitted:
            shap_model = fitted[name]
            shap_name = name
            break
    if shap_model is not None and ml["shap"] is not None:
        try:
            import numpy as np
            explainer = ml["shap"].TreeExplainer(shap_model)
            shap_values = explainer.shap_values(X_test_t)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # binary case
            mean_abs = np.abs(shap_values).mean(axis=0)
            ranked = sorted(
                zip(feature_names, mean_abs.tolist()),
                key=lambda item: item[1], reverse=True,
            )
            report["shap_top_features"] = {
                "model": shap_name,
                "mean_abs_shap": [
                    {"feature": name, "mean_abs_shap": round(value, 4)}
                    for name, value in ranked[:15]
                ],
            }
        except Exception as exc:  # noqa: BLE001
            report["shap_top_features"] = {"error": f"{type(exc).__name__}: {exc}"}

    if save_model and fitted:
        best_name = max(
            fitted,
            key=lambda name: (
                report["models"][name].get("auc", 0.0)
                if report["models"][name].get("auc") is not None else 0.0
            ),
        )
        # Tier cutpoints for the trained model: relative risk bands = training-score
        # quartiles (p25/p50/p75). The 5/10/20% absolute thresholds are designed for
        # rare-event CHD risk and do not fit high-prevalence outcomes like
        # hospitalization (63% here), where scores never reach a <5% band.
        tier_thresholds = None
        tier_method = "score_quantiles"
        try:
            train_scores = fitted[best_name].predict_proba(X_train_t)[:, 1]
            cutpoints = np.percentile(train_scores, [25.0, 50.0, 75.0])
            tier_thresholds = [round(float(value), 4) for value in cutpoints]
        except Exception:  # noqa: BLE001 - guard pathological fits
            tier_thresholds = None
        bundle = TrainedModelBundle(
            preprocessor=preprocessor,
            model=fitted[best_name],
            feature_names=feature_names,
            model_name=best_name,
            metadata={
                "outcome_col": outcome_col,
                "data_provenance": "synthetic-demo" if is_synthetic else "research-table",
                "n_train": len(X_train_t),
                "n_test": len(X_test_t),
                "test_auc": report["models"][best_name].get("auc"),
                "input": str(csv_path),
                "tier_thresholds": tier_thresholds,
                "tier_method": tier_method,
            },
        )
        bundle_path = bundle.save(save_model)
        report["saved_model"] = {
            "path": str(bundle_path),
            "model_name": best_name,
            "description": bundle.describe(),
        }

    output_report = Path(output_report)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(
        json.dumps(_json_safe(report), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return _json_safe(report)
