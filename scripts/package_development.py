"""Create deterministic private development bundles, never a public release."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import tarfile
import sys
import tomllib
import release_support as s
from review_dependencies import cargo_inventory, target

INSTALL = b'''Veil Guard development bundle (NOT a public release)

Project source licensing, release approval and model redistribution remain pending.
Do not redistribute this development bundle. No model or Python runtime is bundled.

Verify the archive SHA-256 using a checksum obtained independently from its builder.
SHA256SUMS detects corruption, but is not a signature or authenticity guarantee.
Extract into a new private directory. Check bundle-manifest.json and THIRD-PARTY.txt.
Copy bin/veilguard to a stable user-owned absolute location, chmod 700, and run --version.
No administrator rights, installer, hook modification or network inference is required.

  /absolute/path/to/veilguard scan --staged --repo /absolute/path/to/owned-repository
  /absolute/path/to/veilguard scan --staged --repo /absolute/path/to/owned-repository --format json
  /absolute/path/to/veilguard explain --report /path/to/saved-v3.json --finding finding-00001
  /absolute/path/to/veilguard hooks manual

Exit 0: completed within declared scope without blocking rules; not a safety certificate.
Exit 1: blocking rule finding. Exit 2: incomplete/unusable scan or invalid arguments.
Exit 3: internal failure. Generic candidates remain review regardless of model vote.
Reports redact values but may retain protected paths and numerical information: keep
reports private and remove them when no longer needed. Existing output files are refused.

Optional model selection uses --model /absolute/path/to/approved-model.json. Missing or
invalid models leave scanning usable with explicit degraded model status. No model is
downloaded automatically. The project's synthetic model failed its benefit gate.

For a deliberate hook installation at a stable binary location:
  /absolute/path/to/veilguard hooks install --repo /absolute/path/to/owned-repository
  /absolute/path/to/veilguard hooks uninstall --repo /absolute/path/to/owned-repository
Existing/custom/edited hooks are preserved or refused; hooks manual describes integration.
Alternate commit indexes are refused by the automatic wrapper. Hooks can be bypassed.
Before moving/removing the binary, uninstall or reinstall its owned hooks. Updates to a
binary at its existing path change future hook execution. Uninstall removes only exact
managed hooks; your repository sources and reports are never deleted by uninstall.

To upgrade: verify a separately approved replacement, uninstall/reinstall managed hooks
if changing binary location, and retain the old version for rollback. No auto-update exists.
To uninstall the app: remove owned hooks first, then remove the copied binary; inspect
and delete private reports separately. This does not revoke credentials or erase history.

macOS: this development archive is not notarized or a signed public release. Do not disable
system-wide security protections to run an untrusted download. Linux: match the recorded
architecture and inspect system-library requirements; no universal glibc compatibility claim.
'''


def payload():
    version=tomllib.loads((s.ROOT/"Cargo.toml").read_text())["package"]["version"]
    triple=target()
    if triple not in ("aarch64-apple-darwin","x86_64-unknown-linux-gnu"):
        raise ValueError("unsupported_package_target")
    if s.run([s.BINARY,"--version"]).stdout.decode().strip()!=f"veilguard {version}":
        raise ValueError("binary_version_mismatch_rebuild_required")
    file=s.run(["file",s.BINARY]).stdout.decode()
    assert ("arm64" in file if triple.startswith("aarch64") else "x86-64" in file),"binary_architecture_mismatch"
    crates,notices=cargo_inventory()
    files={"bin/veilguard":s.BINARY.read_bytes(),"INSTALL.txt":INSTALL,
           "Cargo.lock":(s.ROOT/"Cargo.lock").read_bytes()}
    for name,content in notices.items(): files["third-party/"+name]=content
    sysroot=Path(s.run(["rustc","--print","sysroot"]).stdout.decode().strip())
    rustdoc=sysroot/"share/doc/rust"
    for f in [rustdoc/"COPYRIGHT-library.html",*sorted((rustdoc/"licenses").glob("*"))]:
        if f.is_file():files["third-party/rust-standard-library/"+f.name]=f.read_bytes()
    if "third-party/rust-standard-library/COPYRIGHT-library.html" not in files:
        raise ValueError("rust_std_notices_missing")
    files["THIRD-PARTY.txt"]=(
        "Collected upstream licence/notice files for resolved host build dependencies and Rust standard library.\n"
        "This is a conservative notice collection, including build-only or unused bundled components.\n"
        "Crate declarations do not replace bundled C component terms; libgit2 COPYING includes a linking exception.\n"
        "No legal compatibility or project licensing approval is implied. Review before redistribution.\n"+
        "\n".join(f"{p['name']} {p['version']}: {p['declared_license'] or 'NOASSERTION'}" for p in crates)+"\n"
    ).encode()
    linked=s.run(["otool","-L",s.BINARY]).stdout.decode().splitlines()[1:] if platform.system()=="Darwin" else s.run(["ldd",s.BINARY]).stdout.decode().splitlines()
    # Remove process-specific load addresses from Linux metadata.
    import re
    linked=[re.sub(r"\s*\(0x[0-9a-fA-F]+\)","",line.strip()) for line in linked]
    if platform.system()=="Darwin":
        load=s.run(["otool","-l",s.BINARY]).stdout.decode()
        minimum=re.search(r"\bminos\s+([0-9.]+)",load)
        abi={"minimum_macos_load_command":minimum[1] if minimum else None}
    else:
        versions=s.run(["readelf","--version-info",s.BINARY]).stdout.decode()
        abi={"glibc_symbol_versions":sorted(set(re.findall(r"GLIBC_[0-9.]+",versions)))}
    manifest={"schema":"veilguard.development-bundle.v1","version":version,"target":triple,
        "distribution_status":"private_development_only_no_release_approval",
        "model_bundled":False,"python_bundled":False,"source_license":"NOASSERTION",
        "release_blockers":["Project source redistribution licence is unset.",
            "Native/OS security patch applicability requires review.",
            "Signatures, notarization, independent builds and remote platform results remain pending."],
        "source_identity":s.identity(),"rustc":s.run(["rustc","--version"]).stdout.decode().strip(),
        "dynamic_libraries":linked,"abi_requirements":abi,"cargo_lock_sha256":s.sha(s.ROOT/"Cargo.lock"),
        "members":{name:{"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
                         "mode":0o755 if name=="bin/veilguard" else 0o644} for name,data in sorted(files.items())}}
    files["bundle-manifest.json"]=(json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode()
    return f"veilguard-{version}-{triple}-development",files


def archive_bytes(files):
    output=io.BytesIO()
    with gzip.GzipFile(fileobj=output,mode="wb",filename="",mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode="w",format=tarfile.USTAR_FORMAT) as archive:
            for name,data in sorted(files.items()):
                member=tarfile.TarInfo(name);member.size=len(data);member.mtime=0
                member.mode=0o755 if name=="bin/veilguard" else 0o644
                archive.addfile(member,io.BytesIO(data))
    return output.getvalue()


def verify(archive):
    """Validate data only; this does not execute or authenticate the packaged binary."""
    archive=Path(archive)
    if archive.stat().st_size>100*1024*1024:raise ValueError("compressed_size_limit")
    files={};total=0
    class Bounded:
        def __init__(self, stream): self.stream=stream; self.remaining=64*1024*1024
        def read(self, size=-1):
            if size<0 or size>self.remaining: raise ValueError("tar_stream_size_limit")
            data=self.stream.read(size); self.remaining-=len(data)
            return data
    with gzip.open(archive,"rb") as compressed, tarfile.open(fileobj=Bounded(compressed),mode="r|") as tar:
        for member in tar:
            name=member.name;parts=PurePosixPath(name).parts
            if (not parts or name.startswith("/") or ".." in parts or "\\" in name
                or any(ord(c)<32 for c in name) or not member.isfile() or name in files
                or len(name)>240 or member.size>32*1024*1024
                or member.mode != (0o755 if name=="bin/veilguard" else 0o644)
                or (name not in ("bin/veilguard","Cargo.lock","INSTALL.txt","THIRD-PARTY.txt","bundle-manifest.json") and not name.startswith("third-party/"))):
                raise ValueError("unsafe_archive_member")
            if str(PurePosixPath(name))!=name:raise ValueError("noncanonical_member")
            total+=member.size
            if total>64*1024*1024 or len(files)>=10000:raise ValueError("expanded_size_limit")
            data=tar.extractfile(member).read(member.size+1)
            if len(data)!=member.size:raise ValueError("member_size_mismatch")
            files[name]=(data,member.mode)
    manifest=json.loads(files["bundle-manifest.json"][0])
    if manifest["schema"]!="veilguard.development-bundle.v1" or manifest["source_license"]!="NOASSERTION" or manifest["model_bundled"] or manifest["python_bundled"]:
        raise ValueError("bundle_contract")
    if manifest["distribution_status"]!="private_development_only_no_release_approval" or manifest["target"] not in ("aarch64-apple-darwin","x86_64-unknown-linux-gnu"):
        raise ValueError("bundle_release_or_target_contract")
    expected=manifest["members"]
    if not {"bin/veilguard","Cargo.lock","INSTALL.txt","THIRD-PARTY.txt"}.issubset(expected):
        raise ValueError("required_payload_missing")
    if set(files)!=(set(expected)|{"bundle-manifest.json"}):raise ValueError("member_set_mismatch")
    for name,record in expected.items():
        data,mode=files[name]
        if len(data)!=record["bytes"] or hashlib.sha256(data).hexdigest()!=record["sha256"] or mode!=record["mode"]:
            raise ValueError("member_integrity_mismatch")
    return files,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output",type=Path)
    mode.add_argument("--verify",type=Path,help="Validate archive data only; never execute its binary.")
    args=parser.parse_args()
    if args.verify is not None:
        try:
            verify(args.verify)
        except (ValueError, OSError, KeyError, TypeError, tarfile.TarError, EOFError):
            print("Bundle validation failed; archive data was not executed.",file=sys.stderr)
            return 2
        print("Archive structure and integrity verified; authenticity and release approval are not established.")
        return 0
    output=s.new_directory(args.output)
    name,files=payload();data=archive_bytes(files)
    archive=output/(name+".tar.gz")
    with archive.open("xb") as handle:handle.write(data)
    digest=s.sha(archive)
    (output/"SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
    verify(archive)
    print(f"Private development bundle verified: {archive.name}; SHA-256 {digest}")
    return 0

if __name__=="__main__":raise SystemExit(main())
