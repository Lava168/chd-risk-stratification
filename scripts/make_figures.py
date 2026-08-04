"""Generate model report figures with matplotlib + seaborn (English labels).

Figures are saved to outputs/figures/.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from stage_c3_strongest_model import (
    FEATURES,
    _load_derived,
    _preprocessor,
    _tuned_models,
)

from chd_risk.config import RiskThresholds
from chd_risk.model_registry import load_bundle
from chd_risk.risk import classify_risk
from chd_risk.schema import PatientSnapshot

OUT = Path(__file__).resolve().parent.parent / "outputs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "ensemble": "Ensemble",
}
COLORS = {
    "logistic_regression": "#4C72B0",
    "random_forest": "#55A868",
    "xgboost": "#C44E52",
    "lightgbm": "#8172B2",
    "ensemble": "#CCB974",
}
FEATURE_EN = {
    "age": "Age", "male": "Male", "sbp": "SBP", "pulse_pressure": "Pulse pressure",
    "total_chol": "Total cholesterol", "ldl_c": "LDL-C", "hdl_c_low": "Low HDL-C",
    "triglyceride": "Triglycerides", "fasting_glucose": "Fasting glucose",
    "glucose": "Glucose", "hba1c": "HbA1c", "creatinine": "Creatinine",
    "uric_acid": "Uric acid", "bun": "BUN", "has_lipids": "Lipid labs done",
    "has_glucose": "Glucose labs done", "has_renal": "Renal labs done",
    "has_any_lab": "Any lab done", "smoker": "Smoker", "diabetes": "Diabetes",
    "hypertension": "Hypertension", "ecg_abnormal": "Abnormal ECG",
}
TIER_EN = {"低危": "Low", "中危": "Medium", "高危": "High", "极高危": "Very high"}


def _load_data():
    derived, df = _load_derived("data/processed/research_table_local.csv")
    features = [n for n in FEATURES if n in derived.columns]
    X = derived[features].reset_index(drop=True)
    y = df["outcome_hospitalized"].astype(int).reset_index(drop=True)
    return df, X, y, features


def _temporal_split(df, X, y):
    order = pd.to_datetime(df["index_date"], errors="coerce").argsort(kind="stable")
    n_tr = int(len(df) * 0.85)
    tr, te = order[:n_tr], order[n_tr:]
    return X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]


# ---------------------------------------------------------------- fig 1
def fig1_cohort(df, X):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    sns.histplot(
        data=df, x="age", hue="sex", bins=20, kde=True, ax=axes[0],
        palette={"male": "#4C72B0", "female": "#C44E52"},
    )
    axes[0].set_title("Patient age distribution by sex", fontsize=12)
    axes[0].set_xlabel("Age"); axes[0].set_ylabel("Count")
    handles, _ = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, ["Male", "Female"], title="Sex")

    feats = ["diabetes", "hypertension", "ecg_abnormal", "smoker", "has_any_lab", "has_lipids", "has_glucose", "has_renal"]
    labels_en = [FEATURE_EN[c] for c in feats]
    prevalence = [float(X[c].fillna(0).mean()) for c in feats]
    bars = axes[1].barh(labels_en, prevalence, color=sns.color_palette("deep", len(labels_en))[::-1])
    axes[1].set_title("Feature prevalence / availability", fontsize=12)
    axes[1].set_xlabel("Proportion")
    axes[1].set_xlim(0, 1)
    for bar, v in zip(bars, prevalence):
        axes[1].text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2, f"{v:.0%}", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_cohort.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- fig 2
def fig2_roc_temporal(models, X_tr, X_te, y_tr, y_te):
    from sklearn.metrics import roc_auc_score, roc_curve
    fig, ax = plt.subplots(figsize=(7.2, 6))
    for name, model in models.items():
        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]
        fpr, tpr, _ = roc_curve(y_te, proba)
        auc = roc_auc_score(y_te, proba)
        ax.plot(fpr, tpr, color=COLORS[name], lw=2, label=f"{MODEL_LABELS[name]} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="gray", lw=1, label="Random guess")
    ax.set_xlabel("False positive rate (1 - specificity)")
    ax.set_ylabel("True positive rate (sensitivity)")
    ax.set_title(f"ROC curves - temporal validation (n_test={len(y_te)}, events={int(y_te.sum())})", fontsize=12)
    ax.legend(loc="lower right", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "fig5_roc_temporal.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 3
def _calibration_curve(y_true, proba, bins=5):
    order = np.argsort(proba)
    edges = np.array_split(order, bins)
    points = []
    for idx in edges:
        if len(idx) < 2:
            continue
        points.append((float(np.mean(proba[idx])), float(np.mean(y_true[idx])), len(idx)))
    return points


def fig3_calibration(models, X_tr, X_te, y_tr, y_te):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for name, model in models.items():
        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]
        pts = _calibration_curve(y_te.to_numpy(), proba)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        axes[0].plot(xs, ys, marker="o", lw=1.5, ms=5, color=COLORS[name], label=MODEL_LABELS[name])
    axes[0].plot([0, 1], [0, 1], ls="--", color="gray", lw=1)
    axes[0].set_xlabel("Predicted probability"); axes[0].set_ylabel("Observed event rate")
    axes[0].set_title("Calibration - temporal holdout (n=37)", fontsize=12)
    axes[0].legend(fontsize=9); axes[0].set_xlim(0, 1); axes[0].set_ylim(0, 1)

    from sklearn.model_selection import StratifiedKFold
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    oof = {name: np.zeros(len(y_te)) * np.nan for name in models}
    oof_y = np.zeros(len(y_te))
    for tr_idx, te_idx in cv.split(X_te, y_te):
        for name, model in models.items():
            model.fit(X_te.iloc[tr_idx], y_te.iloc[tr_idx])
            oof[name][te_idx] = model.predict_proba(X_te.iloc[te_idx])[:, 1]
        oof_y[te_idx] = y_te.iloc[te_idx]
    for name in models:
        pts = _calibration_curve(oof_y, oof[name], bins=5)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        axes[1].plot(xs, ys, marker="o", lw=1.5, ms=5, color=COLORS[name], label=MODEL_LABELS[name])
    axes[1].plot([0, 1], [0, 1], ls="--", color="gray", lw=1)
    axes[1].set_xlabel("Predicted probability"); axes[1].set_ylabel("Observed event rate")
    axes[1].set_title("Calibration - test 5-fold OOF", fontsize=12)
    axes[1].legend(fontsize=9); axes[1].set_xlim(0, 1); axes[1].set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(OUT / "fig6_calibration.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 4
def fig4_shap(X, y, features):
    import shap
    pre = _preprocessor(features).fit(X, y)
    Xt = pre.transform(X)
    import xgboost
    model = xgboost.XGBClassifier(
        n_estimators=400, max_depth=3, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, eval_metric="logloss",
    ).fit(Xt, y)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(Xt)
    if isinstance(values, list):
        values = values[1]
    mean_abs = np.abs(values).mean(axis=0)
    order = np.argsort(mean_abs)
    labels = [FEATURE_EN.get(features[i], features[i]) for i in order]
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    colors = sns.color_palette("crest", len(order))
    ax.barh(labels, mean_abs[order], color=colors)
    ax.set_xlabel("Mean |SHAP| (contribution to predicted probability)")
    ax.set_title("XGBoost global feature importance (SHAP)", fontsize=13)
    fig.tight_layout(); fig.savefig(OUT / "fig7_shap.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 5
def fig5_tiers(df):
    bundle = load_bundle()
    if bundle is None:
        print("no bundle, skip fig5")
        return
    probs, tiers = [], []
    for record in df.to_dict("records"):
        snapshot = PatientSnapshot.from_mapping(record)
        prob = bundle.predict_proba(snapshot)
        thresholds = RiskThresholds(*bundle.tier_thresholds) if bundle.tier_thresholds else None
        tier = classify_risk(prob, thresholds) if thresholds else classify_risk(prob)
        probs.append(prob); tiers.append(TIER_EN.get(tier, tier))
    scored = pd.DataFrame({"tier": tiers, "prob": probs, "outcome": df["outcome_hospitalized"].values})

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    order = ["Low", "Medium", "High", "Very high"]
    counts = scored["tier"].value_counts().reindex(order).fillna(0).astype(int)
    colors = ["#55A868", "#4C72B0", "#C44E52", "#8C1D18"]
    bars = axes[0].bar(order, counts.values, color=colors)
    axes[0].set_title("Risk tier distribution (strongest model)", fontsize=12)
    axes[0].set_ylabel("Patients")
    for bar, v in zip(bars, counts.values):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, str(v), ha="center")

    rates = scored.groupby("tier")["outcome"].mean().reindex(order)
    bars2 = axes[1].bar(order, rates.values * 100, color=colors)
    axes[1].axhline(scored["outcome"].mean() * 100, ls="--", color="gray", lw=1, label="Overall hospitalization rate")
    axes[1].set_title("Observed hospitalization rate by tier", fontsize=12)
    axes[1].set_ylabel("Observed rate (%)"); axes[1].set_ylim(0, 110)
    axes[1].legend(fontsize=9)
    for bar, v in zip(bars2, rates.values):
        if np.isfinite(v):
            axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{v:.0%}", ha="center")
    fig.tight_layout(); fig.savefig(OUT / "fig9_tiers.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 6
def fig6_model_compare():
    with open("outputs/stage_c3/strongest_outcome_hospitalized.json", encoding="utf-8") as handle:
        report = json.load(handle)
    names = list(report["models"])
    means = [report["models"][n]["cv"]["auc_mean"] for n in names]
    lows = [report["models"][n]["cv"]["auc_95ci_low"] for n in names]
    highs = [report["models"][n]["cv"]["auc_95ci_high"] for n in names]
    if report.get("ensemble"):
        names.append("ensemble")
        means.append(report["ensemble"]["cv"]["auc_mean"])
        lows.append(report["ensemble"]["cv"]["auc_95ci_low"])
        highs.append(report["ensemble"]["cv"]["auc_95ci_high"])

    labels = [MODEL_LABELS.get(n, n) for n in names]
    colors = [COLORS.get(n, "#CCB974") for n in names]
    yerr = np.array([[means[i] - lows[i], highs[i] - means[i]] for i in range(len(means))]).T
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.bar(labels, means, yerr=yerr, capsize=6, color=colors, alpha=0.85, error_kw={"ecolor": "black"})
    ax.set_ylabel("10x5 repeated stratified CV AUC")
    ax.set_ylim(0.7, 1.0)
    ax.set_title("Model comparison: CV AUC (95% CI)", fontsize=13)
    for i, m in enumerate(means):
        ax.text(i, m + 0.008, f"{m:.3f}", ha="center", fontsize=10)
    ax.axhline(0.8, ls="--", color="gray", lw=1, label="AUC=0.8 reference")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "fig8_model_compare.png", dpi=160); plt.close(fig)


def main():
    df, X, y, features = _load_data()
    print("features:", len(features))
    X_tr, X_te, y_tr, y_te = _temporal_split(df, X, y)
    tuned = _tuned_models(42, X, y, features)

    fig1_cohort(df, X); print("fig1 ok")
    fig2_roc_temporal(tuned, X_tr, X_te, y_tr, y_te); print("fig2 ok")
    fig3_calibration(tuned, X_tr, X_te, y_tr, y_te); print("fig3 ok")
    fig4_shap(X, y, features); print("fig4 ok")
    fig5_tiers(df); print("fig5 ok")
    fig6_model_compare(); print("fig6 ok")
    print("saved to", OUT)


if __name__ == "__main__":
    main()
