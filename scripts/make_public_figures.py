"""Generate report figures for the public multi-dataset validation.

Reads outputs/stage_public/*_summary.json (produced by
stage_public_multi_validation.py) and writes:
- outputs/figures/fig2_public_overview.png   sample size + event rate
- outputs/figures/fig3_public_auc_compare.png test-set AUC by model & dataset
- outputs/figures/fig4_public_roc.png        ROC curves per dataset

Run after stage_public_multi_validation.py so the JSON summaries exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.direction": "out",
    "ytick.direction": "out",
})

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
# Nature-skill palette (Yuan1z0825/nature-skills, nature-figure DEFAULT_COLORS):
# blue_main #0F4D92, green_3 #8BCF8B, red_strong #B64342, teal #42949E,
# violet #9A4D8E, neutral_light #CFCECE
PALETTE = ["#0F4D92", "#8BCF8B", "#B64342", "#42949E", "#9A4D8E", "#CFCECE"]


def load_reports() -> dict[str, dict]:
    reports = {}
    for path in SUMMARIES:
        reports[path.stem.replace("_summary", "")] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def _short_name(dataset: str) -> str:
    if "Cleveland" in dataset:
        return "Cleveland"
    if "Statlog" in dataset:
        return "Statlog"
    if "Hungarian" in dataset:
        return "Hungarian"
    if "SAheart" in dataset:
        return "SAheart"
    return dataset


def fig2_overview(reports: dict[str, dict]) -> None:
    short = [_short_name(r["dataset"]) for r in reports.values()]
    n_rows = [r["n_rows"] for r in reports.values()]
    event_rate = [r["event_rate"] * 100 for r in reports.values()]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    fig.subplots_adjust(wspace=0.32)

    bars = axes[0].bar(short, n_rows, width=0.55, color=PALETTE[0], alpha=0.95)
    for b, v in zip(bars, n_rows):
        axes[0].text(b.get_x() + b.get_width() / 2, v + max(n_rows) * 0.02, str(v),
                     ha="center", va="bottom", fontsize=10)
    axes[0].set_title("Sample size by dataset", fontsize=12.5)
    axes[0].set_ylabel("Subjects (n)", fontsize=11)
    axes[0].set_ylim(0, max(n_rows) * 1.22)
    axes[0].tick_params(axis="x", labelsize=10.5)
    axes[0].tick_params(axis="y", labelsize=10)

    bars = axes[1].bar(short, event_rate, width=0.55, color=PALETTE[4], alpha=0.95)
    for b, v in zip(bars, event_rate):
        axes[1].text(b.get_x() + b.get_width() / 2, v + max(event_rate) * 0.02,
                     f"{v:.1f}%", ha="center", va="bottom", fontsize=10)
    axes[1].set_title("Positive event rate by dataset", fontsize=12.5)
    axes[1].set_ylabel("Event rate (%)", fontsize=11)
    axes[1].set_ylim(0, max(event_rate) * 1.22)
    axes[1].tick_params(axis="x", labelsize=10.5)
    axes[1].tick_params(axis="y", labelsize=10)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(direction="out")
    fig.savefig(OUT / "fig2_public_overview.png", dpi=160)
    plt.close(fig)
    print("fig2_public_overview ok")


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
                      color=PALETTE[i], alpha=0.95)
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
    fig.savefig(OUT / "fig3_public_auc_compare.png", dpi=160)
    plt.close(fig)
    print("fig3_public_auc_compare ok")


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
    fig.savefig(OUT / "fig4_public_roc.png", dpi=160)
    plt.close(fig)
    print("fig4_public_roc ok")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    reports = load_reports()
    if not reports:
        raise SystemExit(
            "No summaries found in outputs/stage_public/. Run "
            "scripts/stage_public_multi_validation.py first."
        )
    fig2_overview(reports)
    fig8_auc_compare(reports)
    fig9_roc(reports)
    print("public validation figures written to outputs/figures/")


if __name__ == "__main__":
    main()
