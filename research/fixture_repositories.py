"""Materialise ONLY authored rows into new, isolated, staged Git fixtures."""
from collections import defaultdict
import os
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

import corpus


def git_environment():
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                       GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    return environment


def git(arguments, environment):
    result = subprocess.run(["git", *arguments], env=environment, capture_output=True, check=False)
    corpus.require(result.returncode == 0, "fixture_git_operation_failed")
    return result.stdout


def materialise(rows, destination):
    destination = Path(destination)
    corpus.require(not destination.exists() and not destination.is_symlink(), "fixture_output_exists")
    grouped = defaultdict(list)
    for row in rows:
        corpus.require(re.fullmatch(r"(?:repo|challenge-repo)-[0-9]{2}", row["repository_id"]) is not None)
        corpus.require(re.fullmatch(r"vg-[0-9a-f]{24}", row["id"]) is not None)
        corpus.require(row["provenance"] == "authored_offline_synthetic")
        grouped[row["repository_id"]].append(row)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    environment = git_environment()
    records = []
    with tempfile.TemporaryDirectory(prefix="veilguard-empty-template-") as template:
        for identifier, selected in sorted(grouped.items()):
            root = destination / identifier
            root.mkdir(mode=0o700)
            git(["init", "--quiet", "--object-format=sha1", "--initial-branch=main",
                 "--template=" + template, str(root)], environment)
            for row in sorted(selected, key=lambda r: r["id"]):
                path = root / (row["id"] + ".fixture")
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(row["source"] + "\n")
            git(["-C", str(root), "-c", "core.hooksPath=" + os.devnull, "add", "--all"], environment)
            records.append({"repository_id": identifier, "directory": identifier,
                            "staged_fixture_files": len(selected), "head": "unborn", "object_format": "sha1"})
    return {"schema": "veilguard.fixture-repositories.v1", "repositories": records,
            "git_version": git(["--version"], environment).decode("ascii").strip(),
            "source_sha256": corpus.source_digest(rows), "policy": "New authored-only worktrees; inherited Git overrides/config/templates disabled."}


def verify_staged(rows, metadata, destination):
    """Check every staged SHA-1 blob against the authored UTF-8/LF bytes."""
    corpus.require(metadata["schema"] == "veilguard.fixture-repositories.v1")
    corpus.require(metadata["source_sha256"] == corpus.source_digest(rows))
    grouped = defaultdict(dict)
    for row in rows:
        grouped[row["repository_id"]][row["id"] + ".fixture"] = row
    corpus.require(set(grouped) == {r["repository_id"] for r in metadata["repositories"]})
    environment = git_environment()
    for entry in metadata["repositories"]:
        repository = entry["repository_id"]
        corpus.require(entry["directory"] == repository)
        expected = grouped[repository]
        root = Path(destination) / repository
        staged = git(["-C", str(root), "ls-files", "--stage", "-z"], environment)
        observed = set()
        for item in staged.split(b"\0"):
            if not item:
                continue
            header, name = item.split(b"\t", 1)
            mode, oid, stage = header.split()
            name = name.decode("ascii")
            corpus.require(mode == b"100644" and stage == b"0" and name in expected and name not in observed,
                           "staged_fixture_structure_mismatch")
            data = (expected[name]["source"] + "\n").encode("utf-8")
            blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            corpus.require(oid.decode("ascii") == hashlib.sha1(blob).hexdigest(), "staged_fixture_content_mismatch")
            corpus.require((root / name).read_bytes() == data, "fixture_worktree_changed")
            observed.add(name)
        corpus.require(observed == set(expected) and entry["staged_fixture_files"] == len(observed))
    return len(metadata["repositories"])
