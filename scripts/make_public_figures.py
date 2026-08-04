"""Generate report figures for the public multi-dataset validation.

Reads outputs/stage_public/*_summary.json (produced by
stage_public_multi_validation.py) and writes:
- outputs/figures/fig7_public_overview.png   sample size + event rate
- outputs/figures/fig8_public_auc_compare.png test-set AUC by model & dataset
- outputs/figures/fig9_public_roc.png        ROC curves per dataset

Run after stage_public_multi_validation.py so the JSON summaries exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SUMMARIES = sorted((ROOT / "outputs" / "stage_public").glob("*_summary.json"))
OUT = ROOT / "outputs" / "figures"

MODEL_ORDER = ["logistic_regression", "random_forest", "xgboost", "lightgbm"]
MODEL_SHORT = {
    "logistic_regression": "Logistic",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
}
PALETTE = ["#1f6feb", "#2ea043", "#bf8700", "#8957e5"]


def load_reports() -> dict[str, dict]:
    reports = {}
    for path in SUMMARIES:
        reports[path.stem.replace("_summary", "")] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def fig7_overview(reports: dict[str, dict]) -> None:
    names = [r["dataset"] for r in reports.values()]
    short = [n.replace("UCI Heart Disease (", "").replace(")", "").replace(
        "ESL South African Heart Disease (SAheart)", "SAheart") for n in names]
    n_rows = [r["n_rows"] for r in reports.values()]
    event_rate = [r["event_rate"] * 100 for r in reports.values()]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    bars = axes[0].bar(short, n_rows, color=PALETTE[0], alpha=0.9)
    for b, v in zip(bars, n_rows):
        axes[0].text(b.get_x() + b.get_width() / 2, v + 4, str(v),
                     ha="center", fontsize=10)
    axes[0].set_title("Sample size by dataset", fontsize=12)
    axes[0].set_ylabel("Subjects (n)")
    axes[0].set_ylim(0, max(n_rows) * 1.18)

    bars = axes[1].bar(short, event_rate, color=PALETTE[3], alpha=0.9)
    for b, v in zip(bars, event_rate):
        axes[1].text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%",
                     ha="center", fontsize=10)
    axes[1].set_title("Positive event rate by dataset", fontsize=12)
    axes[1].set_ylabel("Event rate (%)")
    axes[1].set_ylim(0, max(event_rate) * 1.18)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig7_public_overview.png", dpi=160)
    plt.close(fig)
    print("fig7 ok")


def fig8_auc_compare(reports: dict[str, dict]) -> None:
    datasets = list(reports.keys())
    short = {
        "cleveland": "Cleveland",
        "statlog": "Statlog",
        "hungarian": "Hungarian",
        "saheart": "SAheart",
    }
    x = np.arange(len(datasets))
    width = 0.2

    fig, ax = plt.subplots(figsize=(9.5, 5))
    for i, model in enumerate(MODEL_ORDER):
        aucs = [
            reports[d]["models"].get(model, {}).get("auc", np.nan)
            for d in datasets
        ]
        bars = ax.bar(x + (i - 1.5) * width, aucs, width, label=MODEL_SHORT[model],
                      color=PALETTE[i], alpha=0.92)
        for b, v in zip(bars, aucs):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.3f}",
                        ha="center", fontsize=7.5, rotation=0)

    ax.set_xticks(x)
    ax.set_xticklabels([short[d] for d in datasets])
    ax.set_ylabel("Test-set AUC (80/20 stratified split)")
    ax.set_title("Model AUC across public datasets", fontsize=13)
    ax.set_ylim(0.6, 1.0)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig8_public_auc_compare.png", dpi=160)
    plt.close(fig)
    print("fig8 ok")


def fig9_roc(reports: dict[str, dict]) -> None:
    short = {
        "cleveland": "Cleveland (Logistic AUC 0.950)",
        "statlog": "Statlog (Logistic AUC 0.896)",
        "hungarian": "Hungarian (RF AUC 0.886)",
        "saheart": "SAheart (Logistic AUC 0.821)",
    }
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for i, name in enumerate(reports.keys()):
        r = reports[name]
        # logistic regression when available, otherwise best-AUC model
        if "logistic_regression" in r["models"]:
            roc = r["models"]["logistic_regression"]["roc"]
            auc = r["models"]["logistic_regression"]["auc"]
        else:
            best = max(r["models"], key=lambda m: r["models"][m]["auc"])
            roc = r["models"][best]["roc"]
            auc = r["models"][best]["auc"]
        ax.plot(roc["fpr"], roc["tpr"], color=PALETTE[i], lw=2,
                label=f"{short[name]} — AUC {auc:.3f}")
    ax.plot([0, 1], [0, 1], ls="--", color="#888", lw=1, label="Chance")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves on public datasets", fontsize=13)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig9_public_roc.png", dpi=160)
    plt.close(fig)
    print("fig9 ok")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reports = load_reports()
    if not reports:
        raise SystemExit(
            "No summaries found in outputs/stage_public/. Run "
            "scripts/stage_public_multi_validation.py first."
        )
    fig7_overview(reports)
    fig8_auc_compare(reports)
    fig9_roc(reports)
    print("public validation figures written to outputs/figures/")


if __name__ == "__main__":
    main()
