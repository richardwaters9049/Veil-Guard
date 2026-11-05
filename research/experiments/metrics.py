"""Prespecified ranking, selective-classification and group-bootstrap metrics."""
from collections import defaultdict
import math
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, auc

from learning import require

RANKING_METRICS = ("precision_at_20", "recall_at_20", "average_precision", "trapezoidal_pr_auc")


def mean_defined(values):
    selected = [float(v) for v in values if v is not None]
    return sum(selected) / len(selected) if selected else None


def ranking(ids, outcomes, scores, top_k=20):
    require(len(ids) == len(outcomes) == len(scores) and len(set(ids)) == len(ids))
    require(all(v in (0, 1) for v in outcomes) and all(math.isfinite(float(s)) for s in scores))
    n, positives = len(ids), sum(outcomes)
    m = min(top_k, n)
    order = sorted(range(n), key=lambda i: (-float(scores[i]), ids[i]))
    hits = sum(outcomes[i] for i in order[:m])
    precision = hits / m if m else None
    recall = hits / positives if positives else None
    if n and positives:
        ap = float(average_precision_score(outcomes, scores))
        curve_p, curve_r, _ = precision_recall_curve(outcomes, scores)
        pr_area = float(auc(curve_r, curve_p))
    else:
        ap = pr_area = None
    return {"n": n, "positives": positives, "top_m": m, "hits": hits,
            "precision_at_m": precision, "recall_at_m": recall,
            "precision_at_20": precision if n >= top_k else None,
            "recall_at_20": recall if n >= top_k else None,
            "average_precision": ap, "trapezoidal_pr_auc": pr_area}


def repositories(records, model):
    groups = defaultdict(list)
    for row in records:
        groups[row["repository_id"]].append(row)
    result = []
    for repository, selected in sorted(groups.items()):
        component = {r["group_id"] for r in selected}
        require(len(component) == 1, "repository_crosses_components")
        metrics = ranking([r["id"] for r in selected], [r["label"] for r in selected],
                          [r["scores"][model] for r in selected])
        result.append({"repository_id": repository, "group_id": component.pop(), **metrics})
    return result


def aggregate(per_repository):
    return {
        "repositories": len(per_repository),
        "eligible_at_20": sum(r["n"] >= 20 for r in per_repository),
        "small_repositories": sum(r["n"] < 20 for r in per_repository),
        "no_positive_repositories": sum(r["positives"] == 0 for r in per_repository),
        "macro": {metric: mean_defined(r[metric] for r in per_repository)
                  for metric in (*RANKING_METRICS, "precision_at_m", "recall_at_m")},
        "undefined": {metric: sum(r[metric] is None for r in per_repository) for metric in RANKING_METRICS},
    }


def paired_interval(left, right, metric, repetitions, seed):
    right_by_id = {r["repository_id"]: r for r in right}
    require({r["repository_id"] for r in left} == set(right_by_id))
    groups = defaultdict(list)
    for row in left:
        other = right_by_id[row["repository_id"]]
        require(row["group_id"] == other["group_id"])
        if row[metric] is not None and other[metric] is not None:
            groups[row["group_id"]].append(float(row[metric] - other[metric]))
    ordered = [groups[key] for key in sorted(groups)]
    if not ordered:
        return {"estimate": None, "lower": None, "upper": None, "groups": 0, "valid_replicates": 0}
    generator = np.random.default_rng(seed)
    draws = generator.integers(0, len(ordered), size=(repetitions, len(ordered)))
    values = []
    for sample in draws:
        selected = [value for index in sample for value in ordered[int(index)]]
        values.append(sum(selected) / len(selected))
    pooled = [v for group in ordered for v in group]
    low, high = np.quantile(values, [0.025, 0.975], method="linear")
    return {"estimate": sum(pooled) / len(pooled), "lower": float(low), "upper": float(high),
            "groups": len(ordered), "valid_replicates": repetitions,
            "method": "paired_connected_group_percentile_95", "seed": seed}


def intervals(per_repository, repetitions, seed):
    zero = [{**row, **{metric: 0.0 if row[metric] is not None else None for metric in RANKING_METRICS}}
            for row in per_repository]
    return {metric: paired_interval(per_repository, zero, metric, repetitions, seed)
            for metric in RANKING_METRICS}


def selective(outcomes, predictions):
    require(len(outcomes) == len(predictions))
    counts = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    accepted_y, accepted_pred = [], []
    for truth, prediction in zip(outcomes, predictions):
        require(truth in (0, 1) and prediction in (0, 1, None))
        if prediction is not None:
            counts[("tn", "fp", "fn", "tp")[truth * 2 + prediction]] += 1
            accepted_y.append(truth)
            accepted_pred.append(prediction)
    accepted = len(accepted_y)
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"total": len(outcomes), "accepted": accepted, "abstained": len(outcomes) - accepted,
            "coverage": accepted / len(outcomes) if outcomes else None,
            "error_rate_on_accepted": (fp + fn) / accepted if accepted else None,
            "accepted_positive_support": sum(accepted_y),
            "accepted_negative_support": accepted - sum(accepted_y),
            "full_positive_support": sum(outcomes), "confusion": counts,
            "precision_on_accepted": precision, "recall_on_accepted": recall, "f1_on_accepted": f1}


def confidence_coverage(ids, outcomes, scores, fractions):
    order = sorted(range(len(ids)), key=lambda i: (-abs(2 * scores[i] - 1), ids[i]))
    result = []
    for fraction in fractions:
        n = max(1, int(len(order) * fraction)) if order else 0
        accepted = order[:n]
        errors = sum(int(scores[i] >= 0.5) != outcomes[i] for i in accepted)
        result.append({"requested_fraction": fraction, "accepted": n,
                       "actual_coverage": n / len(order) if order else None,
                       "hypothetical_error": errors / n if n else None})
    return result


def benefit(standardised, entropy, interval, minimum_relative):
    if standardised is None or entropy is None or entropy == 0 or interval["lower"] is None:
        return {"decision": "unproven", "relative_improvement": None,
                "reason": "undefined_baseline_or_interval"}
    relative = (standardised - entropy) / entropy
    passed = relative >= minimum_relative and interval["lower"] > 0
    return {"decision": "pass_on_synthetic_benchmark" if passed else "fail_on_synthetic_benchmark",
            "relative_improvement": relative,
            "reason": "relative_and_interval_gates_met" if passed else "relative_or_interval_gate_not_met",
            "deployment_status": "experimental_research_only"}
