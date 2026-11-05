"""Generate the approved synthetic recipe into a NEW private directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

import corpus
import corpus_audit
import fixture_repositories


def write_new(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory; existing paths are refused.")
    parser.add_argument("--materialise-repositories", action="store_true",
                        help="Create and stage disposable authored Git fixture worktrees.")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        print("Corpus output must be a new directory.", file=sys.stderr)
        return 2
    try:
        rows, manifest, dedup, summary = corpus.build()
        corpus_audit.validate(rows, manifest, dedup, summary)
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        write_new(args.output / "corpus.jsonl", "".join(corpus.canonical(row) for row in rows))
        for name, value in (("split-manifest.json", manifest), ("deduplication.json", dedup), ("summary.json", summary)):
            write_new(args.output / name, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
        if args.materialise_repositories:
            fixtures = fixture_repositories.materialise(rows, args.output / "repositories")
            fixture_repositories.verify_staged(rows, fixtures, args.output / "repositories")
            write_new(args.output / "fixture-repositories.json", json.dumps(fixtures, indent=2, sort_keys=True) + "\n")
        environment = {
            "schema": "veilguard.corpus-environment.v1",
            "materialised_fixture_repositories": args.materialise_repositories,
            "python": platform.python_version(), "os": platform.system(), "architecture": platform.machine(),
            "source_sha256": manifest["source_sha256"], "input_hashes": manifest["input_hashes"],
            "rust_toolchain_sha256": hashlib.sha256((corpus.ROOT / "rust-toolchain.toml").read_bytes()).hexdigest(),
            "cargo_lock_sha256": hashlib.sha256((corpus.ROOT / "Cargo.lock").read_bytes()).hexdigest(),
            "corpus_jsonl_sha256": hashlib.sha256((args.output / "corpus.jsonl").read_bytes()).hexdigest(),
            "numeric_identity": "f64 coordinates checked within 1e-9; source/splits byte-stable across supported platforms",
        }
        write_new(args.output / "environment.json", json.dumps(environment, indent=2, sort_keys=True) + "\n")
    except (corpus.CorpusError, OSError, ValueError, TypeError, KeyError):
        print("Corpus generation failed; no source values are included in this error.", file=sys.stderr)
        return 2
    print(f"Synthetic corpus generated: {len(rows)} canonical rows; {summary['groups']} groups; no model fitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
