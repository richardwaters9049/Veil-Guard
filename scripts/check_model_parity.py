"""Compare native inference with frozen Python on approved synthetic vectors only."""
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/experiments"))
import common
from learning import ExactKNN


def compare(bundle, queries, offline):
    model = ExactKNN.from_bundle(bundle)
    command = ["cargo", "run", "--quiet", "--locked"]
    if offline:
        command.append("--offline")
    command.extend(["--example", "model_predictions"])
    process = subprocess.run(command, cwd=ROOT,
                             input=json.dumps({"model": bundle, "queries": queries}),
                             text=True, capture_output=True, timeout=120, check=False)
    if process.returncode:
        raise AssertionError("native_bridge_failed")
    native = json.loads(process.stdout)
    expected = model.predict(queries, bundle["policy"])
    assert len(native) == len(expected)
    maximum = 0.0
    for actual, reference, info, query in zip(native, expected, model.neighbours(queries), queries):
        for key, value in reference.items():
            if key in ("score", "nearest"):
                error = abs(actual[key] - value)
                maximum = max(maximum, error)
                assert math.isclose(actual[key], value, rel_tol=1e-12, abs_tol=1e-9), key
            else:
                assert actual[key] == value, key
        assert [n["id"] for n in actual["neighbours"]] == model.ids[info["indices"]].tolist()
        assert [n["label"] for n in actual["neighbours"]] == model.y[info["indices"]].tolist()
        z = (query-model.mean)/model.scale
        for neighbour, index, distance in zip(actual["neighbours"], info["indices"], info["distances"]):
            assert math.isclose(neighbour["distance"], distance, rel_tol=1e-12, abs_tol=1e-9)
            contributions = (model.z[index]-z)**2
            for a, b in zip(neighbour["contributions"], contributions):
                assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)
    return len(queries), maximum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    rows, _ = common.approved_data()
    directory = ROOT / "research/results/synthetic-v1/development"
    bundles = [common.load_json(directory / "model.json"),
               common.load_json(directory / "baselines.json")["raw_knn"]]
    # No fitting or selection: query frozen exports with every eligible corpus row.
    queries = [r["features"] for r in rows if r["features"] is not None]
    total, maximum = 0, 0.0
    for bundle in bundles:
        count, error = compare(bundle, queries, args.offline)
        total += count
        maximum = max(maximum, error)
    metadata = {"model_id":"authored-parity", "corpus_source_sha256":"a"*64,
                "protocol_sha256":"b"*64}
    policy = {"review_all":False, "margin":0.0, "distance_limit":10.0,
              "selection_status":"baseline_fixed"}
    cases = [
        ([[1,0,0,0,0,0,0,0],[0,2,0,0,0,0,0,0],[0,0,2,0,0,0,0,0]], [1,1,0], ["A","B","C"], 3),
        ([[0]*8]*3, [1,0,1], ["C","A","B"], 1),
        ([[-1]+[0]*7,[1]+[0]*7], [1,0], ["Z","A"], 1),
    ]
    for x, labels, ids, k in cases:
        for weights in ("uniform", "inverse_distance"):
            model = ExactKNN(x, labels, ids, k, weights, standardised=False)
            count, error = compare(model.bundle(metadata, policy), [[0]*8,[20]*8], args.offline)
            total += count
            maximum = max(maximum, error)
    print(f"Native/reference model parity passed: {total} predictions; maximum score/distance error {maximum:.3g}.")
    print("Synthetic vectors only; this does not change the failed benefit gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
