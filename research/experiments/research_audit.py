"""Verify frozen membership/exports and replay sealed metrics without model tuning."""
from pathlib import Path
import math
import numpy as np

import common
from development import policy_from_predictions, macro_ap
from learning import ExactKNN, require, review_reason, NAMES
import evaluation
import metrics


def close(left, right, tolerance=1e-9):
    if left is None or isinstance(left, (str, bool)):
        require(left == right, "replay_value_mismatch")
    elif isinstance(left, dict):
        require(isinstance(right, dict) and set(left) == set(right), "replay_fields_mismatch")
        for key in left:
            close(left[key], right[key], tolerance)
    elif isinstance(left, list):
        require(isinstance(right, list) and len(left) == len(right), "replay_length_mismatch")
        for a, b in zip(left, right):
            close(a, b, tolerance)
    else:
        require(type(left) in (float, int) and type(right) in (float, int)
                and math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance,
                "replay_numeric_mismatch")


def development_artifacts(directory, rows, manifest):
    from run_experiment import verify_freeze
    directory = Path(directory)
    freeze = verify_freeze(directory)
    require(freeze["corpus_source_sha256"] == manifest["source_sha256"])
    train = sorted([r for r in rows if r["partition"] == "train"], key=lambda r: r["id"])
    validation = sorted([r for r in rows if r["partition"] == "validation"], key=lambda r: r["id"])
    x, y, ids = common.arrays(train)
    data = common.load_json(directory / "development.json")
    require(data["train_rows"] == len(train) and data["validation_rows"] == len(validation))
    require(data["train_ids_sha256"] == common.identity(ids))
    require(data["validation_ids_sha256"] == common.identity([r["id"] for r in validation]))
    groups = {r["group_id"] for r in train}
    held_out_groups = []
    for fold in data["folds"]:
        fit, held_out = set(fold["fit_groups"]), set(fold["score_groups"])
        require(not fit.intersection(held_out) and fit.union(held_out) == groups, "fold_leakage")
        held_out_groups.extend(held_out)
        fit_rows = [r for r in train if r["group_id"] in fit]
        scored_rows = [r for r in train if r["group_id"] in held_out]
        require(common.identity(sorted(r["id"] for r in fit_rows)) == fold["fit_ids_sha256"])
        require(common.identity(sorted(r["id"] for r in scored_rows)) == fold["score_ids_sha256"])
        fit_x, _, _ = common.arrays(fit_rows)
        close(fold["mean"], fit_x.mean(axis=0).tolist())
        scales = fit_x.std(axis=0, ddof=0)
        scales[scales == 0] = 1
        close(fold["scale"], scales.tolist())
    require(len(data["folds"]) == common.protocol()["folds"] and len(held_out_groups) == len(set(held_out_groups))
            and set(held_out_groups) == groups)
    model_bundle = common.load_json(directory / "model.json")
    baselines = common.load_json(directory / "baselines.json")
    require(set(baselines) == {"schema", "raw_knn", "logistic"} and baselines["schema"] == "veilguard.baselines.v1")
    for representation, bundle in (("standardised", model_bundle), ("raw", baselines["raw_knn"])):
        model = ExactKNN.from_bundle(bundle)
        require(model.ids.tolist() == ids and model.y.tolist() == y.tolist(), "non_training_model_reference")
        require(bundle["corpus_source_sha256"] == manifest["source_sha256"]
                and bundle["protocol_sha256"] == common.sha_file(common.EXPERIMENT / "protocol.json"))
        close(model.lower.tolist(), x.min(axis=0).tolist())
        close(model.upper.tolist(), x.max(axis=0).tolist())
        if representation == "standardised":
            close(model.mean.tolist(), x.mean(axis=0).tolist())
            scales = x.std(axis=0, ddof=0)
            scales[scales == 0] = 1
            close(model.scale.tolist(), scales.tolist())
        else:
            close(model.mean.tolist(), [0]*8)
            close(model.scale.tolist(), [1]*8)
        close(model.z.tolist(), ((x-model.mean)/model.scale).tolist())
        require(model.k == data["selected_knn"][representation]["k"]
                and model.weights == data["selected_knn"][representation]["weights"])
    for representation in ("standardised", "raw"):
        candidates = [r for r in data["knn_grid"] if r["representation"] == representation]
        best = max(candidates, key=lambda r: (round(r["macro_repository_AP"],12),-r["k"],
                                             r["weights"]=="inverse_distance"))
        require(data["selected_knn"][representation] == best, "selection_not_training_grid_winner")
    best_c = max(data["logistic_grid"], key=lambda r:(round(r["macro_repository_AP"],12),-r["C"]))["C"]
    require(best_c == data["selected_logistic_C"] == baselines["logistic"]["C"])
    close(baselines["logistic"]["mean"], model_bundle["mean"])
    close(baselines["logistic"]["scale"], model_bundle["scale"])
    require(len(baselines["logistic"]["coefficient"]) == 8
            and all(math.isfinite(v) for v in baselines["logistic"]["coefficient"])
            and math.isfinite(baselines["logistic"]["intercept"]))
    record = data["validation_policy"]
    require(record["ids"] == [r["id"] for r in validation] and len(record["predictions"]) == len(validation))
    policy, replayed = policy_from_predictions(record["predictions"],
                                               [int(r["label"]=="sensitive_candidate") for r in validation],
                                               common.protocol())
    close(policy, model_bundle["policy"])
    close({k:v for k,v in record.items() if k not in ("ids","predictions")}, replayed)
    require([r["name"] for r in data["training_only_ablations"]] == NAMES)
    oof = common.load_json(directory / "development-predictions.json")
    require([r["id"] for r in oof] == ids)
    for model_name, representation in (("standardised_knn","standardised"),("raw_knn","raw")):
        close(macro_ap(train,y,[r["scores"][model_name] for r in oof]),
              data["selected_knn"][representation]["macro_repository_AP"])
    close(macro_ap(train,y,[r["scores"]["logistic"] for r in oof]),
          max(r["macro_repository_AP"] for r in data["logistic_grid"]))
    return model_bundle, baselines, data


def sealed_evaluation(directory, development_directory, rows, manifest):
    directory = Path(directory)
    seal = common.load_json(directory / "evaluation-seal.json")
    require(seal["schema"] == "veilguard.evaluation-seal.v1"
            and seal["implementation_sha256"] == common.core_hashes())
    require(seal["development_freeze_sha256"] == common.sha_file(Path(development_directory) / "freeze.json"))
    names = {"evaluation.json", "test-predictions.json", "challenge-predictions.json"}
    require(set(seal["artifacts"]) == names)
    for name, checksum in seal["artifacts"].items():
        require(common.sha_file(directory / name) == checksum, "sealed_evaluation_changed")
    report = common.load_json(directory / "evaluation.json")
    records = common.load_json(directory / "test-predictions.json")
    challenges = common.load_json(directory / "challenge-predictions.json")
    test = {r["id"]:r for r in rows if r["partition"] == "test"}
    missing = set(report["native_extraction"]["missing_test_fixture_ids"])
    require(missing.issubset(test) and {r["id"] for r in records} == set(test)-missing)
    require(len(records) == len({r["id"] for r in records}))
    model_bundle = common.load_json(Path(development_directory) / "model.json")
    baselines = common.load_json(Path(development_directory) / "baselines.json")
    for row in records:
        source = test[row["id"]]
        require(row["label"] == int(source["label"]=="sensitive_candidate"))
        for key in ("repository_id","family_id","group_id","value_kind"):
            require(row[key] == source[key])
        require(set(row["scores"]) == set(evaluation.MODELS) and all(math.isfinite(v) for v in row["scores"].values()))
        close(row["scores"]["entropy"],source["features"][1])
        for model, policy in (("standardised_knn",model_bundle["policy"]),("raw_knn",baselines["raw_knn"]["policy"])):
            prediction = row["predictions"][model]
            require(0 <= row["scores"][model] <= 1)
            close(prediction["score"],row["scores"][model])
            reason = review_reason(prediction["score"],prediction,policy)
            require(prediction["review_reason"] == reason and prediction["prediction"] ==
                    (None if reason else int(prediction["score"]>=.5)))
        require(row["scores"]["rules"] in (0,1) and row["scores"]["gitleaks"] in (0,1))
        require(0 <= row["scores"]["logistic"] <= 1)
        require(row["predictions"]["logistic"] == {"prediction":int(row["scores"]["logistic"]>=.5),"review_reason":None})
    require({r["id"] for r in challenges} == {r["id"] for r in rows if r["partition"]=="challenge"})
    replay = evaluation.summarise(records,challenges,report["native_extraction"],
                                  report["external_reference"],common.protocol(),manifest)
    close({k:v for k,v in report.items() if k!="environment"},
          {k:v for k,v in replay.items() if k!="environment"})
    tool = report["external_reference"]["tool"]
    lock = common.load_json(common.EXPERIMENT/"gitleaks-lock.json")
    require(tool["version"]==lock["version"] and any(
        asset["name"]==tool["asset"] and asset["sha256"]==tool["archive_sha256"]
        for asset in lock["assets"].values()))
    return report
