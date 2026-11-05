"""Checksum-pinned Gitleaks reference; authored snapshots only, never user code."""
from collections import Counter
import hashlib
import io
import os
from pathlib import Path
import platform
import re
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen

import common
from learning import require
import fixture_repositories


def tool_asset():
    lock = common.load_json(common.EXPERIMENT / "gitleaks-lock.json")
    key = platform.system() + "-" + platform.machine()
    require(key in lock["assets"], "unsupported_external_tool_platform")
    return lock, lock["assets"][key]


def binary_from_archive(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.getmember("gitleaks")
        require(member.isfile() and 0 < member.size <= 64 * 1024 * 1024, "invalid_external_archive")
        handle = archive.extractfile(member)
        require(handle is not None)
        return handle.read()


def setup_tool(output):
    lock, asset = tool_asset()
    destination = common.new_directory(output)
    url = "https://github.com/gitleaks/gitleaks/releases/download/v" + lock["version"] + "/" + asset["name"]
    with urlopen(url, timeout=60) as response:
        archive = response.read(64 * 1024 * 1024 + 1)
    require(len(archive) <= 64 * 1024 * 1024 and hashlib.sha256(archive).hexdigest() == asset["sha256"],
            "external_checksum_mismatch")
    binary = binary_from_archive(archive)
    for name, data in (("archive.tar.gz", archive), ("gitleaks", binary)):
        descriptor = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700 if name == "gitleaks" else 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
    metadata = {"schema": "veilguard.external-tool-install.v1", "version": lock["version"],
                "asset": asset["name"], "archive_sha256": asset["sha256"],
                "binary_sha256": hashlib.sha256(binary).hexdigest()}
    common.save_new(destination / "tool.json", metadata)
    return metadata


def verified_tool(directory):
    directory = Path(directory)
    lock, asset = tool_asset()
    archive = directory / "archive.tar.gz"
    require(archive.is_file() and archive.stat().st_size <= 64 * 1024 * 1024, "external_archive_missing")
    data = archive.read_bytes()
    require(hashlib.sha256(data).hexdigest() == asset["sha256"], "external_checksum_mismatch")
    expected = hashlib.sha256(binary_from_archive(data)).hexdigest()
    require(common.sha_file(directory / "gitleaks") == expected, "external_binary_changed")
    metadata = common.load_json(directory / "tool.json")
    require(metadata["archive_sha256"] == asset["sha256"] and metadata["binary_sha256"] == expected
            and metadata["version"] == lock["version"])
    return directory / "gitleaks", metadata


def scan(rows, directory):
    require(rows and all(r["partition"] == "test" for r in rows), "external_scope_not_test")
    binary, metadata = verified_tool(directory)
    by_id = {r["id"]: r for r in rows}
    with tempfile.TemporaryDirectory(prefix="veilguard-gitleaks-reference-") as temporary:
        root = Path(temporary)
        snapshot = root / "snapshot"
        snapshot.mkdir(mode=0o700)
        for row in rows:
            require(re.fullmatch(r"repo-[0-9]{2}", row["repository_id"]) is not None)
            target = snapshot / row["repository_id"]
            target.mkdir(mode=0o700, exist_ok=True)
            (target / (row["id"] + ".fixture")).write_text(row["source"] + "\n", encoding="utf-8")
        report = root / "redacted.json"
        environment = {k: v for k, v in fixture_repositories.git_environment().items()
                       if not k.startswith("GITLEAKS")}
        arguments = [str(binary.resolve()), "dir", "--redact=100", "--no-banner",
                     "--report-format=json", "--report-path=" + str(report), "--exit-code=1", str(snapshot)]
        result = subprocess.run(arguments, cwd=root, env=environment, capture_output=True, check=False)
        require(result.returncode in (0, 1), "external_scan_failed")
        found = common.load_json(report) if report.exists() else []
        require(isinstance(found, list), "external_report_mismatch")
        matches, counts = set(), Counter()
        for finding in found:
            identifier = Path(finding["File"]).name.removesuffix(".fixture")
            require(identifier in by_id, "external_unknown_fixture")
            rule = finding["RuleID"]
            require(isinstance(rule, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", rule) is not None)
            matches.add(identifier)
            counts[rule] += 1
    return matches, {"schema": "veilguard.external-reference.v1", "tool": metadata,
                     "configuration": "embedded_defaults; no environment/local snapshot overrides",
                     "scope": "authored_test_directory_snapshot_of_verified_staged_source; excludes_git_metadata",
                     "redaction": "100_percent; raw_external_report_not_retained",
                     "finding_occurrences": sum(counts.values()), "matched_fixtures": len(matches),
                     "rule_counts": dict(sorted(counts.items())),
                     "comparison_limit": "different detection scope and policy; not a direct replacement claim"}
