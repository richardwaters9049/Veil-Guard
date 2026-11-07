# Development install, verification and removal

This guide covers private development bundles only. The project source uses [MIT](../LICENSE) with a separate [scope notice](../LICENSE-SCOPE). Public binary release and model redistribution approval remain open. Git index behaviour follows [R17](13-sources.md#r17); bundle checks and hook ownership are project contracts described in [Phase Six evidence](24-phase-six-evidence.md).

## Build and create a bundle

From the repository root with the pinned Rust toolchain/dependencies available:

```sh
cargo build --release --locked --offline
python3 scripts/check_all.py --offline
python3 scripts/check_packaging.py --output /new/private/package-directory
```

The final command creates a native development `.tar.gz`, SHA256SUMS and a packaging evidence JSON. It assembles twice, compares bytes, verifies contents and runs only that freshly built trusted binary from an isolated temporary prefix. It tests version, scan, explanation and owned hook install/uninstall. The package excludes Python, generated data, corpus and model files. `scripts/package_development.py --output /new/private/package-directory` creates/validates without executing an extracted copy.

The bundle contains `bin/veilguard`, INSTALL.txt, Cargo.lock, a structural manifest, third-party metadata and preserved upstream notice/licence files, including Rust standard-library notices. Source/compiler/runtime identities and OS shared-library requirements are recorded. Same-input archive assembly is deterministic; independent compiler build reproducibility and portable minimum OS/glibc compatibility remain unproven. Output directories must be new; existing files are not overwritten.

## Verify before trusting a download

A checksum obtained from the same untrusted download is not authentication. First obtain an independently trusted checksum or approved future signature. No public signing key/notarization channel is established yet. Do not disable system-wide security protections to run an untrusted development build.

Compare SHA-256 with `shasum -a 256 <archive>` on macOS or `sha256sum <archive>` on Linux. Inspect the manifest target/version, `source_license`, status, member hashes and system-library dependencies. Run `python3 scripts/package_development.py --verify /path/to/archive.tar.gz` from this repository to validate archive data without running it: only regular canonical members are accepted; traversal, symlinks, hardlinks, duplicate entries, unsafe permissions, unlisted data, oversized members and decompression beyond the stream ceiling are refused. These are integrity/structure checks, not an authenticity or licensing decision.

For a bundle you trust, extract into a new private directory. Copy `bin/veilguard` to a stable user-owned absolute location and grant only the needed execute permission (for a private installation, mode 0700). It needs no Rust or Python runtime. Check `--version` and run on a disposable authored fixture before scanning your authorised repositories. The local fresh-prefix test does not establish behaviour on every fresh operating system.

## Use and retain reports deliberately

```sh
/absolute/path/to/veilguard scan --staged --repo /absolute/path/to/owned-repository
/absolute/path/to/veilguard scan --staged --repo /absolute/path/to/owned-repository --format json --output /new/private/findings.json
/absolute/path/to/veilguard explain --report /private/findings.json --finding finding-00001
```

Exit 0 means no blocking finding within declared complete coverage; it does not certify safety. Exit 1 means a blocking rule; 2 means invalid/unusable/incomplete operation; 3 means internal failure. Generic candidates remain reviews. Protect saved reports: values are redacted, but protected paths and optional numerical evidence can still be sensitive. The CLI does not automatically collect or remove your reports. Existing output files are refused.

Models are explicit via `--model /path/to/approved-model.json`; no model is downloaded. Missing/invalid models preserve rule-only scanning and show status. Only approved local data should populate an experimental model. The project's synthetic model failed its benefit gate and is excluded from the development bundle while redistribution remains unapproved.

## Hooks, upgrades and uninstall

Use `hooks manual` to review integration before deliberately installing with `hooks install --repo ...`. Existing/custom/edited hooks are preserved or refused. The automatic wrapper binds the installed binary's absolute location and refuses alternate commit indexes. It is convenience, not organisation-wide enforcement.

Before moving or deleting the executable, run `hooks uninstall --repo ...` in every repository where you deliberately installed it, or reinstall from the new stable binary location. Removal checks the ownership record and exact generated contents; edited/unowned hooks require manual inspection. Updating a binary in place changes what installed hooks run on later commits. Retain a previously trusted version for rollback; no automatic updater exists.

To remove the app, remove matching managed hooks first, then delete the copied binary. Inspect/remove private reports separately. Uninstall does not modify source, revoke credentials or erase Git history. Review licensing, patch status, provenance and platform evidence again before distributing a replacement build.
