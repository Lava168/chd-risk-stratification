# Data Directory

This directory is for synthetic or fully de-identified demonstration files only.

Do not commit raw HIS/LIS/PACS/EMR exports, patient-level real-world data, identifiers, or derived files that can be traced back to an individual.

`stage_b_research_table_schema.csv` is a schema template for the de-identified
one-patient-one-row research table needed for local model training. It is not
patient data.

Generate a demo dataset:

```bash
PYTHONPATH=src python -m chd_risk.cli generate-synthetic --n 200 --output data/synthetic_patients.csv
```
