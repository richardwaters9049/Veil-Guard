"""Exercise the optimized scanner on an isolated, authored Git fixture."""
from pathlib import Path
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/release/veilguard"


def git(directory, args, environment):
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
         "-C", str(directory), *args],
        env=environment, capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError("Fixture Git operation failed; details withheld.")


def run_case(directory, expected, synthetic_value):
    index = directory / ".git/index"
    before = index.read_bytes()
    result = subprocess.run(
        [str(BINARY), "scan", "--staged", "--repo", str(directory), "--format", "json"],
        capture_output=True, check=False,
    )
    assert result.returncode == expected, "Unexpected release scan status."
    assert synthetic_value.encode() not in result.stdout + result.stderr, "Fixture value was exposed."
    assert index.read_bytes() == before, "Release scan modified the index."
    report = json.loads(result.stdout)
    assert report["report_schema"] == "veilguard.report.v2"
    assert report["coverage_complete"] and not report["issues"]
    return report


def main():
    # Build/tests may use subprocesses; the shipped scan path does not use this helper.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    synthetic = "ghp_" + "A" * 36  # Authored, unprovisioned fixture; never validated.
    with tempfile.TemporaryDirectory(prefix="veilguard-smoke-") as temporary:
        directory = Path(temporary)
        template = directory / "empty-template"
        template.mkdir()
        git(directory, ["init", "--quiet", "--initial-branch=main", f"--template={template}"], environment)
        source = directory / "fixture.txt"
        source.write_text(f'token = "{synthetic}"\n')
        git(directory, ["add", "--", "fixture.txt"], environment)
        source.write_text("plain = short\n")
        report = run_case(directory, 1, synthetic)
        assert any(finding["policy"] == "block" for finding in report["findings"])
        assert source.read_text() == "plain = short\n", "Release scan modified the working tree."
        git(directory, ["add", "--", "fixture.txt"], environment)
        source.write_text(f'token = "{synthetic}"\n')
        report = run_case(directory, 0, synthetic)
        assert not report["findings"], "Working-tree-only content was scanned."
    print("Optimized scan smoke checks passed: staged-only reading, redaction and no index/worktree edits.")


if __name__ == "__main__":
    main()
