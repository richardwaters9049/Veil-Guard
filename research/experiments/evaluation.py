"""Held-out evaluation after export freeze. This module never fits a model."""
from collections import Counter, defaultdict
from pathlib import Path
import subprocess
import tempfile
import time

import numpy as np

import common
import metrics
from learning import ExactKNN, require
from development import logistic_scores
import external_reference
import fixture_repositories


MODELS = ("rules", "entropy", "raw_knn", "standardised_knn", "logistic", "gitleaks")


def native_surface(rows, binary):
    require(rows and all(r["partition"] in ("test", "challenge") for r in rows), "native_scope_mismatch")
    binary = Path(binary).resolve()
    require(binary.is_file(), "native_binary_missing")
    by_name = {r["id"] + ".fixture": r for r in rows}
    by_repository = defaultdict(list)
    for row in rows:
        by_repository[row["repository_id"]].append(row)
    covered, severity = set(), {}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="veilguard-held-out-") as temporary:
        root = Path(temporary) / "repositories"
        materialised = fixture_repositories.materialise(rows, root)
        fixture_repositories.verify_staged(rows, materialised, root)
        index_before = {key: common.sha_file(root / key / ".git/index") for key in by_repository}
        for repository, selected in sorted(by_repository.items()):
            result = subprocess.run([str(binary), "scan", "--staged", "--repo", str(root / repository),
                                     "--format", "json"], capture_output=True,
                                    env=fixture_repositories.git_environment(), check=False, timeout=30)
            require(result.returncode in (0, 1), "native_scan_incomplete")
            output = result.stdout.decode("utf-8")
            error = result.stderr.decode("utf-8")
            require(not any(r["value"] in output or r["value"] in error for r in selected),
                    "native_private_value_capture")
            import json
            report = json.loads(output, parse_constant=common.reject_constant)
            require(report["report_schema"] == "veilguard.report.v2" and report["coverage_complete"],
                    "native_report_mismatch")
            for finding in report["findings"]:
                name = Path(finding["path"]).name
                if name not in by_name:
                    continue
                row = by_name[name]
                if row["partition"] == "challenge" or (
                        finding["staged_line"] == 1 and finding["staged_column"] - 1 < row["end"]
                        and finding["end_column"] - 1 > row["start"]):
                    covered.add(row["id"])
                    severity[row["id"]] = max(severity.get(row["id"], 0.0),
                                              1.0 if finding["policy"] == "block" else 0.0)
        require(index_before == {key: common.sha_file(root / key / ".git/index") for key in by_repository},
                "native_index_modified")
        fixture_repositories.verify_staged(rows, materialised, root)
    test = [r for r in rows if r["partition"] == "test"]
    positives = [r for r in test if r["label"] == "sensitive_candidate"]
    benign = [r for r in test if r["label"] == "benign_fixture"]
    reached = sum(r["id"] in covered for r in positives)
    false_reviews = sum(r["id"] in covered for r in benign)
    changed_lines = sum(len(r["source"].splitlines()) for r in test)
    return covered, severity, {
        "scanner_binary_sha256": common.sha_file(binary),
        "scanner_source_hashes": {str(p.relative_to(common.ROOT)): common.sha_file(p)
                                  for p in sorted((common.ROOT / "src").glob("*.rs"))},
        "test_repositories": len({r["repository_id"] for r in test}), "test_rows": len(test),
        "sensitive_support": len(positives), "sensitive_candidates_surfaced": reached,
        "sensitive_surfacing_recall": reached / len(positives) if positives else None,
        "benign_candidates_surfaced": false_reviews,
        "benign_review_occurrences_per_1000_changed_lines": 1000 * false_reviews / changed_lines if changed_lines else None,
        "changed_test_lines": changed_lines,
        "missing_test_fixture_ids": sorted(r["id"] for r in test if r["id"] not in covered),
        "challenge_fixtures_with_any_finding": sum(r["partition"] == "challenge" and r["id"] in covered for r in rows),
        "blocking_pattern_fixtures": sum(score == 1.0 for score in severity.values()),
        "source_index_immutability": "verified", "source_value_capture": "none_observed",
        "elapsed_seconds_including_fixture_setup": time.monotonic() - started,
        "interpretation": "surfacing authored candidates for review; not credential validity or model-enabled recall",
    }


def challenge_predictions(model, policy, rows):
    require(all(r["partition"] == "challenge" for r in rows))
    result = []
    eligible = [r for r in rows if r["feature_status"] == "eligible"]
    inferred = {r["id"]: prediction for r, prediction in zip(
        eligible, model.predict([r["features"] for r in eligible], policy))} if eligible else {}
    for row in rows:
        prediction = inferred.get(row["id"])
        result.append({"id": row["id"], "value_kind": row["value_kind"],
                       "feature_status": row["feature_status"],
                       "score": prediction["score"] if prediction else None,
                       "prediction": prediction["prediction"] if prediction else None,
                       "review_reason": prediction["review_reason"] if prediction else "unsupported_input"})
    return result


def summarise(records, challenge, native, external, p, manifest):
    ranked = {}
    for model in MODELS:
        per_repository = metrics.repositories(records, model)
        ranked[model] = {"aggregate": metrics.aggregate(per_repository), "repositories": per_repository,
                         "intervals": metrics.intervals(per_repository, p["bootstrap"]["repetitions"],
                                                       p["bootstrap"]["seed"])}
    comparison = metrics.paired_interval(ranked["standardised_knn"]["repositories"],
                                         ranked["entropy"]["repositories"], "precision_at_20",
                                         p["bootstrap"]["repetitions"], p["bootstrap"]["seed"])
    gate = metrics.benefit(ranked["standardised_knn"]["aggregate"]["macro"]["precision_at_20"],
                           ranked["entropy"]["aggregate"]["macro"]["precision_at_20"], comparison,
                           p["benefit_gate"]["minimum_relative_improvement"])
    outcomes = [r["label"] for r in records]
    classification = {}
    for key in ("standardised_knn", "raw_knn", "logistic"):
        classification[key] = {
            "selective": metrics.selective(outcomes, [r["predictions"][key]["prediction"] for r in records]),
            "review_reasons": dict(Counter(r["predictions"][key]["review_reason"] for r in records
                                           if r["predictions"][key]["review_reason"] is not None)),
            "hypothetical_confidence_coverage": metrics.confidence_coverage(
                [r["id"] for r in records], outcomes, [r["scores"][key] for r in records],
                p["diagnostics"]["fixed_confidence_coverage"]),
        }
    by_kind = {}
    for kind in sorted({r["value_kind"] for r in records}):
        subset = [r for r in records if r["value_kind"] == kind]
        by_kind[kind] = {"rows": len(subset), "sensitive": sum(r["label"] for r in subset),
                         "standardised_knn": metrics.ranking(
                             [r["id"] for r in subset], [r["label"] for r in subset],
                             [r["scores"]["standardised_knn"] for r in subset]),
                         "selective": metrics.selective([r["label"] for r in subset],
                             [r["predictions"]["standardised_knn"]["prediction"] for r in subset])}
    skew_ids = set(manifest["evaluation_slices"]["synthetic_skewed_test"])
    skew = [r for r in records if r["id"] in skew_ids]
    skew_metrics = {model: metrics.aggregate(metrics.repositories(skew, model)) for model in MODELS}
    challenge_scores = [r["score"] for r in challenge if r["score"] is not None]
    return {
        "schema": "veilguard.evaluation.v1", "corpus_source_sha256": manifest["source_sha256"],
        "protocol_sha256": common.sha_file(common.EXPERIMENT / "protocol.json"),
        "environment": common.environment(), "test_population": {
            "extracted_eligible_rows": len(records), "sensitive": sum(outcomes),
            "benign": len(records) - sum(outcomes),
            "repositories": len({r["repository_id"] for r in records}),
            "connected_groups": len({r["group_id"] for r in records}),
            "families": len({r["family_id"] for r in records})},
        "ranking": ranked, "primary_paired_difference": comparison, "benefit_gate": gate,
        "classification": classification, "value_kind_slices": by_kind,
        "synthetic_skewed_test": {"rows": len(skew), "sensitive": sum(r["label"] for r in skew),
                                  "ranking": skew_metrics, "independent_of_primary_test": False},
        "representational_limits": {
            "test_exact_match_conflict_queries": sum(r["predictions"]["standardised_knn"]["conflict"] for r in records),
            "test_outside_training_support_queries": sum(r["predictions"]["standardised_knn"]["outside"] for r in records)},
        "challenge": {
            "rows": len(challenge), "eligible": len(challenge_scores),
            "accepted_predictions_without_ground_truth": sum(r["prediction"] is not None for r in challenge),
            "review_reasons": dict(Counter(r["review_reason"] for r in challenge if r["review_reason"] is not None)),
            "score_min": min(challenge_scores) if challenge_scores else None,
            "score_median": float(np.median(challenge_scores)) if challenge_scores else None,
            "score_max": max(challenge_scores) if challenge_scores else None,
            "accuracy": None, "interpretation": "no binary ground truth; no challenge tuning"},
        "native_extraction": native, "external_reference": external,
        "limitations": ["synthetic authored-intent benchmark only", "ten held-out connected groups",
                        "assisted labels without independent human adjudication", "corpus redistribution licence pending",
                        "uncalibrated votes", "native model integration/parity and workload benchmarks remain later phases"],
    }


def evaluate(rows, manifest, model_bundle, baselines, tool_directory, scanner):
    standard = ExactKNN.from_bundle(model_bundle)
    raw = ExactKNN.from_bundle(baselines["raw_knn"])
    test = sorted([r for r in rows if r["partition"] == "test"], key=lambda r: r["id"])
    challenge_rows = sorted([r for r in rows if r["partition"] == "challenge"], key=lambda r: r["id"])
    covered, rule_scores, native = native_surface(test + challenge_rows, scanner)
    detected, external = external_reference.scan(test, tool_directory)
    selected = [r for r in test if r["id"] in covered]
    require(bool(selected), "no_extracted_test_candidates")
    x, y, ids = common.arrays(selected)
    standard_predictions = standard.predict(x, model_bundle["policy"])
    raw_predictions = raw.predict(x, baselines["raw_knn"]["policy"])
    logistic = logistic_scores(baselines["logistic"], x)
    records = []
    for index, row in enumerate(selected):
        log_score = float(logistic[index])
        records.append({
            "id": row["id"], "repository_id": row["repository_id"], "group_id": row["group_id"],
            "family_id": row["family_id"], "value_kind": row["value_kind"], "label": int(y[index]),
            "scores": {"standardised_knn": standard_predictions[index]["score"],
                       "raw_knn": raw_predictions[index]["score"], "logistic": log_score,
                       "entropy": row["features"][1], "rules": rule_scores[row["id"]],
                       "gitleaks": float(row["id"] in detected)},
            "predictions": {"standardised_knn": standard_predictions[index], "raw_knn": raw_predictions[index],
                            "logistic": {"prediction": int(log_score >= 0.5), "review_reason": None}},
        })
    challenge = challenge_predictions(standard, model_bundle["policy"], challenge_rows)
    return summarise(records, challenge, native, external, common.protocol(), manifest), records, challenge
