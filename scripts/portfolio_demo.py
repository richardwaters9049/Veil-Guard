"""Rehearse the portfolio demo using an authored temporary repository."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import release_support as support


def rehearse():
    """Return the validated terminal scenes in presentation order."""
    scenes = [
        ("Veil Guard | staged credential review", 8),
        ("This demo uses a disposable repository and authored nonfunctional values.", 8),
    ]
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
        blocking = next(finding for finding in report["findings"] if finding["policy"] == "block")
        scenes.append((
            "The working-tree copy is clean. The staged copy still triggers a blocking rule.\n"
            f"{blocking['path']}:{blocking['staged_line']} [{blocking['rule_id']}] [REDACTED]\n"
            f"Exit {scan.returncode}. Coverage complete. {len(ranked)} generic reviews.",
            16,
        ))
        scenes.append((explanation.stdout.decode().strip(), 28))
        support.git(repository, "add", "--", "blocking.txt")
        after = support.run(command, env=support.clean_env())
        clean_report = json.loads(after.stdout)
        assert clean_report["coverage_complete"]
        assert all(finding["policy"] == "review" for finding in clean_report["findings"])
        scenes.append((
            "After staging the clean copy, the blocking finding is gone. Generic reviews remain.\n"
            "Exit 0. Coverage complete.",
            12,
        ))
    evidence = support.ROOT / "research/results/phase-six/benchmark-exact-selection-macos-arm64/benchmark.json"
    benchmark = json.loads(evidence.read_text())
    largest = next(
        row for row in benchmark["workloads"] if row["rows"] == 10000 and row["model_enabled"]
    )
    scenes.extend([
        (
            "The eight squared coordinate differences add up to squared Euclidean distance.\n"
            "On held-out synthetic fixtures, KNN reached 0.539 mean Precision@20 vs 0.500 for entropy.\n"
            "The relative gain missed the 10% target and the paired interval crossed zero.",
            17,
        ),
        (
            f"Local {benchmark['cpu']} benchmark with 10,000 model-scored candidates\n"
            f"p95 {largest['p95_seconds_nearest_rank']:.3f} s, "
            f"peak RSS {largest['maximum_peak_rss_bytes'] / 1024**2:.1f} MiB.\n"
            "The model remains experimental. See the repository for raw runs and methods.",
            16,
        ),
    ])
    return scenes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, help="Write a new paced asciicast v2 recording")
    args = parser.parse_args()
    scenes = rehearse()
    if args.record is None:
        for output, _ in scenes:
            print(output)
        return 0

    elapsed = 0
    with args.record.open("x", encoding="utf-8") as recording:
        header = {"version": 2, "width": 100, "height": 36, "title": "Veil Guard portfolio demo"}
        recording.write(json.dumps(header) + "\n")
        for output, duration in scenes:
            text = "\x1b[2J\x1b[H" + output.replace("\n", "\r\n") + "\r\n"
            recording.write(json.dumps([elapsed, "o", text]) + "\n")
            elapsed += duration
        recording.write(json.dumps([elapsed, "o", "\r\n"]) + "\n")
    print(f"Recorded {elapsed} seconds to {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
