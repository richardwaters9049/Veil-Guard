"""Offline synthetic corpus v1. No repository ingestion or provider validation.

Labels come from authored scenario intent. Source bytes, IDs and splits are
portable; feature coordinates use the existing f64 tolerance, not byte equality.
"""
from collections import Counter, defaultdict
import base64
import hashlib
import json
from pathlib import Path
import re

import feature_reference as features

ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = ROOT / "research/synthetic-recipe.json"
SCHEMA = "veilguard.corpus.v1"
LABELS = ("sensitive_candidate", "benign_fixture", "uncertain")
DOMAINS = (
    "billing inventory search session mail metrics cache queue archive reports "
    "workspace worker scheduler ledger analytics media edge relay backup sync "
    "notifications catalog support gateway broker audit stream export ingest accounts "
    "jobs storage chat registry build deploy monitor console portal receipts "
    "events telemetry tasks identity routing dispatch uploads downloads pricing shipping "
    "indexer realtime feature sandbox signing snapshots migration admin tracing heartbeat"
).split()
KINDS = ("opaque", "hex", "numeric", "repeated", "uuid", "passphrase",
         "encoded_looking", "placeholder_like", "prose", "marked_demo")
CHALLENGES = ("array_context", "named_argument", "unfamiliar_key", "escape",
              "template", "concatenation", "unicode", "multiline", "short", "long")
WORDS = ("amber", "orbit", "copper", "river", "maple", "lunar", "velvet", "harbour")


class CorpusError(ValueError):
    """Fixed codes only; never format source, values or candidate coordinates."""


def require(condition, code="corpus_contract_mismatch"):
    if not condition:
        raise CorpusError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def recipe():
    config = json.loads(RECIPE_PATH.read_text())
    require(config["schema"] == "veilguard.corpus-recipe.v1")
    require(config["recipe_version"] == "synthetic-v1")
    require(config["repositories"] == len(DOMAINS) == 60)
    require(config["variants_per_family"] == 50 and config["challenge_variants"] == 20)
    return config


def safe_id(seed, family, ordinal, duplicate=False):
    return "vg-" + digest(canonical([seed, family, ordinal, duplicate]))[:24]


def noise(seed, root, length, alphabet):
    raw = hashlib.shake_256(canonical([seed, root]).encode()).digest(length)
    return "".join(alphabet[b % len(alphabet)] for b in raw)


def authored_value(seed, repository, ordinal):
    root = f"core/{repository:02}/{ordinal:02}"
    # The fixed seed is public test configuration, never key material.
    alnum = noise(seed, root, 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    kind = repository % len(KINDS)
    if kind == 0:
        return alnum[:16 + ordinal % 33]
    if kind == 1:
        return noise(seed, root, 32 if ordinal % 2 else 64, "0123456789abcdef")
    if kind == 2:
        return noise(seed, root, 8 + ordinal % 9, "0123456789")
    if kind == 3:
        pattern = noise(seed, root, 2 + ordinal % 3, "abcxyz012")
        if repository == 23 and ordinal == 0:
            return "00000000"
        return (pattern * 12)[:16 + ordinal % 25] + "-" + alnum[:8]
    if kind == 4:
        h = noise(seed, root, 32, "0123456789abcdef")
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
    if kind == 5:
        return "-".join(WORDS[(ord(c) + ordinal) % len(WORDS)] for c in alnum[:3]) + "-" + alnum[3:9]
    if kind == 6:
        return base64.urlsafe_b64encode(hashlib.sha256(alnum.encode()).digest()).decode().rstrip("=")
    if kind == 7:
        return ("replace_me_", "example_", "your_api_key_here_")[ordinal % 3] + alnum[:10]
    if kind == 8:
        return " ".join(WORDS[(ord(c) + ordinal) % len(WORDS)] for c in alnum[:3]) + " " + alnum[3:9]
    return "VG_DEMO_" + alnum[:16]


def render(repository, role, value):
    domain = DOMAINS[repository]
    if role == "sensitive_candidate":
        key = (f"{domain}_password", f"{domain}Credential",
               f"{domain}_access", f"{domain}Material")[repository % 4]
    else:
        key = (f"{domain}_example_password", f"{domain}_checksum",
               f"{domain}_fixture_id")[repository % 3]
    form = repository % 6
    if form == 0:
        prefix, suffix = key + ' = "', '"'
    elif form == 1:
        prefix, suffix = "  '" + key + "': '", "', # authored offline fixture"
    elif form == 2:
        prefix, suffix = key + ': "', '"; // authored lab'
    elif form == 3 and re.fullmatch(r"[A-Za-z0-9_./:@%\-]+", value):
        prefix, suffix = key + "=", ""
    elif form == 4:
        prefix, suffix = "register_" + key + '("', '")'
    elif form == 5:
        prefix, suffix = 'set_option("', '") // ' + key
    else:
        prefix, suffix = key + '="', '"'
    return prefix + value + suffix, len(prefix.encode()), len((prefix + value).encode())


def make_record(config, family, repository, ordinal, label, kind, value, rendered,
                derivation, copy_of=None):
    line, start, end = rendered
    return {
        "schema": SCHEMA, "id": safe_id(config["seed"], family, ordinal),
        "recipe_version": config["recipe_version"], "provenance": "authored_offline_synthetic",
        "family_id": family, "repository_id": repository, "derivation_id": derivation,
        "copy_of": copy_of, "label": label, "value_kind": kind,
        "label_rationale": (
            "Scenario intentionally simulates a credential requiring review; no credential is provisioned."
            if label == LABELS[0] else
            "Scenario intentionally uses a nonsecret test constant, identifier or placeholder."
            if label == LABELS[1] else
            "Authored ambiguity/unsupported-format challenge; no reliable credential class is asserted."
        ),
        "value": value, "source": line, "start": start, "end": end,
        "feature_schema": features.SCHEMA, "feature_status": None, "features": None,
    }


def source_records(config):
    records = []
    for index, domain in enumerate(DOMAINS):
        for label in LABELS[:2]:
            family = f"{domain}/" + ("credential" if label == LABELS[0] else "nonsecret")
            for ordinal in range(config["variants_per_family"]):
                ancestor = index - 1 if index < 20 and index % 2 and ordinal == 0 else index
                root = f"core/{ancestor:02}/{ordinal:02}"
                value = authored_value(config["seed"], ancestor, ordinal)
                if index == 59 and label == LABELS[1] and ordinal < 5:
                    value = ("password", "changeme", "placeholder", "replace_me", "your_api_key_here")[ordinal]
                copied_family = f"{DOMAINS[ancestor]}/" + family.split("/")[1]
                copied_id = safe_id(config["seed"], copied_family, ordinal) if ancestor != index else None
                row = make_record(config, family, f"repo-{index:02}", ordinal, label,
                                  ("exact_placeholder" if index == 59 and label == LABELS[1] and ordinal < 5 else KINDS[index % 10]),
                                  value, render(index, label, value), root, copied_id)
                records.append(row)
                if ordinal == 0:
                    duplicate = dict(row)
                    duplicate["id"] = safe_id(config["seed"], family, ordinal, duplicate=True)
                    records.append(duplicate)
    for index, kind in enumerate(CHALLENGES):
        for ordinal in range(config["challenge_variants"]):
            family = "challenge/" + kind
            root = f"challenge/{index}/{ordinal}"
            value = noise(config["seed"], root, 24, "abcdefghijklmnopqrstuvwxyz0123456789")
            prefix, suffix = '["', '",]'
            if index == 1:
                prefix, suffix = 'deliver(value: "', '")'
            elif index == 2:
                prefix, suffix = '"X-Veil-Material": "', '"'
            elif index == 3:
                value = value[:8] + r"\t" + value[8:]
                prefix, suffix = 'token = "', '"'
            elif index == 4:
                prefix, suffix = "token = " + chr(96), chr(96)
            elif index == 5:
                prefix, suffix = 'token = "', '" + extension'
            elif index == 6:
                value = "café-" + value
                prefix, suffix = 'token = "', '"'
            elif index == 7:
                value = value[:12] + "\n" + value[12:]
                prefix, suffix = 'token = """', '"""'
            elif index == 8:
                value = value[:7]
                prefix, suffix = 'token = "', '"'
            elif index == 9:
                value = noise(config["seed"], root, 257, "abcdefghijklmnopqrstuvwxyz0123456789")
                prefix, suffix = 'token = "', '"'
            rendered = (prefix + value + suffix, len(prefix.encode()), len((prefix + value).encode()))
            records.append(make_record(config, family, f"challenge-repo-{index:02}", ordinal,
                                       LABELS[2], kind, value, rendered, root))
    return records


def deduplicate(rows):
    seen, kept, aliases = {}, [], []
    for row in rows:
        key = canonical([row[k] for k in ("family_id", "repository_id", "derivation_id",
                                         "label", "source", "start", "end")])
        if key in seen:
            aliases.append({"duplicate_id": row["id"], "canonical_id": seen[key],
                            "reason": "exact_source_span_intent_and_provenance"})
        else:
            seen[key] = row["id"]
            kept.append(row)
    require(len({row["id"] for row in rows}) == len(rows), "duplicate_fixture_id")
    return sorted(kept, key=lambda r: r["id"]), sorted(aliases, key=lambda a: a["duplicate_id"])


def components(rows):
    parent = {row["id"]: row["id"] for row in rows}
    def find(key):
        require(key in parent, "unknown_copy_reference")
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    def union(left, right):
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    owners = {}
    for row in rows:
        keys = [("family", row["family_id"]), ("repository", row["repository_id"]),
                ("derivation", row["derivation_id"]), ("value", row["value"])]
        for key in keys:
            if key in owners:
                union(row["id"], owners[key])
            else:
                owners[key] = row["id"]
        if row["copy_of"] is not None:
            union(row["id"], row["copy_of"])
    groups = defaultdict(list)
    for row in rows:
        groups[find(row["id"])].append(row)
    return list(groups.values())


def input_hashes():
    paths = ("research/corpus.py", "research/synthetic-recipe.json", "research/feature_reference.py",
             "research/uv.lock", "schemas/feature-contract.json", "schemas/corpus-v1.json")
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def source_digest(rows):
    # f64 features are checked numerically; source/provenance identity is byte-stable.
    return digest("".join(canonical({k: v for k, v in row.items()
                                    if k not in ("features", "feature_status")}) for row in rows))


def build(config=None, include_features=True):
    config = config or recipe()
    raw = source_records(config)
    rows, aliases = deduplicate(raw)
    groups = []
    for members in components(rows):
        uncertain = {row["label"] == LABELS[2] for row in members}
        require(len(uncertain) == 1, "challenge_connected_to_labelled_corpus")
        ids = sorted(row["id"] for row in members)
        groups.append({"group_id": "group-" + digest(canonical(ids))[:20], "members": ids,
                       "repository_ids": sorted({r["repository_id"] for r in members}),
                       "family_ids": sorted({r["family_id"] for r in members}),
                       "partition": "challenge" if True in uncertain else None})
    labelled = sorted((g for g in groups if g["partition"] is None),
                      key=lambda g: digest(canonical([config["seed"], g["group_id"]])))
    counts = config["split"]
    require(len(labelled) == sum(counts[k] for k in ("train_groups", "validation_groups", "test_groups")),
            "independent_group_count_changed")
    start = 0
    for partition in ("train", "validation", "test"):
        end = start + counts[partition + "_groups"]
        for group in labelled[start:end]:
            group["partition"] = partition
        start = end
    membership = {identifier: g for g in groups for identifier in g["members"]}
    for row in rows:
        row["group_id"] = membership[row["id"]]["group_id"]
        row["partition"] = membership[row["id"]]["partition"]
        if include_features:
            try:
                row["features"] = features.from_line(row["source"], row["start"], row["end"])
                row["feature_status"] = "eligible"
            except features.FeatureError:
                row["feature_status"] = "unsupported"
    # This prespecified subset is synthetic skew, not measured real-world prevalence.
    skew = sorted(row["id"] for row in rows if row["partition"] == "test"
                  and (row["label"] == LABELS[1] or int(digest(row["id"]), 16) % 10 == 0))
    manifest = {
        "schema": "veilguard.split-manifest.v1", "corpus_schema": SCHEMA,
        "recipe_version": config["recipe_version"], "feature_schema": features.SCHEMA,
        "seed": config["seed"], "input_hashes": input_hashes(), "source_sha256": source_digest(rows),
        "groups": sorted(groups, key=lambda g: g["group_id"]),
        "evaluation_slices": {"synthetic_skewed_test": skew},
        "split_policy": "Connected family/repository/value/derivation/copy components; 30/10/10 core groups; challenges isolated.",
    }
    summary = {
        "schema": "veilguard.corpus-summary.v1", "raw_records": len(raw), "canonical_records": len(rows),
        "exact_duplicates_removed": len(aliases), "distinct_values": len({r["value"] for r in rows}),
        "families": len({r["family_id"] for r in rows}),
        "repositories": len({r["repository_id"] for r in rows}),
        "groups": len(groups), "core_groups": len(labelled),
        "feature_schema": features.SCHEMA, "feature_names": list(features.NAMES),
        "labels": dict(sorted(Counter(r["label"] for r in rows).items())),
        "partitions": {},
        "synthetic_skewed_test_labels": dict(sorted(Counter(r["label"] for r in rows if r["id"] in set(skew)).items())),
    }
    for partition in ("train", "validation", "test", "challenge"):
        selected = [r for r in rows if r["partition"] == partition]
        summary["partitions"][partition] = {
            "records": len(selected), "groups": sum(g["partition"] == partition for g in groups),
            "labels": dict(sorted(Counter(r["label"] for r in selected).items())),
            "feature_status": dict(sorted(Counter(r["feature_status"] for r in selected).items())),
        }
    return rows, manifest, {"schema": "veilguard.deduplication.v1", "aliases": aliases}, summary
