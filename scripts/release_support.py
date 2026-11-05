"""Shared development/release evidence helpers; never imported by the CLI."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/release/veilguard"
MODEL = ROOT / "research/results/synthetic-v1/development/model.json"


def run(command, **kwargs):
    return subprocess.run([str(c) for c in command], capture_output=True, check=True,
                          timeout=kwargs.pop("timeout", 120), **kwargs)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def new_directory(path):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError("output_must_be_new")
    path.mkdir(mode=0o700)
    return path


def identity():
    files = [ROOT / n for n in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml")]
    for pattern in ("src/**/*.rs", "scripts/**/*.py", "scripts/runtime/*.c", ".github/workflows/*.yml"):
        files.extend(ROOT.glob(pattern))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))}


def host():
    return {"system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "logical_cpus": os.cpu_count(),
            "python": platform.python_version()}


def now():
    return datetime.now(timezone.utc).isoformat()


def clean_env():
    env = {k:v for k,v in os.environ.items() if not k.startswith(("GIT_", "DYLD_", "LD_"))}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return env


def git(directory, *args):
    return run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                "-C", directory, *args], env=clean_env())


def fixture(directory, rows=100, blocking=False):
    directory = Path(directory)
    template = directory / "empty-template"
    template.mkdir()
    git(directory, "init", "--quiet", "--initial-branch=main", f"--template={template}")
    for start in range(0, rows, 500):
        content = "".join(f"fixture_{i:05} = 'VG_DEMO_{i:05}_AlphaBeta0123456789'\n"
                          for i in range(start, min(start+500, rows)))
        (directory / f"fixture-{start:05}.txt").write_text(content)
    if blocking:
        (directory / "blocking.txt").write_text("token = 'ghp_" + "A"*36 + "'\n")
    git(directory, "add", "--", "*.txt")


def snapshot(directory):
    directory = Path(directory)
    paths = list(directory.glob("*.txt")) + [directory / ".git/index", directory / ".git/config"]
    paths += [p for p in (directory / ".gitattributes", directory / ".git/hooks/pre-commit") if p.exists()]
    return {str(p.relative_to(directory)): sha(p) for p in sorted(paths)}
