"""Record pinned dependency metadata, notices and dated advisory checks."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import release_support as s


def target():
    return s.run(["rustc","-vV"]).stdout.decode().split("host: ")[1].splitlines()[0]


def cargo_inventory():
    metadata=json.loads(s.run(["cargo","metadata","--locked","--offline","--format-version","1",
                               "--filter-platform",target()],cwd=s.ROOT).stdout)
    nodes={n["id"]:n for n in metadata["resolve"]["nodes"]}
    rows=[]
    notices={}
    for p in sorted(metadata["packages"],key=lambda p:p["name"]):
        root=Path(p["manifest_path"]).parent
        files=[]
        if p["name"] != "veilguard":
            for f in sorted(root.rglob("*")):
                if (f.is_file() and not f.is_symlink() and
                    f.name.upper().startswith(("LICENSE","LICENCE","COPYING","NOTICE","AUTHORS"))):
                    if f.stat().st_size > 2*1024*1024: raise ValueError("notice_size")
                    name=f"{p['name']}-{p['version']}/{f.relative_to(root)}"
                    notices[name]=f.read_bytes()
                    files.append({"path":name,"sha256":s.sha(f)})
        rows.append({"name":p["name"],"version":p["version"],"source":p["source"],
                     "declared_license":p["license"],"declared_license_file":p["license_file"],
                     "features":nodes[p["id"]]["features"],"notices":files})
    return rows,notices


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--no-fetch",action="store_true",help="Use cached RustSec DB, recording its identity.")
    parser.add_argument("--python-audit",action="store_true",help="Query PyPI using names/versions only via pinned pip-audit.")
    args=parser.parse_args()
    output=s.new_directory(args.output)
    rows,notices=cargo_inventory()
    audit=subprocess.run(["cargo","audit","--json",*(["--no-fetch"] if args.no_fetch else [])],
                         cwd=s.ROOT,capture_output=True,timeout=120)
    report=json.loads(audit.stdout)
    if audit.returncode not in (0,1): raise ValueError("advisory_check_failed")
    s.save(output/"rustsec.json",report)
    python=json.loads(s.run([s.ROOT/".venv/bin/uv","run","--locked","--offline","--project",
                             s.ROOT/"research/experiments","python",s.ROOT/"scripts/python_inventory.py"]).stdout)
    python_report=None
    if args.python_audit:
        requirements=output/"research-requirements.txt"
        requirements.write_text("".join(f"{p['name']}=={p['version']}\n" for p in python))
        result=subprocess.run([str(s.ROOT/".venv/bin/uv"),"tool","run","--from","pip-audit==2.10.1",
                               "pip-audit","--disable-pip","--no-deps","--progress-spinner","off",
                               "--format","json","--requirement",str(requirements)],
                              capture_output=True,timeout=180)
        if result.returncode not in (0,1): raise ValueError("python_advisory_check_failed")
        python_report=json.loads(result.stdout)
        s.save(output/"python-advisories.json",python_report)
    native=[r for r in rows if r["name"] in ("libgit2-sys","libz-sys")]
    s.save(output/"review.json",{"schema":"veilguard.dependency-review.v1","recorded_at":s.now(),
        "target":target(),"cargo_lock_sha256":s.sha(s.ROOT/"Cargo.lock"),
        "experiment_lock_sha256":s.sha(s.ROOT/"research/experiments/uv.lock"),
        "rustsec_fetch_requested":not args.no_fetch,
        "cargo_audit_version":s.run(["cargo","audit","--version"]).stdout.decode().strip(),
        "rust":rows,"python_research_only":python,"python_audit_performed":args.python_audit,
        "python_audit_tool":"pip-audit==2.10.1" if args.python_audit else None,
        "native_notice_review":native,
        "rustsec_vulnerabilities":report["vulnerabilities"]["count"],"rustsec_warnings":report["warnings"],
        "release_blockers":["Review third-party notice and redistribution obligations before public release.",
            "Corpus/model redistribution remains unapproved; exclude both from packages.",
            "Declared Rust wrapper licences do not replace native C component notices.",
            "Collected notices and metadata are not a legal compatibility determination.",
            "RustSec does not establish coverage of all bundled C or OS library vulnerabilities.",
            "Upstream zlib 1.4 security fixes require OS/native patch applicability review; version strings alone cannot establish backport status."],
        "notice_files":len(notices),"source_identity":s.identity()})
    print("Dependency review recorded; release/licence decisions remain explicit blockers.")
    return int(report["vulnerabilities"]["count"]>0 or bool(report["warnings"]) or
               bool(python_report and any(d.get("vulns") for d in python_report["dependencies"])))

if __name__=="__main__":
    raise SystemExit(main())
