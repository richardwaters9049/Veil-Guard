import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research"))
import feature_reference as reference


class Features(unittest.TestCase):
    def test_authored_fixtures(self):
        fixture = json.loads((ROOT / "research/fixtures/features-v1.json").read_text())
        self.assertEqual(fixture["feature_schema"], reference.SCHEMA)
        for case in fixture["cases"]:
            with self.subTest(id=case["id"]):
                function = reference.keyword_proximity if case["kind"] == "proximity" else reference.from_line
                if case["expected"] is None:
                    with self.assertRaises(reference.FeatureError):
                        function(case["line"], case["start"], case["end"])
                else:
                    actual = function(case["line"], case["start"], case["end"])
                    expected = case["expected"]
                    if isinstance(expected, list):
                        self.assertEqual(len(actual), 8)
                        for a, b in zip(actual, expected):
                            self.assertTrue(math.isfinite(a) and abs(a-b) <= 1e-9)
                    else:
                        self.assertAlmostEqual(actual, expected, delta=1e-9)

    def test_invalid_context(self):
        for start, end in [(0, 0), (-1, 8), (8, 1), (0, 999), (1, 9), (True, 8)]:
            with self.subTest(start=start, end=end), self.assertRaisesRegex(reference.FeatureError, "^invalid_context$"):
                reference.from_line("é", start, end)
        with self.assertRaises(reference.FeatureError):
            reference.from_line(" " * 1_048_577, 1, 9)

    def test_invalid_vectors(self):
        for vector in [[0]*7, [0]*9, [math.nan]*8, [math.inf]*8, [True]*8, [10**1000]*8]:
            with self.subTest(length=len(vector)), self.assertRaises(reference.FeatureError):
                reference.standardise(vector, [0]*8, [1]*8)
            with self.assertRaises(reference.FeatureError):
                reference.squared_distance_contributions(vector, [0]*8)
        for scale in [0, -1, math.nan, math.inf]:
            with self.assertRaises(reference.FeatureError):
                reference.standardise([0]*8, [0]*8, [scale]*8)
        with self.assertRaises(reference.FeatureError):
            reference.standardise([sys.float_info.max]*8, [-sys.float_info.max]*8, [1]*8)
        with self.assertRaises(reference.FeatureError):
            reference.squared_distance_contributions([1e154]*8, [0]*8)

    def test_hand_worked_distance(self):
        fixture = json.loads((ROOT / "research/fixtures/features-v1.json").read_text())
        for case in fixture["distance_cases"]:
            z = reference.standardise(case["values"], case["means"], case["scales"])
            self.assertEqual(z, case["expected_standardised"])
            terms = reference.squared_distance_contributions(z, case["neighbour"])
            self.assertEqual(terms, case["expected_contributions"])
            self.assertEqual(sum(terms), case["expected_squared_distance"])
            self.assertEqual(reference.squared_distance_contributions(z, z), [0]*8)
            self.assertEqual(reference.squared_distance_contributions(case["neighbour"], z), terms)


if __name__ == "__main__":
    unittest.main()
