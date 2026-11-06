"""Build twice, compare archive bytes, and test our own bundle in a fresh prefix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import package_development as p
import release_support as s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    output=s.new_directory(args.output)
    name,files=p.payload();one=p.archive_bytes(files);two=p.archive_bytes(files)
    assert one==two,"archive_assembly_not_deterministic"
    archive=output/(name+".tar.gz");archive.write_bytes(one)
    digest=hashlib.sha256(one).hexdigest()
    (output/"SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    members,manifest=p.verify(archive)
    with tempfile.TemporaryDirectory(prefix="veilguard-fresh-install-") as temporary:
        prefix=Path(temporary)/"application";prefix.mkdir()
        # Only the package just built from our trusted local binary is executed.
        for name,(data,mode) in members.items():
            destination=prefix/name;destination.parent.mkdir(parents=True,exist_ok=True)
            with destination.open("xb") as handle:handle.write(data)
            destination.chmod(mode)
        binary=prefix/"bin/veilguard"
        env=s.clean_env();env["PATH"]="/usr/bin:/bin"
        version=s.run([binary,"--version"],env=env).stdout.decode().strip()
        repository=Path(temporary)/"owned-fixture";repository.mkdir();s.fixture(repository,10,blocking=True)
        result=subprocess.run([str(binary),"scan","--staged","--repo",str(repository),"--format","json"],env=env,capture_output=True,timeout=30)
        assert result.returncode==1 and b"VG_DEMO_" not in result.stdout+result.stderr
        report=json.loads(result.stdout);assert report["coverage_complete"]
        assert report["model_status"]=="not_requested" and len(report["findings"])==11
        # Hook install refuses management overrides, so use ordinary clean invocation.
        hookenv={k:v for k,v in env.items() if not k.startswith("GIT_")}
        # Use empty per-test personal config, not the user's configuration.
        home=Path(temporary)/"home";home.mkdir()
        hookenv["HOME"]=str(home);hookenv["XDG_CONFIG_HOME"]=str(home/"xdg")
        for operation in ("install","uninstall"):
            s.run([binary,"hooks",operation,"--repo",repository],env=hookenv)
        saved=Path(temporary)/"saved.json";saved.write_text(json.dumps(report))
        s.run([binary,"explain","--report",saved,"--finding","finding-00001"],env=env)
        assert not (repository/".git/hooks/pre-commit").exists()
    s.save(output/"packaging.json",{"schema":"veilguard.packaging-evidence.v1","recorded_at":s.now(),
        "host":s.host(),"archive":archive.name,"sha256":digest,"archive_bytes":len(one),
        "assembly_reproducible_same_inputs":True,"fresh_prefix_scan_explain_hooks_passed":True,
        "binary_version":version,"binary_sha256":manifest["members"]["bin/veilguard"]["sha256"],"target":manifest["target"],"model_or_corpus_distributed":False,
        "limits":"Same-binary archive assembly reproducibility, not independent compiler build reproducibility. Fresh prefix on existing host, not a fresh OS. No release licence approval, signature, notarization or remote platform result implied."})
    print("Package checks passed: byte-identical assembly and fresh-prefix scan/explain/hooks.")
    return 0

if __name__=="__main__":raise SystemExit(main())
