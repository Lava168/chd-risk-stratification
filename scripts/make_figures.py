"""Generate model report figures with matplotlib + seaborn.

Figures are saved to outputs/figures/. Uses Chinese labels (Arial Unicode MS).
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

plt.rcParams["font.family"] = ["Arial Unicode MS", "Hiragino Sans GB", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", palette="deep")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from stage_c3_strongest_model import (
    FEATURES,
    _load_derived,
    _preprocessor,
    _tuned_models,
)

from chd_risk.config import RiskThresholds
from chd_risk.features import FEATURE_LABELS
from chd_risk.model_registry import load_bundle
from chd_risk.risk import classify_risk, tier_label

OUT = Path(__file__).resolve().parent.parent / "outputs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

MODEL_LABELS = {
    "logistic_regression": "Logistic 回归",
    "random_forest": "随机森林",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
}
COLORS = {
    "logistic_regression": "#4C72B0",
    "random_forest": "#55A868",
    "xgboost": "#C44E52",
    "lightgbm": "#8172B2",
    "ensemble": "#CCB974",
}


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
    axes[0].set_title("患者年龄分布（按性别）", fontsize=12)
    axes[0].set_xlabel("年龄"); axes[0].set_ylabel("人数")
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, ["男", "女"], title="性别")

    feats = ["diabetes", "hypertension", "ecg_abnormal", "smoker", "has_any_lab", "has_lipids", "has_glucose", "has_renal"]
    labels = ["糖尿病", "高血压", "心电图异常", "吸烟", "有任一检验", "有血脂检验", "有血糖检验", "有肾功能检验"]
    prevalence = [float(X[c].fillna(0).mean()) for c in feats]
    bars = axes[1].barh(labels, prevalence, color=sns.color_palette("deep", len(labels))[::-1])
    axes[1].set_title("特征阳性/可获得率", fontsize=12)
    axes[1].set_xlabel("比例")
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
    ax.plot([0, 1], [0, 1], ls="--", color="gray", lw=1, label="随机猜测")
    ax.set_xlabel("假阳性率 (1-特异度)"); ax.set_ylabel("真阳性率 (灵敏度)")
    ax.set_title(f"时间外验证 ROC 曲线（n_test={len(y_te)}, 阳性 {int(y_te.sum())}）", fontsize=12)
    ax.legend(loc="lower right", fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / "fig2_roc_temporal.png", dpi=160); plt.close(fig)


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
    # left: temporal test calibration
    for name, model in models.items():
        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]
        pts = _calibration_curve(y_te.to_numpy(), proba)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        axes[0].plot(xs, ys, marker="o", lw=1.5, ms=5, color=COLORS[name], label=MODEL_LABELS[name])
    axes[0].plot([0, 1], [0, 1], ls="--", color="gray", lw=1)
    axes[0].set_xlabel("预测概率"); axes[0].set_ylabel("实际事件率")
    axes[0].set_title("校准曲线（时间外，n=37）", fontsize=12)
    axes[0].legend(fontsize=9); axes[0].set_xlim(0, 1); axes[0].set_ylim(0, 1)

    # right: 5-fold OOF calibration (more points)
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
    axes[1].set_xlabel("预测概率"); axes[1].set_ylabel("实际事件率")
    axes[1].set_title("校准曲线（测试集 5 折 OOF）", fontsize=12)
    axes[1].legend(fontsize=9); axes[1].set_xlim(0, 1); axes[1].set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(OUT / "fig3_calibration.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 4
def fig4_shap(X, y, features):
    import shap
    pre = _preprocessor(features).fit(X, y)
    Xt = pre.transform(X)
    import xgboost
    model = xgboost.XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8, random_state=42,
                                  eval_metric="logloss").fit(Xt, y)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(Xt)
    if isinstance(values, list):
        values = values[1]
    mean_abs = np.abs(values).mean(axis=0)
    order = np.argsort(mean_abs)
    labels = [FEATURE_LABELS.get(features[i], features[i]) for i in order]
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    colors = sns.color_palette("crest", len(order))
    ax.barh(labels, mean_abs[order], color=colors)
    ax.set_xlabel("平均 |SHAP| (对预测概率的贡献)")
    ax.set_title("XGBoost 全局特征重要性（SHAP）", fontsize=13)
    fig.tight_layout(); fig.savefig(OUT / "fig4_shap.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 5
def fig5_tiers(df):
    bundle = load_bundle()
    if bundle is None:
        print("no bundle, skip fig5")
        return
    from chd_risk.schema import PatientSnapshot
    probs, tiers = [], []
    for record in df.to_dict("records"):
        snapshot = PatientSnapshot.from_mapping(record)
        prob = bundle.predict_proba(snapshot)
        thresholds = RiskThresholds(*bundle.tier_thresholds) if bundle.tier_thresholds else None
        tier = classify_risk(prob, thresholds) if thresholds else classify_risk(prob)
        probs.append(prob); tiers.append(tier_label(tier))
    scored = pd.DataFrame({"tier": tiers, "prob": probs, "outcome": df["outcome_hospitalized"].values})

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    order = ["低危", "中危", "高危", "极高危"]
    counts = scored["tier"].value_counts().reindex(order).fillna(0).astype(int)
    colors = ["#55A868", "#4C72B0", "#C44E52", "#8C1D18"]
    bars = axes[0].bar(order, counts.values, color=colors)
    axes[0].set_title("最强模型分层人数分布", fontsize=12)
    axes[0].set_ylabel("人数")
    for bar, v in zip(bars, counts.values):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, str(v), ha="center")

    rates = scored.groupby("tier")["outcome"].mean().reindex(order)
    bars2 = axes[1].bar(order, rates.values * 100, color=colors)
    axes[1].axhline(scored["outcome"].mean() * 100, ls="--", color="gray", lw=1, label="总体住院率")
    axes[1].set_title("各档实际住院率（模型分层的验证）", fontsize=12)
    axes[1].set_ylabel("实际住院率 (%)"); axes[1].set_ylim(0, 110)
    axes[1].legend(fontsize=9)
    for bar, v in zip(bars2, rates.values):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{v:.0%}", ha="center")
    fig.tight_layout(); fig.savefig(OUT / "fig5_tiers.png", dpi=160); plt.close(fig)


# ---------------------------------------------------------------- fig 6
def fig6_model_compare():
    with open("outputs/stage_c3/strongest_outcome_hospitalized.json", encoding="utf-8") as handle:
        report = json.load(handle)
    names = list(report["models"])
    means = [report["models"][n]["cv"]["auc_mean"] for n in names]
    lows = [report["models"][n]["cv"]["auc_95ci_low"] for n in names]
    highs = [report["models"][n]["cv"]["auc_95ci_high"] for n in names]
    if report.get("ensemble"):
        names.append("集成")
        means.append(report["ensemble"]["cv"]["auc_mean"])
        lows.append(report["ensemble"]["cv"]["auc_95ci_low"])
        highs.append(report["ensemble"]["cv"]["auc_95ci_high"])

    labels = [MODEL_LABELS.get(n, n) for n in names]
    colors = [COLORS.get(n, "#CCB974") for n in names]
    yerr = np.array([[means[i] - lows[i], highs[i] - means[i]] for i in range(len(means))]).T
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.bar(labels, means, yerr=yerr, capsize=6, color=colors, alpha=0.85, error_kw={"ecolor": "black"})
    ax.set_ylabel("10×5 重复分层 CV AUC")
    ax.set_ylim(0.7, 1.0)
    ax.set_title("模型对比：CV AUC（95% 置信区间）", fontsize=13)
    for i, m in enumerate(means):
        ax.text(i, m + 0.008, f"{m:.3f}", ha="center", fontsize=10)
    ax.axhline(0.8, ls="--", color="gray", lw=1, label="AUC=0.8 参考线")
    ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "fig6_model_compare.png", dpi=160); plt.close(fig)


def main():
    df, X, y, features = _load_data()
    print("features:", len(features))
    X_tr, X_te, y_tr, y_te = _temporal_split(df, X, y)
    tuned = _tuned_models(42, X, y, features)

    fig1_cohort(df, X)
    print("fig1 ok")
    fig2_roc_temporal(tuned, X_tr, X_te, y_tr, y_te)
    print("fig2 ok")
    fig3_calibration(tuned, X_tr, X_te, y_tr, y_te)
    print("fig3 ok")
    fig4_shap(X, y, features)
    print("fig4 ok")
    fig5_tiers(df)
    print("fig5 ok")
    fig6_model_compare()
    print("fig6 ok")
    print("saved to", OUT)


if __name__ == "__main__":
    main()
