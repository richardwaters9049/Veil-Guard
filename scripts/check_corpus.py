"""Rebuild and audit the frozen synthetic corpus. Print aggregate counts only."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import corpus
import corpus_audit
import fixture_repositories


def main():
    try:
        rows, manifest, dedup, summary = corpus.build()
        corpus_audit.validate(rows, manifest, dedup, summary)
        # Regenerate source identities/splits without a second floating-point extraction.
        again, repeated, repeated_dedup, _ = corpus.build(include_features=False)
        corpus.require(manifest == repeated and dedup == repeated_dedup, "nondeterministic_recipe")
        corpus.require(corpus.source_digest(rows) == corpus.source_digest(again))
        for name, actual in (("split-manifest.json", manifest), ("deduplication.json", dedup), ("summary.json", summary)):
            expected = json.loads((ROOT / "data/synthetic-v1" / name).read_text())
            corpus.require(actual == expected, "frozen_corpus_artifact_changed")
        review = json.loads((ROOT / "data/synthetic-v1/label-review.json").read_text())
        reviewed = corpus_audit.validate_review(rows, review)
        with tempfile.TemporaryDirectory(prefix="veilguard-corpus-acceptance-") as temporary:
            destination = Path(temporary) / "repositories"
            materialised = fixture_repositories.materialise(rows, destination)
            repository_count = fixture_repositories.verify_staged(rows, materialised, destination)
        for partition in ("train", "validation", "test"):
            ids, matrix, labels = corpus_audit.matrix_for(rows, manifest, partition)
            corpus.require(len(ids) == len(matrix) == len(labels))
            corpus.require(all(len(vector) == 8 for vector in matrix))
    except (corpus.CorpusError, OSError, ValueError, TypeError, KeyError, OverflowError):
        print("Corpus check failed: frozen identity, safety, schema, review, numeric or split contract mismatch.",
              file=sys.stderr)
        return 1
    counts = summary["partitions"]
    print(f"Corpus checks passed: {summary['canonical_records']} canonical rows; "
          f"{summary['exact_duplicates_removed']} exact duplicates removed; "
          f"{summary['families']} families; {summary['repositories']} fixture repositories.")
    print("Partitions: " + ", ".join(f"{key}={value['records']} rows/{value['groups']} groups"
                                   for key, value in counts.items()) + ".")
    print(f"{repository_count} authored Git worktrees materialised; every staged SHA-1 blob matches its fixture source.")
    print(f"{reviewed} stratified assisted label reviews; 8-column matrices; no cross-split relations.")
    print("Synthetic-only engineering evidence. No training, detection metric or independent human label audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
