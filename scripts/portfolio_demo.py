"""Rehearse the portfolio demo using an authored temporary repository."""
import json
from pathlib import Path
import subprocess
import tempfile

import release_support as support


def main():
    with tempfile.TemporaryDirectory(prefix="veilguard-portfolio-") as temporary:
        repository = Path(temporary)
        support.fixture(repository, rows=10, blocking=True)
        (repository / "blocking.txt").write_text("clean working-tree copy\n")
        command = [str(support.BINARY), "scan", "--staged", "--repo", str(repository),
                   "--format", "json", "--model", str(support.MODEL), "--explanations"]
        before = support.snapshot(repository)
        scan = subprocess.run(command, env=support.clean_env(), capture_output=True, timeout=30)
        report = json.loads(scan.stdout)
        assert scan.returncode == 1 and report["coverage_complete"]
        assert b"ghp_" + b"A" * 36 not in scan.stdout + scan.stderr
        assert any(finding["policy"] == "block" for finding in report["findings"])
        ranked = [finding for finding in report["findings"] if finding["model"] is not None]
        assert len(ranked) == 10
        assert all(finding["review_reason"] == "validation_policy_unmet" for finding in ranked)
        first = min(ranked, key=lambda finding: finding["model"]["rank"])
        saved = repository / "report.json"
        support.save(saved, report)
        explanation = support.run([support.BINARY, "explain", "--report", saved,
                                   "--finding", first["id"]], env=support.clean_env())
        assert b"squared contribution" in explanation.stdout
        assert before == support.snapshot(repository)
        print("The working-tree copy is clean. The staged copy still triggers a blocking rule.")
        print(explanation.stdout.decode(), end="")
        support.git(repository, "add", "--", "blocking.txt")
        after = support.run(command, env=support.clean_env())
        clean_report = json.loads(after.stdout)
        assert clean_report["coverage_complete"]
        assert all(finding["policy"] == "review" for finding in clean_report["findings"])
        print("After staging the clean copy, the blocking finding is gone. Generic reviews remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
