"""Ensure the gate refuses schema, ordering, dimension and numeric drift."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_feature_parity as gate


class ParityGate(unittest.TestCase):
    def setUp(self):
        self.fixtures = json.loads((ROOT / "research/fixtures/features-v1.json").read_text())
        self.contract = json.loads((ROOT / "schemas/feature-contract.json").read_text())
        self.actual = {
            "schema": "veilguard.feature-parity.v1", "feature_schema": gate.reference.SCHEMA,
            "names": list(gate.reference.NAMES), "keywords": list(gate.reference.KEYWORDS),
            "placeholders": list(gate.reference.PLACEHOLDERS),
            "cases": [{"id": c["id"], "actual": c["expected"]} for c in self.fixtures["cases"]],
            "distance_cases": [{"id": c["id"], "standardised": c["expected_standardised"],
                                "contributions": c["expected_contributions"],
                                "squared_distance": c["expected_squared_distance"]}
                               for c in self.fixtures["distance_cases"]],
        }

    def test_accepts_authored_contract(self):
        self.assertLessEqual(gate.check(self.fixtures, self.actual, self.contract), 1e-9)

    def test_rejects_artifact_drift(self):
        mutations = [
            lambda d: d.update(feature_schema="veilguard.features.v2"),
            lambda d: d.update(schema="unknown"),
            lambda d: d["names"].reverse(),
            lambda d: d["keywords"].append("new_word"),
            lambda d: d["placeholders"].pop(),
            lambda d: d["cases"].pop(),
            lambda d: d["cases"].reverse(),
            lambda d: d["cases"][0].update(id="duplicate"),
            lambda d: d["cases"][0].update(actual=None),
            lambda d: d["cases"][0]["actual"].append(0),
            lambda d: d["cases"][0]["actual"].pop(),
            lambda d: d["cases"][0]["actual"].__setitem__(0, float("nan")),
            lambda d: d["cases"][0]["actual"].__setitem__(0, float("inf")),
            lambda d: d["cases"][0]["actual"].__setitem__(0, True),
            lambda d: d["cases"][0]["actual"].__setitem__(0, 999),
            lambda d: d["distance_cases"][0]["contributions"].__setitem__(0, -1),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(gate.ParityError):
                altered = deepcopy(self.actual)
                mutate(altered)
                gate.check(self.fixtures, altered, self.contract)

    def test_rejects_contract_and_fixture_drift(self):
        for field, value in [("dimension", 9), ("schema_version", "unknown")]:
            altered = deepcopy(self.contract)
            altered[field] = value
            with self.assertRaises(gate.ParityError):
                gate.check(self.fixtures, self.actual, altered)
        altered = deepcopy(self.contract)
        altered["features"][0]["maximum"] = 999
        with self.assertRaises(gate.ParityError):
            gate.check(self.fixtures, self.actual, altered)
        altered = deepcopy(self.fixtures)
        altered["tolerance"] = 1
        with self.assertRaises(gate.ParityError):
            gate.check(altered, self.actual, self.contract)
        with self.assertRaises(gate.ParityError):
            json.loads('{"value": NaN}', parse_constant=gate.reject_constant)
