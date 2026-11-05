"""Train/validation-only selection. Held-out rows are refused at this boundary."""
import time
import warnings
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import common
import metrics
from learning import ExactKNN, require, review_reason, NAMES


def row_scores(rows, outcomes, scores):
    return [{"id": row["id"], "repository_id": row["repository_id"], "group_id": row["group_id"],
             "label": int(label), "scores": {"candidate": float(score)}}
            for row, label, score in zip(rows, outcomes, scores)]


def macro_ap(rows, outcomes, scores):
    result = metrics.aggregate(metrics.repositories(row_scores(rows, outcomes, scores), "candidate"))
    require(result["macro"]["average_precision"] is not None, "undefined_selection_metric")
    return result["macro"]["average_precision"]


def logistic_fit(x, y, c, p):
    estimator = make_pipeline(StandardScaler(), LogisticRegression(
        C=c, solver=p["logistic_solver"], tol=p["logistic_tolerance"],
        max_iter=p["logistic_max_iter"], random_state=p["seed"]))
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        estimator.fit(x, y)
    require(not any(issubclass(w.category, ConvergenceWarning) for w in captured), "logistic_not_converged")
    return estimator


def grouped_selection(rows, p):
    require(rows and all(r["partition"] == "train" for r in rows), "non_training_rows_in_cv")
    x, y, ids = common.arrays(rows)
    groups = np.asarray([r["group_id"] for r in rows])
    splitter = GroupKFold(n_splits=p["folds"], shuffle=True, random_state=p["seed"])
    folds = list(splitter.split(x, y, groups))
    knn_scores = {(representation, k, weight): np.zeros(len(rows))
                  for representation in p["representations"] for k in p["k_grid"] for weight in p["weight_grid"]}
    logistic_scores = {c: np.zeros(len(rows)) for c in p["logistic_C_grid"]}
    fold_records = []
    for number, (fit, held_out) in enumerate(folds):
        require(not set(groups[fit]).intersection(groups[held_out]), "cv_group_overlap")
        require(max(p["k_grid"]) <= len(fit))
        record = {"fold": number, "fit_groups": sorted(set(groups[fit].tolist())),
                  "score_groups": sorted(set(groups[held_out].tolist())),
                  "fit_ids_sha256": common.identity(sorted(ids[i] for i in fit)),
                  "score_ids_sha256": common.identity(sorted(ids[i] for i in held_out))}
        for representation in p["representations"]:
            model = ExactKNN(x[fit], y[fit], [ids[i] for i in fit],
                             k=max(p["k_grid"]), standardised=representation == "standardised")
            if representation == "standardised":
                record["mean"], record["scale"] = model.mean.tolist(), model.scale.tolist()
            for position, info in zip(held_out, model.neighbours(x[held_out], max(p["k_grid"]))):
                for k in p["k_grid"]:
                    for weight in p["weight_grid"]:
                        knn_scores[(representation, k, weight)][position] = model.vote(info, k, weight)
        for c in p["logistic_C_grid"]:
            estimator = logistic_fit(x[fit], y[fit], c, p)
            logistic_scores[c][held_out] = estimator.predict_proba(x[held_out])[:, 1]
        fold_records.append(record)
        print(f"Development CV fold {number + 1}/{len(folds)} complete.", flush=True)
    grid = [{"representation": key[0], "k": key[1], "weights": key[2],
             "macro_repository_AP": macro_ap(rows, y, scores)}
            for key, scores in knn_scores.items()]
    selected = {}
    for representation in p["representations"]:
        candidates = [g for g in grid if g["representation"] == representation]
        selected[representation] = max(candidates, key=lambda g: (
            round(g["macro_repository_AP"], 12), -g["k"], g["weights"] == "inverse_distance"))
    logistic_grid = [{"C": c, "macro_repository_AP": macro_ap(rows, y, score)}
                     for c, score in logistic_scores.items()]
    selected_c = max(logistic_grid, key=lambda g: (round(g["macro_repository_AP"], 12), -g["C"]))["C"]
    oof = []
    for i, row in enumerate(rows):
        s = selected["standardised"]
        r = selected["raw"]
        oof.append({"id": row["id"], "repository_id": row["repository_id"], "group_id": row["group_id"],
                    "label": int(y[i]), "scores": {
                        "standardised_knn": float(knn_scores[("standardised", s["k"], s["weights"])][i]),
                        "raw_knn": float(knn_scores[("raw", r["k"], r["weights"])][i]),
                        "logistic": float(logistic_scores[selected_c][i]),
                        "entropy": float(x[i, 1]), "rules": 0.0}})
    return selected, selected_c, grid, logistic_grid, fold_records, oof, folds


def policy_from_predictions(predictions, outcomes, p):
    grid = []
    settings = p["validation"]
    for quantile in settings["distance_quantiles"]:
        limit = float(np.quantile([r["nearest"] for r in predictions], quantile, method=settings["quantile_method"]))
        for margin in settings["margin_grid"]:
            policy = {"review_all": False, "margin": margin, "distance_limit": limit,
                      "selection_status": "validation_selected"}
            decisions = [None if review_reason(row["score"], row, policy) else int(row["score"] >= 0.5)
                         for row in predictions]
            measured = metrics.selective(outcomes, decisions)
            grid.append({"distance_quantile": quantile, "policy": policy, "metrics": measured})
    feasible = [g for g in grid if g["metrics"]["coverage"] >= settings["minimum_coverage"]
                and g["metrics"]["error_rate_on_accepted"] is not None
                and g["metrics"]["error_rate_on_accepted"] <= settings["maximum_selective_error"]]
    if feasible:
        chosen = min(feasible, key=lambda g: (g["metrics"]["error_rate_on_accepted"],
                                            -g["metrics"]["coverage"], g["policy"]["margin"],
                                            -g["policy"]["distance_limit"]))
        policy = chosen["policy"]
    else:
        policy = {"review_all": True, "margin": 0.0, "distance_limit": 0.0,
                  "selection_status": "coverage_or_error_target_unmet"}
        chosen = {"distance_quantile": None, "policy": policy,
                  "metrics": metrics.selective(outcomes, [None] * len(outcomes))}
    return policy, {"selected": chosen, "grid": grid, "feasible_policies": len(feasible)}


def choose_policy(model, validation_rows, p):
    require(validation_rows and all(r["partition"] == "validation" for r in validation_rows),
            "non_validation_rows_in_threshold_selection")
    x, y, ids = common.arrays(validation_rows)
    predictions = model.predict(x)
    policy, record = policy_from_predictions(predictions, y.tolist(), p)
    record["ids"] = ids
    record["predictions"] = predictions
    return policy, record


def ablations(rows, folds, configuration):
    x, y, ids = common.arrays(rows)
    result = []
    for coordinate in range(8):
        altered = x.copy()
        altered[:, coordinate] = 0.0
        scores = np.zeros(len(rows))
        for fit, held_out in folds:
            model = ExactKNN(altered[fit], y[fit], [ids[i] for i in fit], configuration["k"],
                             configuration["weights"], standardised=True)
            scores[held_out] = [r["score"] for r in model.predict(altered[held_out])]
        result.append({"zeroed_coordinate": coordinate, "name": NAMES[coordinate], "macro_repository_AP": macro_ap(rows, y, scores)})
        print(f"Training-only ablation {coordinate + 1}/8 complete.", flush=True)
    return result


def develop(rows, manifest, p):
    common.require_development(rows)
    started = time.monotonic()
    train = sorted([r for r in rows if r["partition"] == "train"], key=lambda r: r["id"])
    validation = sorted([r for r in rows if r["partition"] == "validation"], key=lambda r: r["id"])
    selected, c, grid, logistic_grid, folds, oof, fold_arrays = grouped_selection(train, p)
    x, y, ids = common.arrays(train)
    standard = ExactKNN(x, y, ids, selected["standardised"]["k"],
                        selected["standardised"]["weights"], standardised=True)
    raw = ExactKNN(x, y, ids, selected["raw"]["k"], selected["raw"]["weights"], standardised=False)
    policy, validation_record = choose_policy(standard, validation, p)
    estimator = logistic_fit(x, y, c, p)
    scale, logistic = estimator.steps[0][1], estimator.steps[1][1]
    logistic_artifact = {"C": c, "mean": scale.mean_.tolist(), "scale": scale.scale_.tolist(),
                         "coefficient": logistic.coef_[0].tolist(), "intercept": float(logistic.intercept_[0])}
    metadata = {"model_id": "synthetic-v1-knn-initial",
                "corpus_source_sha256": manifest["source_sha256"],
                "protocol_sha256": common.sha_file(common.EXPERIMENT / "protocol.json")}
    raw_policy = {"review_all": False, "margin": 0.0, "distance_limit": float(np.finfo(np.float64).max),
                  "selection_status": "baseline_fixed"}
    bundle = standard.bundle(metadata, policy)
    baseline_bundle = {"schema": "veilguard.baselines.v1", "raw_knn": raw.bundle(metadata, raw_policy),
                       "logistic": logistic_artifact}
    ablation = ablations(train, fold_arrays, selected["standardised"])
    centred = x - x.mean(axis=0)
    covariance = centred.T @ centred / len(x)
    deviations = np.sqrt(np.diag(covariance))
    correlation = [[float(covariance[i, j] / (deviations[i] * deviations[j]))
                    if deviations[i] and deviations[j] else None for j in range(8)] for i in range(8)]
    result = {
        "schema": "veilguard.development.v1", "corpus_source_sha256": manifest["source_sha256"],
        "protocol_sha256": metadata["protocol_sha256"], "environment": common.environment(),
        "development_elapsed_seconds": time.monotonic() - started,
        "train_ids_sha256": common.identity(ids), "validation_ids_sha256": common.identity([r["id"] for r in validation]),
        "train_rows": len(train), "validation_rows": len(validation), "folds": folds,
        "knn_grid": grid, "logistic_grid": logistic_grid, "selected_knn": selected,
        "selected_logistic_C": c, "validation_policy": validation_record,
        "training_only_ablations": ablation, "training_only_correlation": correlation,
        "zero_variance_coordinates": np.flatnonzero(np.var(x, axis=0) == 0).tolist(),
        "test_access": "none; only train and validation rows accepted by develop",
    }
    return bundle, baseline_bundle, result, oof


def logistic_scores(artifact, queries):
    from learning import matrix, eight
    x = matrix(queries)
    mean, scale = eight(artifact["mean"]), eight(artifact["scale"])
    coefficient = eight(artifact["coefficient"])
    require(bool((scale > 0).all()) and np.isfinite(artifact["intercept"]))
    z = (x - mean) / scale
    logits = z @ coefficient + artifact["intercept"]
    # Numerically stable sigmoid.
    return np.exp(-np.logaddexp(0, -logits))
