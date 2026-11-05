"""Artifact security tests; no test executes archive-supplied binaries."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import package_development as p


def authored():
    files={"bin/veilguard":b"authored nonexecutable test data", "Cargo.lock":b"lock",
           "INSTALL.txt":b"private development", "THIRD-PARTY.txt":b"notices"}
    manifest={"schema":"veilguard.development-bundle.v1","source_license":"NOASSERTION",
        "model_bundled":False,"python_bundled":False,"target":"aarch64-apple-darwin",
        "distribution_status":"private_development_only_no_release_approval",
        "members":{name:{"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
                         "mode":0o755 if name=="bin/veilguard" else 0o644} for name,data in files.items()}}
    files["bundle-manifest.json"]=json.dumps(manifest).encode()
    return files


class Packaging(unittest.TestCase):
    def verify_bytes(self,data):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"test.tar.gz";path.write_bytes(data)
            return p.verify(path)

    def test_same_input_is_byte_identical_and_valid(self):
        files=authored()
        first=p.archive_bytes(files);second=p.archive_bytes(files)
        self.assertEqual(first,second)
        verified,_=self.verify_bytes(first)
        self.assertEqual(set(verified),set(files))

    def test_verification_cli_is_data_only_and_errors_do_not_echo_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/"authored.tar.gz";data=p.archive_bytes(authored());archive.write_bytes(data)
            command=[sys.executable,str(ROOT/"scripts/package_development.py"),"--verify"]
            result=subprocess.run([*command,str(archive)],capture_output=True,check=False)
            self.assertEqual(result.returncode,0);self.assertEqual(archive.read_bytes(),data)
            bad=Path(temp)/"private-path-sentinel"
            result=subprocess.run([*command,str(bad)],capture_output=True,check=False)
            self.assertEqual(result.returncode,2)
            self.assertNotIn(b"private-path-sentinel",result.stdout+result.stderr)

    def test_corruption_and_unlisted_members_are_refused(self):
        files=authored();files["bin/veilguard"]=b"tampered binary"
        with self.assertRaises(ValueError):self.verify_bytes(p.archive_bytes(files))
        files=authored();files["third-party/unlisted.txt"]=b"unlisted"
        with self.assertRaises(ValueError):self.verify_bytes(p.archive_bytes(files))

    def test_paths_and_symlinks_are_refused_without_extraction(self):
        for name,kind in [("../outside",tarfile.REGTYPE),("/absolute",tarfile.REGTYPE),
                          ("bin/veilguard",tarfile.SYMTYPE),("bin/veilguard",tarfile.LNKTYPE),
                          ("models/secret.json",tarfile.REGTYPE),("third-party/./odd",tarfile.REGTYPE)]:
            output=io.BytesIO()
            with tarfile.open(fileobj=output,mode="w") as tar:
                member=tarfile.TarInfo(name);member.type=kind;member.linkname="/outside";member.mode=0o644
                tar.addfile(member,io.BytesIO(b""))
            with self.assertRaises(ValueError):self.verify_bytes(gzip.compress(output.getvalue()))

    def test_world_writable_and_large_declared_members_are_refused(self):
        for mode,size in [(0o777,0),(0o4755,0),(0o644,33*1024*1024)]:
            member=tarfile.TarInfo("INSTALL.txt");member.mode=mode;member.size=size
            with self.assertRaises(ValueError):self.verify_bytes(gzip.compress(member.tobuf()+b"\0"*1024))

    def test_public_release_or_bundled_model_claims_are_rejected(self):
        for field,value in [("model_bundled",True),("source_license","MIT"),
                            ("distribution_status","approved_public_release"),("target","unverified-target")]:
            files=authored();manifest=json.loads(files["bundle-manifest.json"])
            manifest[field]=value;files["bundle-manifest.json"]=json.dumps(manifest).encode()
            with self.assertRaises(ValueError):self.verify_bytes(p.archive_bytes(files))


if __name__=="__main__":unittest.main()
