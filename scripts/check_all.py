"""Run the development acceptance checks from the repository root.

This deliberately builds/tests this project. It is not part of scanner runtime.
--offline requires the pinned toolchain and Cargo dependencies to be installed.
"""
from pathlib import Path
import argparse
import platform
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use cached Cargo and uv dependencies.")
    args = parser.parse_args()
    uv = shutil.which("uv") or str(ROOT / ".venv/bin/uv")
    if not Path(uv).is_file():
        print("uv is required. Follow the Phase Two environment setup in README.md.", file=sys.stderr)
        return 1
    cargo_extra = ["--offline"] if args.offline else []
    checks = [
        ["git", "diff", "--check"],
        ["cargo", "fmt", "--all", "--check"],
        ["cargo", "clippy", "--all-targets", "--locked", *cargo_extra, "--", "-D", "warnings"],
        ["cargo", "test", "--locked", *cargo_extra],
        ["cargo", "build", "--release", "--locked", *cargo_extra],
        [uv, "run", "--locked", "--offline", "--project", "research", "--python", sys.executable,
         "python", "-m", "unittest", "discover", "-s", "research/tests", "-v"],
        [uv, "run", "--locked", "--offline", "--project", "research", "--python", sys.executable,
         "python", "scripts/check_feature_parity.py", *cargo_extra],
        [sys.executable, "scripts/check_plan.py"],
        [sys.executable, "scripts/smoke_scan.py"],
    ]
    print(f"Environment: {platform.system()} {platform.machine()}; Python {platform.python_version()}", flush=True)
    for command in checks:
        print("$ " + shlex.join(command), flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode:
            print("Acceptance check failed.", file=sys.stderr)
            return 1
    print("All local acceptance checks passed. These are not ML accuracy or sandbox guarantees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
