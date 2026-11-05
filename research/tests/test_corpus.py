"""Leakage, determinism, deduplication and safe-export regression checks."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research"))
import corpus
import corpus_audit as audit
import build_corpus
import fixture_repositories


def small_rows():
    return [
        {"id": f"row-{i}", "family_id": f"family-{i}", "repository_id": f"repo-{i}",
         "derivation_id": f"seed-{i}", "value": f"example-value-{i}", "copy_of": None}
        for i in range(3)
    ]


class CorpusControls(unittest.TestCase):
    def test_every_relation_connects_and_cannot_cross_splits(self):
        for field in ("family_id", "repository_id", "derivation_id", "value"):
            with self.subTest(field=field):
                rows = small_rows()
                rows[1][field] = rows[0][field]
                groups = corpus.components(rows)
                self.assertEqual(sorted(map(len, groups)), [1, 2])
                bindings = {r["id"]: ("group-a", "train") for r in rows}
                self.assertTrue(audit.validate_relations(rows, bindings))
                bindings["row-1"] = ("group-b", "test")
                with self.assertRaisesRegex(corpus.CorpusError, "related_rows_cross_groups"):
                    audit.validate_relations(rows, bindings)

    def test_transitive_edges_form_one_component(self):
        rows = small_rows()
        rows[1]["family_id"] = rows[0]["family_id"]
        rows[2]["derivation_id"] = rows[1]["derivation_id"]
        self.assertEqual(len(corpus.components(rows)), 1)

    def test_copy_references_and_value_match_are_required(self):
        rows = small_rows()
        rows[1]["copy_of"] = "row-0"
        self.assertEqual(sorted(map(len, corpus.components(rows))), [1, 2])
        bindings = {r["id"]: ("same", "train") for r in rows}
        with self.assertRaisesRegex(corpus.CorpusError, "copy_value_mismatch"):
            audit.validate_relations(rows, bindings)
        rows[1]["value"] = rows[0]["value"]
        self.assertTrue(audit.validate_relations(rows, bindings))
        rows[1]["copy_of"] = "absent"
        with self.assertRaisesRegex(corpus.CorpusError, "unknown_copy_reference"):
            corpus.components(rows)

    def test_deduplication_keeps_distinct_intent_and_context(self):
        base = dict(small_rows()[0], label="benign_fixture", source='key="example-value-0"', start=5, end=20)
        duplicate = dict(base, id="alias")
        other_context = dict(base, id="different-context", source='other="example-value-0"')
        other_intent = dict(base, id="different-intent", label="sensitive_candidate")
        kept, aliases = corpus.deduplicate([base, duplicate, other_context, other_intent])
        self.assertEqual(len(kept), 3)
        self.assertEqual(aliases[0]["duplicate_id"], "alias")
        self.assertEqual(aliases[0]["canonical_id"], base["id"])
        with self.assertRaisesRegex(corpus.CorpusError, "duplicate_fixture_id"):
            corpus.deduplicate([base, base])

    def test_source_and_split_generation_are_deterministic(self):
        first = corpus.build(include_features=False)
        second = corpus.build(include_features=False)
        self.assertEqual(first, second)
        rows, manifest, aliases, summary = first
        self.assertEqual(len(rows), 6200)
        self.assertEqual(len(aliases["aliases"]), 120)
        self.assertEqual(summary["core_groups"], 50)
        self.assertEqual({p: sum(g["partition"] == p for g in manifest["groups"])
                          for p in ("train", "validation", "test", "challenge")},
                         {"train": 30, "validation": 10, "test": 10, "challenge": 10})
        self.assertTrue(all(r["features"] is None for r in rows))
        self.assertEqual(len(manifest["evaluation_slices"]["synthetic_skewed_test"]), 766)

    def test_matrix_returns_only_eight_coordinates_and_checks_bindings(self):
        rows = [{"id": "sample", "group_id": "group", "partition": "train",
                 "features": [0.0]*8, "label": "benign_fixture", "feature_status": "eligible"}]
        manifest = {"source_sha256": corpus.source_digest(rows),
                    "groups": [{"group_id": "group", "partition": "train", "members": ["sample"]}]}
        ids, matrix, labels = audit.matrix_for(rows, manifest, "train")
        self.assertEqual((ids, matrix, labels), (["sample"], [[0.0]*8], ["benign_fixture"]))
        matrix[0][0] = 999
        self.assertEqual(rows[0]["features"][0], 0)
        with self.assertRaisesRegex(corpus.CorpusError, "challenge_matrix_forbidden"):
            audit.matrix_for(rows, manifest, "challenge")
        for bad in ([0.0]*9, [float("nan")]*8):
            altered = deepcopy(rows)
            altered[0]["features"] = bad
            with self.assertRaises(corpus.CorpusError):
                audit.matrix_for(altered, manifest, "train")
        manifest["groups"][0]["partition"] = "test"
        with self.assertRaisesRegex(corpus.CorpusError, "split_binding_mismatch"):
            audit.matrix_for(rows, manifest, "train")

    def test_new_files_are_private_and_existing_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "corpus.jsonl"
            build_corpus.write_new(path, "authored synthetic row\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                build_corpus.write_new(path, "replacement")
            self.assertEqual(path.read_text(), "authored synthetic row\n")

    def test_materialised_git_fixtures_ignore_redirects_and_detect_changed_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / "outside-index"
            sentinel.write_text("preserve outside bytes")
            template = root / "untrusted-template"
            template.mkdir()
            (template / "copied-marker").write_text("must not be copied")
            rows = [{"id": "vg-" + "a"*24, "repository_id": "repo-00",
                     "provenance": "authored_offline_synthetic", "source": 'password="changeme"'}]
            destination = root / "repositories"
            overrides = {"GIT_INDEX_FILE": str(sentinel), "GIT_DIR": str(root / "outside-git"),
                         "GIT_TEMPLATE_DIR": str(template), "GIT_DEFAULT_HASH": "sha256"}
            with patch.dict(os.environ, overrides):
                metadata = fixture_repositories.materialise(rows, destination)
                self.assertEqual(fixture_repositories.verify_staged(rows, metadata, destination), 1)
            self.assertEqual(sentinel.read_text(), "preserve outside bytes")
            self.assertFalse((root / "outside-git").exists())
            self.assertFalse((destination / "repo-00/.git/copied-marker").exists())
            with self.assertRaises(corpus.CorpusError):
                fixture_repositories.materialise(rows, destination)
            source = destination / ("repo-00/" + rows[0]["id"] + ".fixture")
            source.write_text("changed")
            with self.assertRaisesRegex(corpus.CorpusError, "fixture_worktree_changed"):
                fixture_repositories.verify_staged(rows, metadata, destination)

    def test_existing_output_and_symlink_are_refused_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "existing"
            destination.mkdir()
            sentinel = destination / "keep.txt"
            sentinel.write_text("preserve this")
            link = root / "symlink"
            link.symlink_to(destination, target_is_directory=True)
            for output in (destination, link):
                result = subprocess.run([sys.executable, str(ROOT / "research/build_corpus.py"),
                                         "--output", str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr.strip(), "Corpus output must be a new directory.")
                self.assertEqual(sentinel.read_text(), "preserve this")
                self.assertEqual(sorted(p.name for p in destination.iterdir()), ["keep.txt"])


class CorpusAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = corpus.build()

    def test_complete_bundle_passes(self):
        self.assertTrue(audit.validate(*self.bundle))
        schema = json.loads((ROOT / "schemas/corpus-v1.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]), set(self.bundle[0][0]))
        self.assertEqual(set(schema["required"]), set(self.bundle[0][0]))
        self.assertEqual(len(schema["properties"]["features"]["anyOf"][0]["prefixItems"]), 8)
        self.assertEqual(schema["properties"]["feature_schema"]["const"], "veilguard.features.v1")

    def test_schema_label_span_numeric_and_membership_mutations_fail(self):
        rows, manifest, aliases, summary = self.bundle
        mutations = [
            lambda row: row.update(schema="unknown"),
            lambda row: row.update(label="uncertain"),
            lambda row: row.update(value="changed"),
            lambda row: row.update(features=[0.0]*9),
            lambda row: row.update(features=[float("nan")]*8),
            lambda row: row.update(features=[999.0]*8),
            lambda row: row.update(partition="challenge"),
            lambda row: row.update(feature_status="unsupported", features=None),
            lambda row: row.update(extra_model_coordinate=1),
        ]
        for index, change in enumerate(mutations):
            with self.subTest(index=index):
                modified = deepcopy(rows)
                change(modified[0])
                current = deepcopy(manifest)
                current["source_sha256"] = corpus.source_digest(modified)
                with self.assertRaises(corpus.CorpusError):
                    audit.validate(modified, current, aliases, summary)
        current = deepcopy(manifest)
        current["groups"][0]["members"].pop()
        with self.assertRaises(corpus.CorpusError):
            audit.validate(rows, current, aliases, summary)

    def test_frozen_assisted_review_rejects_staleness_or_changed_review_claims(self):
        rows = self.bundle[0]
        review = json.loads((ROOT / "data/synthetic-v1/label-review.json").read_text())
        self.assertEqual(audit.validate_review(rows, review), 32)
        for field, value in (("source_sha256", "wrong"), ("label", "uncertain"),
                             ("decision", "independently_verified")):
            changed = deepcopy(review)
            changed["entries"][0][field] = value
            with self.assertRaises(corpus.CorpusError):
                audit.validate_review(rows, changed)
        changed = deepcopy(review)
        changed["reviewer"] = "Independent human panel"
        with self.assertRaises(corpus.CorpusError):
            audit.validate_review(rows, changed)

    def test_uncertain_rows_never_enter_labelled_matrices(self):
        rows, manifest, _, _ = self.bundle
        for partition in ("train", "validation", "test"):
            _, matrix, labels = audit.matrix_for(rows, manifest, partition)
            self.assertEqual(len(matrix), len(labels))
            self.assertNotIn("uncertain", labels)
            self.assertTrue(all(len(vector) == 8 for vector in matrix))


if __name__ == "__main__":
    unittest.main()
