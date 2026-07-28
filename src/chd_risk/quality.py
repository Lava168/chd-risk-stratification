from __future__ import annotations

from collections import Counter
from typing import Iterable


CORE_FIELDS = ("patient_id", "age", "sex", "sbp", "ldl_c", "diabetes")


def completeness(records: Iterable[dict], fields: tuple[str, ...] = CORE_FIELDS) -> dict[str, float]:
    rows = list(records)
    if not rows:
        return {field: 0.0 for field in fields}
    result = {}
    for field in fields:
        present = sum(1 for row in rows if row.get(field) not in (None, ""))
        result[field] = present / len(rows)
    return result


def range_violations(records: Iterable[dict]) -> dict[str, int]:
    rules = {
        "age": (18, 110),
        "sbp": (70, 260),
        "dbp": (40, 160),
        "bmi": (12, 60),
        "ldl_c": (0.2, 12.0),
        "hdl_c": (0.2, 4.0),
        "fasting_glucose": (2.0, 30.0),
    }
    violations = Counter()
    for row in records:
        for field, (lower, upper) in rules.items():
            value = row.get(field)
            if value in (None, ""):
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                violations[field] += 1
                continue
            if numeric < lower or numeric > upper:
                violations[field] += 1
    return dict(violations)

