"""Fixed approved data access, bounded JSON and artifact identity."""
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "research/experiments"
sys.path.insert(0, str(ROOT / "research"))
import corpus
import corpus_audit
from learning import require, ResearchError

CORE_FILES = ("common.py", "learning.py", "metrics.py", "development.py", "evaluation.py",
              "external_reference.py", "run_experiment.py", "protocol.json", "gitleaks-lock.json",
              "pyproject.toml", "uv.lock", "research_audit.py")


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def identity(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def reject_constant(_value):
    raise ResearchError("non_finite_json")


def load_json(path, maximum=16 * 1024 * 1024):
    path = Path(path)
    require(path.is_file() and path.stat().st_size <= maximum, "artifact_size_or_type")
    data = path.read_bytes()
    require(len(data) <= maximum, "artifact_size_or_type")
    return json.loads(data, parse_constant=reject_constant)


def save_new(path, value):
    data = json_bytes(value)
    require(len(data) <= 16 * 1024 * 1024, "artifact_size_limit")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def new_directory(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), "output_must_be_new")
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    return path


def protocol():
    p = load_json(EXPERIMENT / "protocol.json")
    require(p["schema"] == "veilguard.experiment-protocol.v1" and p["feature_schema"] == "veilguard.features.v1")
    return p


def core_hashes():
    return {name: sha_file(EXPERIMENT / name) for name in CORE_FILES}


def approved_data():
    rows, manifest, aliases, summary = corpus.build()
    corpus_audit.validate(rows, manifest, aliases, summary)
    for name, actual in (("split-manifest.json", manifest), ("deduplication.json", aliases), ("summary.json", summary)):
        require(load_json(ROOT / "data/synthetic-v1" / name) == actual, "frozen_corpus_mismatch")
    corpus_audit.validate_review(rows, load_json(ROOT / "data/synthetic-v1/label-review.json"))
    require(manifest["source_sha256"] == protocol()["corpus_source_sha256"])
    return rows, manifest


def environment():
    import numpy
    import sklearn
    import scipy
    return {"python": platform.python_version(), "os": platform.system(), "machine": platform.machine(),
            "numpy": numpy.__version__, "scikit_learn": sklearn.__version__, "scipy": scipy.__version__,
            "thread_policy": "BLAS/OpenMP limited to one thread", "experiment_lock_sha256": sha_file(EXPERIMENT / "uv.lock")}


def arrays(rows):
    import numpy as np
    require(bool(rows) and all(r["label"] in ("sensitive_candidate", "benign_fixture") for r in rows))
    return (np.asarray([r["features"] for r in rows], dtype=np.float64),
            np.asarray([int(r["label"] == "sensitive_candidate") for r in rows], dtype=np.int64),
            [r["id"] for r in rows])


def require_development(rows):
    require(rows and all(r["partition"] in ("train", "validation") for r in rows), "held_out_data_in_development")
    require(all(r["label"] in ("sensitive_candidate", "benign_fixture") for r in rows), "uncertain_in_development")
    scopes = {}
    for row in rows:
        if row["group_id"] in scopes:
            require(scopes[row["group_id"]] == row["partition"], "group_scope_overlap")
        scopes[row["group_id"]] = row["partition"]
