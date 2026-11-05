"""Explicit development/finalisation commands. Existing outputs are never replaced."""
import os
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import subprocess
from threadpoolctl import threadpool_limits

import common
from development import develop
from evaluation import evaluate
import external_reference
from learning import ExactKNN, ResearchError, require


def verify_freeze(directory):
    directory = Path(directory)
    freeze = common.load_json(directory / "freeze.json")
    require(freeze["schema"] == "veilguard.experiment-freeze.v1")
    require(freeze["implementation_sha256"] == common.core_hashes(), "implementation_changed_since_freeze")
    require(freeze["protocol_sha256"] == common.sha_file(common.EXPERIMENT / "protocol.json"))
    expected_names = {"model.json", "baselines.json", "development.json", "development-predictions.json"}
    require(set(freeze["artifacts"]) == expected_names)
    for name, checksum in freeze["artifacts"].items():
        require(common.sha_file(directory / name) == checksum, "frozen_artifact_changed")
    return freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    setup = subcommands.add_parser("setup-tool")
    setup.add_argument("--output", type=Path, required=True)
    development = subcommands.add_parser("develop")
    development.add_argument("--output", type=Path, required=True)
    finalise = subcommands.add_parser("finalise")
    finalise.add_argument("--development", type=Path, required=True)
    finalise.add_argument("--output", type=Path, required=True)
    finalise.add_argument("--gitleaks", type=Path, required=True)
    finalise.add_argument("--scanner", type=Path, default=common.ROOT / "target/release/veilguard")
    args = parser.parse_args()
    try:
        if args.command == "setup-tool":
            metadata = external_reference.setup_tool(args.output)
            print("Pinned external tool prepared: Gitleaks " + metadata["version"])
            return 0
        output = common.new_directory(args.output)
        rows, manifest = common.approved_data()
        with threadpool_limits(limits=1):
            if args.command == "develop":
                selected = [r for r in rows if r["partition"] in ("train", "validation")]
                model, baselines, development, oof = develop(selected, manifest, common.protocol())
                payloads = {"model.json": model, "baselines.json": baselines,
                            "development.json": development, "development-predictions.json": oof}
                for name, payload in payloads.items():
                    common.save_new(output / name, payload)
                freeze = {
                    "schema": "veilguard.experiment-freeze.v1",
                    "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
                    "corpus_source_sha256": manifest["source_sha256"],
                    "protocol_sha256": common.sha_file(common.EXPERIMENT / "protocol.json"),
                    "implementation_sha256": common.core_hashes(),
                    "artifacts": {name: common.sha_file(output / name) for name in payloads},
                    "test_performance_access": "none",
                }
                common.save_new(output / "freeze.json", freeze)
                print("Development export frozen. Test performance has not been evaluated.")
            else:
                freeze = verify_freeze(args.development)
                require(freeze["corpus_source_sha256"] == manifest["source_sha256"])
                model = common.load_json(args.development / "model.json")
                baselines = common.load_json(args.development / "baselines.json")
                import research_audit
                research_audit.development_artifacts(args.development, rows, manifest)
                ExactKNN.from_bundle(model)
                ExactKNN.from_bundle(baselines["raw_knn"])
                report, records, challenge = evaluate(rows, manifest, model, baselines, args.gitleaks, args.scanner)
                common.save_new(output / "evaluation.json", report)
                common.save_new(output / "test-predictions.json", records)
                common.save_new(output / "challenge-predictions.json", challenge)
                seal = {
                    "schema": "veilguard.evaluation-seal.v1", "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "development_freeze_sha256": common.sha_file(args.development / "freeze.json"),
                    "implementation_sha256": common.core_hashes(),
                    "artifacts": {name: common.sha_file(output / name) for name in
                                  ("evaluation.json", "test-predictions.json", "challenge-predictions.json")},
                    "procedure": "frozen model/configuration; no fitting or tuning in finalise",
                }
                common.save_new(output / "evaluation-seal.json", seal)
                print("Held-out evaluation sealed: " + report["benefit_gate"]["decision"])
    except (ResearchError, ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError,
            TimeoutError, subprocess.TimeoutExpired):
        print("Experiment failed: approved-data, scope, artifact, numeric or output contract mismatch.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
