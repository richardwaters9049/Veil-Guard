"""Validate planning links, source metadata and fabricated KNN arithmetic.

This is documentation validation, not a scanner test, external-link checker,
source-entailment review or model benchmark. Python standard library only.
"""
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import math
import re
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def heading_slug(heading):
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


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

    registry = json.loads((ROOT / "docs/references.json").read_text())
    assert registry["schema"] == "veilguard.references.v1"
    records = registry["sources"]
    ids = [row["id"] for row in records]
    assert ids and len(ids) == len(set(ids)), "Duplicate or empty source register"
    for row in records:
        assert re.fullmatch(r"R\d{2}", row["id"]), row["id"]
        for field in ("citation", "type", "url", "reviewed", "supports", "limits", "checked_on"):
            assert isinstance(row[field], str) and row[field].strip(), (row["id"], field)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["checked_on"])
        for field in ("url", "metadata_url", "additional_url"):
            if row.get(field):
                parsed = urlsplit(row[field])
                assert parsed.scheme == "https" and parsed.netloc, (row["id"], field)

    bibliography = ROOT / "docs/13-sources.md"
    source_anchors = re.findall(r'<a id="(r\d{2})"></a>', bibliography.read_text())
    assert len(source_anchors) == len(set(source_anchors)), "Duplicate source anchors"
    assert set(source_anchors) == {value.lower() for value in ids}, "Source index mismatch"
    linked_ids = set()
    checked = 0
    # Check authored files, including untracked work; skip ignored build/dependency trees.
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"],
        cwd=ROOT,
    )
    documents = [ROOT / os.fsdecode(name) for name in names.split(b"\0") if name]
    for doc in documents:
        content = doc.read_text()
        doc_source_ids = set()
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (doc.parent / unquote(parsed.path)).resolve() if parsed.path else doc
            assert target.is_relative_to(ROOT), (doc, link)
            assert target.is_file(), (doc, link)
            if parsed.fragment:
                assert target.suffix == ".md", (doc, link)
                target_text = target.read_text()
                anchors = set(re.findall(r'<a id="([^"]+)"></a>', target_text))
                anchors.update(heading_slug(h) for h in
                               re.findall(r"^#{1,6} (.+)$", target_text, flags=re.MULTILINE))
                assert unquote(parsed.fragment) in anchors, (doc, link, "Missing anchor")
                if target == bibliography and re.fullmatch(r"r\d{2}", parsed.fragment):
                    source_id = parsed.fragment.upper()
                    assert source_id in ids, (doc, source_id)
                    linked_ids.add(source_id)
                    doc_source_ids.add(source_id)
            checked += 1
        if doc != bibliography:
            assert doc_source_ids, (doc, "No linked source citation")
    assert linked_ids == set(ids), ("Uncited sources", set(ids) - linked_ids)
    print(f"Planning checks passed: 8 features, vote={vote}, {checked} local links/anchors, "
          f"{len(records)} cited sources, {len(documents)} Markdown documents.")
    print("This check does not test scanner functionality, external-link availability, "
          "source entailment or model performance.")


if __name__ == "__main__":
    main()
