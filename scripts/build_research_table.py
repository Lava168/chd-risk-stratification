"""Build a one-patient-one-row research table from the local CHD workbook.

This ETL extracts structured predictors and outcome signals from the
visit/report-level Excel export and writes a de-identified patient-level
research table to a LOCAL (git-ignored) path. It does NOT write raw notes,
identifiers, or patient-level text into git.

Extraction rules are documented in docs/research_table_extraction.md.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

CHD_ANY_PATTERN = re.compile(r"冠心病|冠状动脉|心肌梗死|心梗|PCI|支架|CABG|搭桥|CHD|CAD", re.IGNORECASE)
SEVERE_CHD_PATTERN = re.compile(r"心肌梗死|心梗|AMI|STEMI|NSTEMI|PCI|支架|CABG|搭桥", re.IGNORECASE)
BP_PATTERN = re.compile(r"(?:BP|血压)\s*[:：]?\s*(\d{2,3})\s*/\s*(\d{2,3})", re.IGNORECASE)
SMOKE_POSITIVE = re.compile(
    r"吸烟史\s*\d+年|吸烟\s*\d+年|烟龄|长期吸烟|已戒烟|现吸烟|吸烟史", re.IGNORECASE
)
SMOKE_DENY = re.compile(r"否认.*吸烟|无吸烟史|不吸烟|否认吸烟", re.IGNORECASE)
DIAGNOSIS_COLS = ["就诊诊断", "门（急）诊诊断", "入院诊断", "检查结论"]
DATE_COLS = ["就诊日期", "出院日期", "检查日期", "报告日期"]


def _contains(series: pd.Series, pattern: re.Pattern, deny: re.Pattern | None = None) -> pd.Series:
    text = series.dropna().astype(str)
    hit = text.str.contains(pattern, regex=True, na=False)
    result = pd.Series(False, index=series.index)
    result[text.index[hit]] = True
    if deny is not None:
        denied = text.str.contains(deny, regex=True, na=False)
        result[text.index[denied]] = False
    return result


def _extract_bp(text: str) -> tuple[float | None, float | None]:
    match = BP_PATTERN.search(text)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def build_research_table(workbook: Path, sheet: str, output: Path) -> Path:
    df = pd.read_excel(workbook, sheet_name=sheet)
    df["患者ID"] = pd.to_numeric(df["患者ID"], errors="coerce")
    df = df.dropna(subset=["患者ID"]).copy()
    df["患者ID"] = df["患者ID"].astype(int)

    # ---- clean basics ----
    df = df.rename(columns={"年龄": "age"})
    df["sex"] = df["性别"].astype(str).str.strip().replace({"男": "male", "女": "female"})
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # drop implausible dates (e.g. the 1800-01-01 anomaly)
    for col in DATE_COLS:
        df.loc[df[col] < pd.Timestamp("2000-01-01"), col] = pd.NaT

    df["is_hospitalized"] = df["就诊类型"].astype(str).str.strip().eq("住院")
    df["hosp_count_raw"] = pd.to_numeric(df["住院次数"], errors="coerce")

    # ---- per-row signals ----
    bp = df["体格检查"].dropna().astype(str).apply(_extract_bp)
    df["sbp_row"] = bp.apply(lambda v: v[0])
    df["dbp_row"] = bp.apply(lambda v: v[1])

    smoke_text = (
        df["个人史"].fillna("") + " " + df["既往史"].fillna("") + " " + df["现病史"].fillna("")
    )
    # 0 = non-smoker (explicit denial), 1 = current/former smoker, NaN = no information
    df["smoker_row"] = pd.NA
    pos = smoke_text.str.contains(SMOKE_POSITIVE, regex=True, na=False)
    deny = smoke_text.str.contains(SMOKE_DENY, regex=True, na=False)
    df.loc[pos & ~deny, "smoker_row"] = 1
    df.loc[deny, "smoker_row"] = 0

    def _flag(series, keyword, deny=None):
        pat = re.compile(keyword)
        den = re.compile(deny) if deny else None
        return _contains(series, pat, den)

    text_hist = df["既往史"].fillna("") + " " + df["现病史"].fillna("")
    df["diabetes_row"] = _contains(
        text_hist, re.compile(r"糖尿病"), re.compile(r"否认.{0,8}糖尿病|无.{0,4}糖尿病|排除.{0,6}糖尿病")
    )
    df["hypertension_row"] = _contains(
        text_hist, re.compile(r"高血压"), re.compile(r"否认.{0,8}高血压|无.{0,4}高血压|排除.{0,6}高血压")
    )
    for col in DIAGNOSIS_COLS:
        df["diabetes_row"] |= _contains(df[col], re.compile(r"糖尿病"))
        df["hypertension_row"] |= _contains(df[col], re.compile(r"高血压"))

    # ECG abnormal: rows whose report/conclusion is an ECG, conclusion not normal
    ecg_rows = df["报告名称"].dropna().astype(str).str.contains(
        r"心电图|ECG", regex=True, na=False
    ).reindex(df.index, fill_value=False)
    ecg_rows |= df["检查结论"].dropna().astype(str).str.contains(
        r"心电图|ECG", regex=True, na=False
    ).reindex(df.index, fill_value=False)
    df["ecg_abnormal_row"] = False
    ecg_conclusion = df.loc[ecg_rows, "检查结论"].dropna().astype(str)
    abnormal = ~ecg_conclusion.str.contains(r"正常", regex=True, na=False)
    df.loc[ecg_conclusion.index[abnormal], "ecg_abnormal_row"] = True

    chd_any_mask = pd.Series(False, index=df.index)
    severe_mask = pd.Series(False, index=df.index)
    for col in DIAGNOSIS_COLS:
        s = df[col].dropna().astype(str)
        chd_any_mask |= s.str.contains(CHD_ANY_PATTERN, regex=True, na=False).reindex(df.index, fill_value=False)
        severe_mask |= s.str.contains(SEVERE_CHD_PATTERN, regex=True, na=False).reindex(df.index, fill_value=False)

    # ---- collapse to one row per patient ----
    groups = df.groupby("患者ID")
    table = pd.DataFrame(index=groups.size().index)
    table.index.name = "patient_id"
    table["sex"] = groups["sex"].first()
    table["age"] = groups["age"].first()
    table["index_date"] = groups["就诊日期"].min()
    table["followup_end_date"] = df[DATE_COLS + ["患者ID"]].melt(
        id_vars="患者ID", value_name="dt"
    ).dropna(subset=["dt"]).groupby("患者ID")["dt"].max().reindex(table.index)
    table["sbp"] = groups["sbp_row"].median()
    table["dbp"] = groups["dbp_row"].median()
    table["pulse_pressure"] = table["sbp"] - table["dbp"]
    table["diabetes"] = groups["diabetes_row"].any().astype(int)
    table["hypertension"] = groups["hypertension_row"].any().astype(int)
    table["smoker"] = groups["smoker_row"].max()
    table["ecg_abnormal"] = groups["ecg_abnormal_row"].any().astype(int)
    table["ever_hospitalized"] = groups["is_hospitalized"].any().astype(int)
    table["hosp_count"] = groups["hosp_count_raw"].max()
    table["n_visits"] = groups.size()
    table["outcome_chd"] = chd_any_mask.groupby(df["患者ID"]).any().astype(int)
    table["outcome_severe_chd"] = severe_mask.groupby(df["患者ID"]).any().astype(int)
    table["outcome_hospitalized"] = table["ever_hospitalized"]

    # outcome_date = first date of a CHD-signal row
    chd_dates = df.loc[chd_any_mask, ["患者ID", "就诊日期"]].dropna(subset=["就诊日期"])
    table["outcome_date"] = chd_dates.groupby("患者ID")["就诊日期"].min().reindex(table.index)

    table = table.reset_index()
    table["index_date"] = table["index_date"].dt.strftime("%Y-%m-%d")
    table["followup_end_date"] = table["followup_end_date"].dt.strftime("%Y-%m-%d")
    table["outcome_date"] = table["outcome_date"].dt.strftime("%Y-%m-%d")

    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False, encoding="utf-8")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build patient-level research table from local CHD workbook.")
    parser.add_argument("--workbook", required=True, help="Local .xlsx file. Do not commit it.")
    parser.add_argument("--sheet", default="冠心病21")
    parser.add_argument(
        "--output",
        default="data/processed/research_table_local.csv",
        help="Local (git-ignored) research table output path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = build_research_table(Path(args.workbook), args.sheet, Path(args.output))
    print(f"Wrote patient-level research table ({path.stat().st_size} bytes) to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
