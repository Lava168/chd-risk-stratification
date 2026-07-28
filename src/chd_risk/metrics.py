from __future__ import annotations


def roc_auc_score(y_true: list[int], y_score: list[float]) -> float:
    """Pure-Python AUC using rank statistics."""
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length")
    positives = sum(1 for value in y_true if value == 1)
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("AUC requires at least one positive and one negative sample")

    ranked = sorted(enumerate(y_score), key=lambda item: item[1])
    ranks = [0.0] * len(y_score)
    index = 0
    while index < len(ranked):
        end = index
        while end + 1 < len(ranked) and ranked[end + 1][1] == ranked[index][1]:
            end += 1
        average_rank = (index + end + 2) / 2.0
        for offset in range(index, end + 1):
            ranks[ranked[offset][0]] = average_rank
        index = end + 1

    positive_rank_sum = sum(rank for rank, target in zip(ranks, y_true) if target == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def binary_classification_metrics(
    y_true: list[int],
    y_score: list[float],
    threshold: float = 0.10,
) -> dict[str, float]:
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length")
    predicted = [1 if score >= threshold else 0 for score in y_score]
    tp = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, predicted) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, predicted) if y == 1 and p == 0)

    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if precision + sensitivity else 0.0
    return {
        "threshold": threshold,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
    }

