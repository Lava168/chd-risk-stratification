from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .assessment import assess_patient
from .quality import completeness, range_violations
from .schema import PatientSnapshot
from .synthetic import write_synthetic_csv
from .training import train_tabular_models


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(payload: dict, path: str | Path | None = None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def score_one(args: argparse.Namespace) -> None:
    snapshot = PatientSnapshot.from_mapping(_read_json(args.input))
    assessment = assess_patient(snapshot)
    _write_json(assessment.to_dict(), args.output)


def score_csv(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    scored = []
    for row in rows:
        assessment = assess_patient(PatientSnapshot.from_mapping(row))
        row.update(
            {
                "risk_probability": f"{assessment.probability:.4f}",
                "risk_tier": assessment.tier,
                "risk_tier_label": assessment.tier_label,
                "top_reasons": ";".join(reason.label for reason in assessment.reasons[:4]),
                "next_follow_up_days": assessment.plan.follow_up_days,
                "referral": assessment.plan.referral,
            }
        )
        scored.append(row)
    fieldnames = list(scored[0].keys()) if scored else []
    with output_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored)
    print(f"Wrote {len(scored)} scored rows to {output_path}")


def generate_synthetic(args: argparse.Namespace) -> None:
    path = write_synthetic_csv(args.output, n=args.n, seed=args.seed)
    print(f"Wrote synthetic data to {path}")


def quality_report(args: argparse.Namespace) -> None:
    with Path(args.input).open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    payload = {
        "rows": len(rows),
        "completeness": completeness(rows),
        "range_violations": range_violations(rows),
    }
    _write_json(payload, args.output)


def train_tabular(args: argparse.Namespace) -> None:
    report = train_tabular_models(
        args.input,
        outcome_col=args.outcome_col,
        output_report=args.output_report,
    )
    _write_json(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CHD risk assessment prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)

    one = subparsers.add_parser("score-one", help="Score one JSON patient snapshot")
    one.add_argument("input")
    one.add_argument("--output")
    one.set_defaults(func=score_one)

    batch = subparsers.add_parser("score-csv", help="Score a CSV of patient snapshots")
    batch.add_argument("input")
    batch.add_argument("--output", required=True)
    batch.set_defaults(func=score_csv)

    synth = subparsers.add_parser("generate-synthetic", help="Generate synthetic demo data")
    synth.add_argument("--n", type=int, default=200)
    synth.add_argument("--seed", type=int, default=42)
    synth.add_argument("--output", default="data/synthetic_patients.csv")
    synth.set_defaults(func=generate_synthetic)

    quality = subparsers.add_parser("quality-report", help="Run basic data quality checks")
    quality.add_argument("input")
    quality.add_argument("--output")
    quality.set_defaults(func=quality_report)

    train = subparsers.add_parser("train-tabular", help="Train optional sklearn baseline models")
    train.add_argument("input")
    train.add_argument("--outcome-col", default="outcome_chd")
    train.add_argument("--output-report", default="outputs/training_report.json")
    train.set_defaults(func=train_tabular)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
