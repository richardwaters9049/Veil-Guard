"""Check independent eight-feature implementations against authored golden cases.

Only compiled-in synthetic fixture vectors cross the Rust/Python boundary.
This is not a model, accuracy benchmark or production vector-export command.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
import feature_reference as reference


class ParityError(ValueError):
    pass


def require(condition):
    if not condition:
        raise ParityError("feature_contract_mismatch")


def compare(actual, expected):
    if isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected) == 8)
        return max(compare(a, b) for a, b in zip(actual, expected))
    if expected is None:
        require(actual is None)
        return 0.0
    require(type(actual) in (float, int) and math.isfinite(actual))
    require(type(expected) in (float, int) and math.isfinite(expected))
    error = abs(actual - expected)
    require(error <= 1e-9)
    return error


def check(fixtures, actual, contract):
    require(fixtures["schema"] == "veilguard.feature-fixtures.v1")
    require(fixtures["feature_schema"] == actual["feature_schema"] == contract["schema_version"] == reference.SCHEMA)
    require(actual["schema"] == "veilguard.feature-parity.v1")
    require(contract["dimension"] == 8 and fixtures["tolerance"] == 1e-9)
    names = [f["name"] for f in contract["features"]]
    require(names == actual["names"] == list(reference.NAMES) and len(names) == 8)
    require([f["index"] for f in contract["features"]] == list(range(8)))
    require(contract["keyword_vocabulary"] == actual["keywords"] == list(reference.KEYWORDS))
    require(contract["placeholder_vocabulary"] == actual["placeholders"] == list(reference.PLACEHOLDERS))
    require(contract["candidate"] == {"encoding": "printable_ascii_0x20_to_0x7e",
                                    "min_length": 8, "max_length": 256, "unsupported": "review_without_vector"})
    expected_ranges = [(math.log(9), math.log(257)), (0, math.log2(95))] + [(0, 1)] * 6
    for feature, (low, high) in zip(contract["features"], expected_ranges):
        require(abs(feature["minimum"] - low) <= 1e-12 and abs(feature["maximum"] - high) <= 1e-12)
    errors = []
    for section in ("cases", "distance_cases"):
        ids = [case["id"] for case in fixtures[section]]
        require(ids and len(ids) == len(set(ids)))
        require(ids == [case["id"] for case in actual[section]])
    for case, rust in zip(fixtures["cases"], actual["cases"]):
        require(case["kind"] in ("features", "proximity"))
        function = reference.from_line if case["kind"] == "features" else reference.keyword_proximity
        try:
            python = function(case["line"], case["start"], case["end"])
        except reference.FeatureError:
            python = None
        errors.extend([compare(python, case["expected"]), compare(rust["actual"], case["expected"]),
                       compare(rust["actual"], python)])
        if isinstance(rust["actual"], list):
            require(len(rust["actual"]) == 8)
            for coordinate, feature in zip(rust["actual"], contract["features"]):
                require(feature["minimum"] - 1e-12 <= coordinate <= feature["maximum"] + 1e-12)
    for case, rust in zip(fixtures["distance_cases"], actual["distance_cases"]):
        z = reference.standardise(case["values"], case["means"], case["scales"])
        terms = reference.squared_distance_contributions(z, case["neighbour"])
        for observed, expected in [(z, case["expected_standardised"]),
                                   (terms, case["expected_contributions"]),
                                   (sum(terms), case["expected_squared_distance"]),
                                   (rust["standardised"], z), (rust["contributions"], terms),
                                   (rust["squared_distance"], sum(terms))]:
            errors.append(compare(observed, expected))
    return max(errors)


def reject_constant(_value):
    raise ParityError("non_finite_json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    command = ["cargo", "run", "--quiet", "--locked", "--example", "feature_fixtures"]
    if args.offline:
        command.append("--offline")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        print("Rust synthetic-fixture harness failed.", file=sys.stderr)
        return 1
    try:
        fixtures = json.loads((ROOT / "research/fixtures/features-v1.json").read_text(), parse_constant=reject_constant)
        contract = json.loads((ROOT / "schemas/feature-contract.json").read_text(), parse_constant=reject_constant)
        actual = json.loads(result.stdout, parse_constant=reject_constant)
        error = check(fixtures, actual, contract)
    except (ParityError, KeyError, TypeError, ValueError, OverflowError):
        print("Feature parity failed: schema, order, fixture status or numeric contract mismatch.", file=sys.stderr)
        return 1
    print(f"Feature parity passed: 8 coordinates; {len(fixtures['cases'])} feature/context cases; "
          f"{len(fixtures['distance_cases'])} distance cases; maximum absolute error {error:.3g} (limit 1e-9).")
    print("Authored synthetic fixtures only; no trained model or accuracy result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
