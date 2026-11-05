"""Verify frozen development and replay sealed evaluation without fitting models."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/experiments"))
import common
import research_audit
from run_experiment import verify_freeze


def main():
    development = ROOT / "research/results/synthetic-v1/development"
    evaluation = ROOT / "research/results/synthetic-v1/evaluation"
    verify_freeze(development)
    rows, manifest = common.approved_data()
    research_audit.development_artifacts(development, rows, manifest)
    report = research_audit.sealed_evaluation(evaluation, development, rows, manifest)
    print("Frozen research artifacts and sealed metric replay verified: "
          + report["benefit_gate"]["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
