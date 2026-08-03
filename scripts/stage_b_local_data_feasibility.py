from __future__ import annotations

import argparse
import json
import re
import warnings
from datetime import date
from pathlib import Path
from typing import Iterable


def _require_pandas():
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install spreadsheet dependencies before running Stage B audit: "
            "pip install pandas openpyxl"
        ) from exc
    return pd


IDENTIFIER_TOKENS = ("患者ID", "就诊编号", "医院名称", "病房")
DATE_TOKENS = ("日期", "时间")
TEXT_TOKENS = (
    "主诉",
    "现病史",
    "既往史",
    "个人史",
    "家族史",
    "体格检查",
    "专科检查",
    "辅助检查",
    "诊断",
    "检查",
    "处置",
    "所见",
    "结论",
)

PREDICTOR_SIGNALS = {
    "age": ("年龄",),
    "sex": ("性别",),
    "blood_pressure": ("收缩压", "舒张压", "SBP", "DBP", "血压"),
    "lipids": ("总胆固醇", "低密度", "高密度", "LDL", "HDL"),
    "glucose": ("空腹血糖", "血糖", "FPG"),
    "smoking": ("吸烟", "烟龄", "戒烟"),
    "diabetes": ("糖尿病",),
    "hypertension": ("高血压",),
    "ckd": ("慢性肾", "肾功能不全", "CKD"),
    "atrial_fibrillation": ("房颤", "心房颤动"),
    "family_history": ("家族史", "冠心病家族史"),
    "medication": ("阿司匹林", "他汀", "降压", "降脂", "抗血小板", "用药"),
    "outcome_follow_up": ("结局", "死亡", "心肌梗死", "心梗", "PCI", "CABG", "随访"),
}

DIAGNOSIS_SIGNALS = {
    "chd_or_cad": "冠心病|冠状动脉|CAD|CHD",
    "acute_mi": "心肌梗死|心梗|AMI|STEMI|NSTEMI",
    "angina": "心绞痛",
    "pci_or_cabg": "PCI|支架|搭桥|CABG",
    "death": "死亡",
}

REQUIRED_RESEARCH_TABLE_FIELDS = {
    "patient_id",
    "index_date",
    "age",
    "sex",
    "sbp",
    "dbp",
    "bmi",
    "total_chol",
    "ldl_c",
    "hdl_c",
    "fasting_glucose",
    "smoker",
    "diabetes",
    "hypertension",
    "outcome_chd",
    "outcome_date",
    "followup_end_date",
}

HEADER_ALIASES = {
    "patient_id": ("patient_id", "患者ID", "研究编号"),
    "index_date": ("index_date", "reference_date", "评估日期", "基准日期"),
    "age": ("age", "年龄"),
    "sex": ("sex", "性别"),
    "sbp": ("sbp", "收缩压"),
    "dbp": ("dbp", "舒张压"),
    "bmi": ("bmi", "BMI", "体重指数"),
    "total_chol": ("total_chol", "总胆固醇", "TC"),
    "ldl_c": ("ldl_c", "LDL", "低密度脂蛋白"),
    "hdl_c": ("hdl_c", "HDL", "高密度脂蛋白"),
    "fasting_glucose": ("fasting_glucose", "空腹血糖", "FPG"),
    "smoker": ("smoker", "吸烟"),
    "diabetes": ("diabetes", "糖尿病"),
    "hypertension": ("hypertension", "高血压"),
    "outcome_chd": ("outcome_chd", "冠心病结局", "结局"),
    "outcome_date": ("outcome_date", "结局日期"),
    "followup_end_date": ("followup_end_date", "随访截止", "末次随访"),
}


def _matches_any(text: str, tokens: Iterable[str]) -> bool:
    text_lower = text.lower()
    return any(token.lower() in text_lower for token in tokens)


def _safe_count_text(df, columns: list[str], pattern: str) -> int:
    count = 0
    for column in columns:
        values = df[column].dropna().astype(str)
        count += int(values.str.contains(pattern, regex=True, case=False, na=False).sum())
    return count


def _date_summary(pd, series) -> dict[str, object]:
    parsed = pd.to_datetime(series, errors="coerce")
    if not parsed.notna().any():
        return {"non_null": 0, "min": None, "max": None}
    return {
        "non_null": int(parsed.notna().sum()),
        "min": str(parsed.min().date()),
        "max": str(parsed.max().date()),
    }


def _direct_required_fields(columns: list[str]) -> dict[str, bool]:
    header_text = " ".join(columns)
    direct = {}
    for field in REQUIRED_RESEARCH_TABLE_FIELDS:
        direct[field] = _matches_any(header_text, HEADER_ALIASES.get(field, (field,)))
    return direct


def audit_workbook(workbook: Path, sheet: str | None = None) -> dict[str, object]:
    pd = _require_pandas()
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

    excel = pd.ExcelFile(workbook)
    sheet_name = sheet or excel.sheet_names[0]
    df = pd.read_excel(workbook, sheet_name=sheet_name)
    df.columns = [str(column) for column in df.columns]
    columns = list(df.columns)

    date_columns = [column for column in columns if _matches_any(column, DATE_TOKENS)]
    text_columns = [column for column in columns if _matches_any(column, TEXT_TOKENS)]
    identifier_columns = [column for column in columns if _matches_any(column, IDENTIFIER_TOKENS)]
    diagnosis_columns = [
        column
        for column in ("就诊诊断", "门（急）诊诊断", "入院诊断", "检查结论")
        if column in df.columns
    ]

    predictor_presence = {}
    header_text = " ".join(columns)
    for key, tokens in PREDICTOR_SIGNALS.items():
        pattern = "|".join(re.escape(token) for token in tokens)
        predictor_presence[key] = {
            "direct_header": _matches_any(header_text, tokens),
            "text_mentions": _safe_count_text(df, text_columns, pattern),
        }

    diagnosis_signal_counts = {}
    for column in diagnosis_columns:
        diagnosis_signal_counts[column] = {
            "non_null": int(df[column].notna().sum()),
            **{
                signal: _safe_count_text(df, [column], pattern)
                for signal, pattern in DIAGNOSIS_SIGNALS.items()
            },
        }

    direct_required_fields = _direct_required_fields(columns)
    missing_direct_required_fields = sorted(
        field for field, is_present in direct_required_fields.items() if not is_present
    )

    missing_rates = df.isna().mean().sort_values(ascending=False)
    non_null_counts = df.notna().sum().sort_values(ascending=False)

    unique_patient_id = None
    if "患者ID" in df.columns:
        unique_patient_id = int(df["患者ID"].nunique(dropna=True))
    unique_visit_id = None
    if "就诊编号" in df.columns:
        unique_visit_id = int(df["就诊编号"].nunique(dropna=True))

    return {
        "generated_on": str(date.today()),
        "source_workbook_name": workbook.name,
        "sheet": sheet_name,
        "shape": {"rows": int(len(df)), "columns": int(len(columns))},
        "unique_patient_id": unique_patient_id,
        "unique_visit_id": unique_visit_id,
        "columns": columns,
        "identifier_like_columns": identifier_columns,
        "date_columns": date_columns,
        "date_ranges": {column: _date_summary(pd, df[column]) for column in date_columns},
        "text_like_columns": text_columns,
        "top_non_null_columns": {
            str(column): int(value) for column, value in non_null_counts.head(15).items()
        },
        "top_missing_columns": {
            str(column): round(float(value), 4) for column, value in missing_rates.head(15).items()
        },
        "direct_required_fields": direct_required_fields,
        "missing_direct_required_fields": missing_direct_required_fields,
        "predictor_signal_counts": predictor_presence,
        "diagnosis_signal_counts": diagnosis_signal_counts,
        "readiness": {
            "stage": "Stage B local data feasibility",
            "training_ready": False,
            "reason": (
                "The workbook is a visit/report-level extract. It lacks a patient-level "
                "research table with structured predictors, explicit outcome_chd, "
                "outcome_date, followup_end_date, and same-source non-CHD controls."
            ),
        },
        "privacy_guardrail": (
            "This audit reports only aggregate counts, headers, missingness, and keyword "
            "signals. It does not export patient-level rows, raw notes, identifiers, or "
            "individual predictions."
        ),
    }


def write_report(summary: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "local_data_feasibility_summary.json"
    report_path = output_dir / "local_data_feasibility_report.md"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    shape = summary["shape"]
    date_ranges = summary["date_ranges"]
    diagnosis_signal_counts = summary["diagnosis_signal_counts"]
    missing_fields = summary["missing_direct_required_fields"]

    lines = [
        "# Stage B Local Data Feasibility Report",
        "",
        f"Generated on: {summary['generated_on']}",
        f"Source workbook: `{summary['source_workbook_name']}`",
        f"Sheet: `{summary['sheet']}`",
        "",
        "## Aggregate Scope",
        "",
        f"- Rows: {shape['rows']}",
        f"- Columns: {shape['columns']}",
        f"- Unique patient IDs: {summary['unique_patient_id']}",
        f"- Unique visit IDs: {summary['unique_visit_id']}",
        "",
        "## Date Coverage",
        "",
    ]
    for column, payload in date_ranges.items():
        lines.append(
            f"- {column}: {payload['non_null']} non-null, {payload['min']} to {payload['max']}"
        )

    lines.extend(
        [
            "",
            "## Training Readiness",
            "",
            "- Status: not training-ready.",
            "- Reason: current file is a visit/report-level extract, not a one-patient-one-row research table.",
            "- Required patient-level outcome fields are not directly present.",
            "- Structured vitals/labs/risk factors need to be extracted or joined from HIS/LIS/public-health tables.",
            "- Same-source non-CHD controls are required before fitting a primary-prevention model.",
            "",
            "## Missing Direct Research-Table Fields",
            "",
        ]
    )
    lines.extend(f"- `{field}`" for field in missing_fields)

    lines.extend(["", "## Diagnosis Signal Counts", ""])
    for column, counts in diagnosis_signal_counts.items():
        lines.append(f"- {column}: {counts}")

    lines.extend(
        [
            "",
            "## Next ETL Tasks",
            "",
            "1. Create a de-identified patient master index and choose one `index_date` per person.",
            "2. Define baseline extraction windows, for example -365 to 0 days before `index_date`.",
            "3. Join structured blood pressure, lipid, glucose, diagnosis, medication, and follow-up records.",
            "4. Label `outcome_chd`, `outcome_date`, and `followup_end_date` from diagnoses, hospitalization, procedure, death, and follow-up sources.",
            "5. Add comparable non-CHD residents or chronic-disease-management controls from the same source system.",
            "6. Export the one-patient-one-row table described in `data/stage_b_research_table_schema.csv`.",
            "",
            "## Privacy Note",
            "",
            str(summary["privacy_guardrail"]),
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit a local real-world workbook for Stage B CHD model feasibility."
    )
    parser.add_argument("--workbook", required=True, help="Local .xlsx file. Do not commit it.")
    parser.add_argument("--sheet", help="Sheet name. Defaults to the first sheet.")
    parser.add_argument("--output-dir", default="outputs/stage_b_local_data")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = audit_workbook(Path(args.workbook), sheet=args.sheet)
    json_path, report_path = write_report(summary, Path(args.output_dir))
    print(f"Wrote aggregate JSON summary to {json_path}")
    print(f"Wrote aggregate Markdown report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
