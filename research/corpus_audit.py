"""Corpus integrity and leakage audit. No metrics, fitting or tuning."""
from collections import Counter, defaultdict
import math
import re

import corpus
import feature_reference as features


def review_digest(row):
    return corpus.digest(corpus.canonical({k: v for k, v in row.items() if k != "features"}))


def review_sample(rows):
    selected = {}
    for row in sorted(rows, key=lambda r: r["id"]):
        stratum = (row["label"], row["value_kind"], row["feature_status"])
        selected.setdefault(stratum, row)
    low_entropy = next(r for r in rows if r["label"] == "sensitive_candidate" and r["value"] == "00000000")
    selected[("targeted", "low_entropy_zeros", "eligible")] = low_entropy
    return sorted(selected.values(), key=lambda r: r["id"])


def validate_relations(rows, assignments):
    require = corpus.require
    by_id = {row["id"]: row for row in rows}
    relations = {}
    for row in rows:
        for kind, key in (("family", row["family_id"]), ("repository", row["repository_id"]),
                          ("derivation", row["derivation_id"]), ("value", row["value"])):
            relation = (kind, key)
            if relation in relations:
                require(relations[relation] == assignments[row["id"]], "related_rows_cross_groups")
            else:
                relations[relation] = assignments[row["id"]]
        if row["copy_of"] is not None:
            require(row["copy_of"] in by_id, "unknown_copy_reference")
            require(assignments[row["copy_of"]] == assignments[row["id"]], "copy_crosses_groups")
            require(by_id[row["copy_of"]]["value"] == row["value"], "copy_value_mismatch")
    return True


def validate(rows, manifest, dedup, summary, config=None):
    config = config or corpus.recipe()
    require = corpus.require
    require(manifest["schema"] == "veilguard.split-manifest.v1")
    require(manifest["corpus_schema"] == corpus.SCHEMA)
    require(manifest["feature_schema"] == features.SCHEMA)
    require(manifest["input_hashes"] == corpus.input_hashes(), "stale_corpus_inputs")
    require(manifest["source_sha256"] == corpus.source_digest(rows), "source_digest_mismatch")
    require(manifest["recipe_version"] == config["recipe_version"] and manifest["seed"] == config["seed"])
    require(summary["schema"] == "veilguard.corpus-summary.v1")
    require(dedup["schema"] == "veilguard.deduplication.v1")
    ids = {row["id"] for row in rows}
    require(len(ids) == len(rows), "duplicate_fixture_id")
    by_id = {row["id"]: row for row in rows}
    assignments = {}
    for group in manifest["groups"]:
        require(group["members"] and len(group["members"]) == len(set(group["members"])))
        require(group["members"] == sorted(group["members"]))
        require(group["group_id"] == "group-" + corpus.digest(corpus.canonical(group["members"]))[:20])
        for identifier in group["members"]:
            require(identifier in ids and identifier not in assignments, "duplicate_or_unknown_split_member")
            assignments[identifier] = (group["group_id"], group["partition"])
        members = [by_id[identifier] for identifier in group["members"]]
        require(group["repository_ids"] == sorted({r["repository_id"] for r in members}))
        require(group["family_ids"] == sorted({r["family_id"] for r in members}))
    require(set(assignments) == ids, "missing_split_member")
    validate_relations(rows, assignments)
    expected_fields = {
        "schema", "id", "recipe_version", "provenance", "family_id", "repository_id",
        "derivation_id", "copy_of", "label", "value_kind", "label_rationale", "value", "source",
        "start", "end", "feature_schema", "feature_status", "features", "group_id", "partition",
    }
    for row in rows:
        require(set(row) == expected_fields, "row_schema_mismatch")
        require(re.fullmatch(r"vg-[0-9a-f]{24}", row["id"]) is not None)
        require(row["schema"] == corpus.SCHEMA and row["recipe_version"] == config["recipe_version"])
        require(row["provenance"] == "authored_offline_synthetic")
        require(row["feature_schema"] == features.SCHEMA)
        require((row["group_id"], row["partition"]) == assignments[row["id"]])
        require(row["partition"] in ("train", "validation", "test", "challenge"))
        require(type(row["start"]) is int and type(row["end"]) is int)
        source = row["source"].encode("utf-8")
        require(0 <= row["start"] <= row["end"] <= len(source))
        require(source[row["start"]:row["end"]].decode("utf-8") == row["value"], "candidate_span_mismatch")
        if row["family_id"].startswith("challenge/"):
            require(row["label"] == "uncertain" and row["partition"] == "challenge",
                    "uncertainty_entered_labelled_split")
            require(row["value_kind"] == row["family_id"].split("/")[1] in corpus.CHALLENGES)
        else:
            domain, intent = row["family_id"].split("/")
            require(domain in corpus.DOMAINS and intent in ("credential", "nonsecret"))
            require(row["label"] == ("sensitive_candidate" if intent == "credential" else "benign_fixture"),
                    "authored_label_mismatch")
            require(row["partition"] != "challenge")
            require(row["feature_status"] == "eligible" and 8 <= len(row["value"]) <= 256)
            require(all(0x20 <= b <= 0x7e for b in row["value"].encode()))
        try:
            expected = features.from_line(row["source"], row["start"], row["end"])
        except features.FeatureError:
            require(row["feature_status"] == "unsupported" and row["features"] is None,
                    "unsupported_vector_imputed")
        else:
            vector = row["features"]
            require(row["feature_status"] == "eligible" and isinstance(vector, list) and len(vector) == 8)
            require(all(type(v) in (int, float) and math.isfinite(v) for v in vector))
            require(all(abs(a - b) <= 1e-9 for a, b in zip(vector, expected)), "feature_source_mismatch")
    expected_components = {frozenset(r["id"] for r in group) for group in corpus.components(rows)}
    require(expected_components == {frozenset(g["members"]) for g in manifest["groups"]},
            "component_partition_mismatch")
    duplicates = dedup["aliases"]
    duplicate_ids = [row["duplicate_id"] for row in duplicates]
    require(len(duplicate_ids) == len(set(duplicate_ids)) and not ids.intersection(duplicate_ids))
    require(all(a["canonical_id"] in ids and a["reason"] == "exact_source_span_intent_and_provenance"
                for a in duplicates))
    # Deduplication evidence must correspond to the authored pre-deduplication inputs.
    originals, expected_aliases = corpus.deduplicate(corpus.source_records(config))
    require(duplicates == expected_aliases and {r["id"] for r in originals} == ids, "deduplication_mismatch")
    policy = config["policy"]
    require(policy["minimum_canonical_candidates"] <= len(rows) <= policy["maximum_canonical_candidates"])
    require(len({r["family_id"] for r in rows}) >= policy["minimum_families"])
    require(len({r["repository_id"] for r in rows}) >= policy["minimum_repositories"])
    require(summary["raw_records"] == len(rows) + len(duplicates))
    require(summary["canonical_records"] == len(rows) and summary["exact_duplicates_removed"] == len(duplicates))
    require(summary["distinct_values"] == len({r["value"] for r in rows}))
    require(summary["families"] == len({r["family_id"] for r in rows}))
    require(summary["repositories"] == len({r["repository_id"] for r in rows}))
    require(summary["groups"] == len(manifest["groups"]))
    require(summary["core_groups"] == sum(g["partition"] != "challenge" for g in manifest["groups"]))
    require(summary["labels"] == dict(Counter(r["label"] for r in rows)))
    require(summary["feature_schema"] == features.SCHEMA and summary["feature_names"] == list(features.NAMES))
    for partition in ("train", "validation", "test", "challenge"):
        selected = [r for r in rows if r["partition"] == partition]
        count = config["split"][partition + "_groups"]
        require(sum(g["partition"] == partition for g in manifest["groups"]) == count)
        require(summary["partitions"][partition] == {
            "records": len(selected), "groups": count,
            "labels": dict(Counter(r["label"] for r in selected)),
            "feature_status": dict(Counter(r["feature_status"] for r in selected)),
        })
        require(set(r["label"] for r in selected) == ({"uncertain"} if partition == "challenge"
                                                     else {"sensitive_candidate", "benign_fixture"}))
    require(config["split"]["train_groups"] >= policy["minimum_train_groups"])
    skew = manifest["evaluation_slices"]["synthetic_skewed_test"]
    expected_skew = sorted(r["id"] for r in rows if r["partition"] == "test"
                           and (r["label"] == "benign_fixture" or int(corpus.digest(r["id"]), 16) % 10 == 0))
    require(skew == expected_skew and len(skew) == len(set(skew)))
    require(summary["synthetic_skewed_test_labels"] == dict(Counter(by_id[i]["label"] for i in skew)))
    return True


def validate_review(rows, review):
    require = corpus.require
    require(review["schema"] == "veilguard.label-review.v1")
    require(review["reviewer"] == "Codex assisted review; not independent human adjudication")
    require(review["reviewed_on"] == "2026-11-05")
    sample = review_sample(rows)
    entries = {entry["id"]: entry for entry in review["entries"]}
    require(len(entries) == len(review["entries"]) == len(sample), "label_review_sample_mismatch")
    require(set(entries) == {r["id"] for r in sample})
    for row in sample:
        entry = entries[row["id"]]
        require(entry["source_sha256"] == review_digest(row), "stale_label_review")
        require(entry["label"] == row["label"] and entry["value_kind"] == row["value_kind"])
        require(entry["decision"] == ("retain_uncertain" if row["label"] == "uncertain"
                                      else "consistent_with_authored_intent"))
        require(isinstance(entry["rationale"], str) and len(entry["rationale"]) >= 30)
    return len(sample)


def matrix_for(rows, manifest, partition):
    """View of previously audited rows; labels/IDs are separate. No fitting."""
    corpus.require(partition in ("train", "validation", "test"), "challenge_matrix_forbidden")
    corpus.require(manifest["source_sha256"] == corpus.source_digest(rows), "source_digest_mismatch")
    bindings = {identifier: (g["group_id"], g["partition"])
                for g in manifest["groups"] for identifier in g["members"]}
    corpus.require(len(bindings) == len(rows) and all(
        bindings.get(r["id"]) == (r["group_id"], r["partition"]) for r in rows), "split_binding_mismatch")
    selected = sorted((r for r in rows if r["partition"] == partition), key=lambda r: r["id"])
    corpus.require(bool(selected), "empty_matrix")
    corpus.require(all(r["label"] in corpus.LABELS[:2] and r["feature_status"] == "eligible"
                       and isinstance(r["features"], list) and len(r["features"]) == 8
                       and all(type(v) in (int, float) and math.isfinite(v) for v in r["features"])
                       for r in selected), "invalid_training_matrix")
    return [r["id"] for r in selected], [list(r["features"]) for r in selected], [r["label"] for r in selected]
