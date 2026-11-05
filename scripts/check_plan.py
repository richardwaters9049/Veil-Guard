"""Validate planning links, feature metadata and the fabricated KNN arithmetic.
This is not a scanner test or model benchmark. Python standard library only.
"""
from pathlib import Path
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]

def main():
    contract = json.loads((ROOT / "schemas/feature-contract.json").read_text())
    names = ["log_length", "shannon_entropy", "digit_ratio", "uppercase_ratio",
             "symbol_ratio", "keyword_proximity", "sensitive_assignment",
             "placeholder_similarity"]
    assert contract["dimension"] == 8
    assert [f["name"] for f in contract["features"]] == names
    assert [f["index"] for f in contract["features"]] == list(range(8))
    assert all(f["minimum"] <= f["maximum"] for f in contract["features"])
    example = json.loads((ROOT / "examples/illustrative-vectors.json").read_text())
    assert len(example["query"]) == 8
    assert all(len(row["vector"]) == 8 for row in example["neighbors"])
    distances = [math.dist(example["query"], row["vector"])
                 for row in example["neighbors"]]
    assert distances == example["expected_distances"]
    vote = sum(1 / d for d, row in zip(distances, example["neighbors"])
               if row["label"] == "sensitive_candidate") / sum(1 / d for d in distances)
    assert math.isclose(vote, example["expected_sensitive_vote"], abs_tol=1e-12)
    checked = 0
    for doc in ROOT.rglob("*.md"):
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text()):
            if "://" in link or link.startswith("#"):
                continue
            target = (doc.parent / link.split("#")[0]).resolve()
            assert target.is_relative_to(ROOT), (doc, link)
            assert target.exists(), (doc, link)
            checked += 1
    print(f"Planning checks passed: 8 features, vote={vote}, {checked} local links.")
    print("No scanner functionality or model performance has been tested.")

if __name__ == "__main__":
    main()
