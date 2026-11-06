"""Metadata only for the active locked research environment; no licence approval."""
import importlib.metadata
import json
import hashlib

rows = []
for distribution in importlib.metadata.distributions():
    metadata = distribution.metadata
    text = metadata.get("License", "")
    rows.append({"name":metadata["Name"], "version":distribution.version,
                 "license_expression":metadata.get("License-Expression"),
                 "legacy_license_summary":text.splitlines()[0][:160] if text else None,
                 "license_classifiers":[c for c in metadata.get_all("Classifier",[]) if c.startswith("License")],
                 "license_files":[{"path":str(f),"sha256":hashlib.sha256(distribution.locate_file(f).read_bytes()).hexdigest()}
                    for f in distribution.files or [] if ".dist-info/" in str(f) and
                    ("/licenses/" in str(f).lower() or f.name.lower().startswith(("license","copying","notice")))]})
print(json.dumps(sorted(rows,key=lambda r:r["name"].lower()),indent=2))
