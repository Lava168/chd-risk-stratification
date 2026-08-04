"""Stage C3: build the strongest deployable model from the local research table.

Design for honest evaluation:
- Leakage guard: utilization features (n_visits, hosp_count, ever_hospitalized)
  are EXCLUDED; outcome_hospitalized must not be predicted from visit counts.
- All models are tuned with inner 5-fold GridSearchCV on the full data, then
  evaluated with 10x repeated stratified 5-fold CV (mean AUC + 95% CI) and a
  time-external (temporal) split.
- Every model uses the same impute+scale preprocessor so results reflect the
  actually deployable pipeline; the winner is saved as the scoring bundle.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import lightgbm
import numpy as np
import pandas as pd
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from chd_risk.features import FEATURE_LABELS, build_feature_vector
from chd_risk.model_registry import TrainedModelBundle
from chd_risk.schema import PatientSnapshot

# Leakage-free derived features (research table columns that map to snapshot fields).
FEATURES = [
    "age", "male", "sbp", "pulse_pressure",
    "total_chol", "ldl_c", "hdl_c_low", "triglyceride",
    "fasting_glucose", "glucose", "hba1c",
    "creatinine", "uric_acid", "bun",
    "has_lipids", "has_glucose", "has_renal", "has_any_lab",
    "smoker", "diabetes", "hypertension", "ecg_abnormal",
]


def _load_derived(csv_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv_path, keep_default_na=False, na_values=[""])
    records = df.to_dict("records")
    rows = []
    for record in records:
        try:
            snapshot = PatientSnapshot.from_mapping(record)
        except ValueError:
            continue
        rows.append(build_feature_vector(snapshot))
    derived = pd.DataFrame(rows)
    derived = derived.reindex(sorted(derived.columns), axis=1)
    derived = derived.loc[:, derived.notna().any()]
    return derived, df


def _preprocessor(features: list[str]):
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]),
                features,
            )
        ]
    )


def _base_models(seed: int, features: list[str]) -> dict[str, dict]:
    return {
        "logistic_regression": {
            "model": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed),
            "params": {"model__C": [0.05, 0.2, 1.0, 5.0]},
        },
        "random_forest": {
            "model": RandomForestClassifier(
                n_estimators=600, class_weight="balanced_subsample", random_state=seed, n_jobs=1
            ),
            "params": {
                "model__max_depth": [3, 5, None],
                "model__min_samples_leaf": [2, 6, 12],
            },
        },
    }


def _tuned_models(seed: int, X, y, features: list[str]) -> dict[str, object]:
    pre = _preprocessor(features)
    candidates = _base_models(seed, features)
    scale_pos = float(np.sum(y == 0) / max(np.sum(y == 1), 1))
    candidates["xgboost"] = {
        "model": xgboost.XGBClassifier(
            n_estimators=400, subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=scale_pos, eval_metric="logloss",
            random_state=seed, n_jobs=1,
        ),
        "params": {
            "model__max_depth": [2, 3, 4],
            "model__learning_rate": [0.02, 0.05, 0.1],
            "model__reg_lambda": [1.0, 10.0],
        },
    }
    candidates["lightgbm"] = {
        "model": lightgbm.LGBMClassifier(
            n_estimators=400, subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=scale_pos, random_state=seed, verbose=-1, n_jobs=1,
        ),
        "params": {
            "model__max_depth": [2, 3, 4],
            "model__learning_rate": [0.02, 0.05, 0.1],
            "model__reg_lambda": [1.0, 10.0],
        },
    }

    tuned: dict[str, object] = {}
    for name, cfg in candidates.items():
        pipeline = Pipeline([("pre", pre), ("model", cfg["model"])])
        search = GridSearchCV(
            pipeline, cfg["params"], cv=5, scoring="roc_auc", n_jobs=1, refit=True
        )
        search.fit(X, y)
        tuned[name] = search.best_estimator_
    return tuned


def _evaluate(model, X, y, repeats=10, seed=42) -> dict[str, float]:
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=seed)
    aucs, briers = [], []
    for train_idx, test_idx in cv.split(X, y):
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        proba = model.predict_proba(X.iloc[test_idx])[:, 1]
        if len(set(y.iloc[test_idx])) > 1:
            aucs.append(roc_auc_score(y.iloc[test_idx], proba))
        briers.append(brier_score_loss(y.iloc[test_idx], proba))
    aucs = np.asarray(aucs)
    return {
        "auc_mean": round(float(aucs.mean()), 4),
        "auc_95ci_low": round(float(np.percentile(aucs, 2.5)), 4),
        "auc_95ci_high": round(float(np.percentile(aucs, 97.5)), 4),
        "brier_mean": round(float(np.mean(briers)), 4),
        "n_folds": len(aucs),
    }


def _temporal_evaluate(model, X, y, df, date_col="index_date") -> dict[str, float]:
    order = pd.to_datetime(df[date_col], errors="coerce").argsort(kind="stable")
    n_tr = int(len(df) * 0.85)
    tr, te = order[:n_tr], order[n_tr:]
    model.fit(X.iloc[tr], y.iloc[tr])
    proba = model.predict_proba(X.iloc[te])[:, 1]
    y_te = y.iloc[te]
    return {
        "auc": round(float(roc_auc_score(y_te, proba)), 4) if len(set(y_te)) > 1 else None,
        "brier": round(float(brier_score_loss(y_te, proba)), 4),
        "n_test": len(te),
        "events_test": int(y_te.sum()),
    }


def run(csv_path: str | Path, outcome_col: str, output_dir: Path, save_model: str | None) -> dict:
    derived, df = _load_derived(csv_path)
    features = [name for name in FEATURES if name in derived.columns]
    X = derived[features]
    y = df[outcome_col].astype(int).reset_index(drop=True)
    X = X.reset_index(drop=True)

    tuned = _tuned_models(42, X, y, features)

    report: dict = {
        "dataset": str(csv_path),
        "outcome_col": outcome_col,
        "n_rows": len(df),
        "n_events": int(y.sum()),
        "event_rate": round(float(y.mean()), 4),
        "features": [{"name": name, "label": FEATURE_LABELS.get(name, name)} for name in features],
        "models": {},
        "ensemble": None,
        "temporal": {},
        "leakage_guard": (
            "n_visits / hosp_count / ever_hospitalized are excluded as features; "
            "outcome must not be predicted from visit counts."
        ),
        "winner": None,
    }

    for name, model in tuned.items():
        cv = _evaluate(model, X, y)
        temporal = _temporal_evaluate(model, X, y, df)
        report["models"][name] = {"cv": cv, "temporal": temporal}
        print(f"  {name}: CV AUC {cv['auc_mean']:.3f} "
              f"({cv['auc_95ci_low']:.3f}-{cv['auc_95ci_high']:.3f}) | temporal AUC {temporal['auc']}")

    # Soft-voting ensemble of tuned XGB + LGBM + RF (trained inside each CV fold)
    tree_names = [name for name in ("xgboost", "lightgbm", "random_forest") if name in tuned]
    if len(tree_names) >= 2:
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
        aucs, briers = [], []
        for train_idx, test_idx in cv.split(X, y):
            probas = []
            for name in tree_names:
                tuned[name].fit(X.iloc[train_idx], y.iloc[train_idx])
                probas.append(tuned[name].predict_proba(X.iloc[test_idx])[:, 1])
            proba = np.mean(probas, axis=0)
            if len(set(y.iloc[test_idx])) > 1:
                aucs.append(roc_auc_score(y.iloc[test_idx], proba))
            briers.append(brier_score_loss(y.iloc[test_idx], proba))
        aucs = np.asarray(aucs)
        report["ensemble"] = {
            "members": tree_names,
            "cv": {
                "auc_mean": round(float(aucs.mean()), 4),
                "auc_95ci_low": round(float(np.percentile(aucs, 2.5)), 4),
                "auc_95ci_high": round(float(np.percentile(aucs, 97.5)), 4),
                "brier_mean": round(float(np.mean(briers)), 4),
            },
        }
        print(f"  ensemble({'+'.join(tree_names)}): CV AUC {aucs.mean():.3f} "
              f"({np.percentile(aucs,2.5):.3f}-{np.percentile(aucs,97.5):.3f})")

    # Winner: best single model by repeated-CV mean AUC
    winner = max(report["models"], key=lambda name: report["models"][name]["cv"]["auc_mean"])
    report["winner"] = winner
    report["winner_cv"] = report["models"][winner]["cv"]
    report["winner_temporal"] = report["models"][winner]["temporal"]

    if save_model:
        best_model = tuned[winner]
        pre = _preprocessor(features).fit(X, y)
        # Relative risk bands = score quartiles on the full training population.
        fitted = best_model.fit(X, y)
        train_scores = fitted.predict_proba(X)[:, 1]
        tier_thresholds = [round(float(v), 4) for v in np.percentile(train_scores, [25.0, 50.0, 75.0])]
        bundle = TrainedModelBundle(
            preprocessor=pre,
            model=fitted.named_steps["model"],
            feature_names=features,
            model_name=winner,
            metadata={
                "outcome_col": outcome_col,
                "data_provenance": "research-table",
                "stage": "c3-strongest",
                "cv_auc_mean": report["winner_cv"]["auc_mean"],
                "temporal_auc": report["winner_temporal"]["auc"],
                "tier_method": "score_quantiles",
                "tier_thresholds": tier_thresholds,
                "input": str(csv_path),
                "n_train": len(X),
            },
        )
        path = bundle.save(save_model)
        report["saved_model"] = {"path": str(path), "model_name": winner}
        report["tier_thresholds"] = tier_thresholds

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"strongest_{outcome_col}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stage C3: strongest deployable model from local research table.")
    parser.add_argument("--input", default="data/processed/research_table_local.csv")
    parser.add_argument("--outcome-col", default="outcome_hospitalized")
    parser.add_argument("--output-dir", default="outputs/stage_c3")
    parser.add_argument("--save-model", default="models/trained_model_bundle.joblib")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run(Path(args.input), args.outcome_col, Path(args.output_dir), args.save_model)
    print(f"\nWinner: {report['winner']} | CV AUC {report['winner_cv']['auc_mean']:.3f} "
          f"| temporal AUC {report['winner_temporal']['auc']}")
    print(f"Report -> {Path(args.output_dir) / f'strongest_{args.outcome_col}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
