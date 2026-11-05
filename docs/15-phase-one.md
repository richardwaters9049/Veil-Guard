# Phase One implementation record

Updated: 5 November 2026. Branch: phase-one/staged-scanner. Status: milestone 1A implemented; milestones 1B and 1C remain open in the [programme plan](09-delivery-plan.md).

Git's staged/index semantics are grounded in [R17](13-sources.md#r17), with object/index interfaces in [R18](13-sources.md#r18). Implementation evidence comes from this repository's tests, not those references. This is a development build with narrow rule coverage and no AI model.

## Implemented in milestone 1A

| Area | Current behaviour |
| --- | --- |
| Content | Reads index entries and Git object bytes; no working-tree substitution |
| Comparison | HEAD versus staged blob bytes; empty baseline for unborn HEAD |
| Diff | [In-memory buffer diff](https://docs.rs/git2/0.21.0/git2/struct.Patch.html#method.from_buffers), with source-path arguments omitted |
| Blocking patterns | GitHub-PAT-shaped strings and private-key markers; no validity check |
| Review | Changed sensitive-key assignments; never treated as benign clearance |
| Changes | Added/modified lines; changed private-key block bodies; deletions add no new content |
| Renames | New path treated conservatively as an addition; may re-report existing content |
| Reports | Text/JSON with synthetic occurrence IDs, escaped paths, static errors, no candidate-value field |
| Files | New output file only; no replacement, including symlinks; mode 0600 on tested macOS |
| Incompleteness | Binary/non-UTF-8 staged blobs, changed symlinks/submodules, conflicts, object failures and resource limits disclosed |
| AI | not_implemented; no feature extraction, training, inference or model-based policy |

The assignment rule recognises sensitive identifiers and reports a line for review. It is not yet the general quoted/unquoted candidate extractor or eight-feature parser. One finding per line/rule is reported; do not interpret this as an exact count of candidate strings. Pattern findings do not establish that a credential is live or even valid.

## Run from the project directory

Directory: /Users/richy/Documents/Github/veilguard.

Build and test:

~~~sh
cargo build --locked
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo fmt --all --check
python3 scripts/check_plan.py
~~~

Scan an owned repository, replacing the example path with its actual directory:

~~~sh
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --format json
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --format json --output findings.json
~~~

The new report path must not already exist. On a file-write failure, the redacted report is emitted to stdout and the command returns 2. Build dependencies may require network access initially; the scan path does not fetch or validate credentials.

Exit 0 means completion within this narrow scope with no blocking pattern findings; review findings can still exist. Exit 1 means blocking findings; exit 2 means invalid arguments, scan/output failure or incomplete coverage; exit 3 means a caught internal panic or report-serialisation failure. These codes are project policy, not a safety certification.

## Budgets and limits

- At most 1 MiB per old or new blob before loading its content.
- At most 20 MiB combined old/new object bytes inspected per scan.
- At most 10,000 line/rule findings.
- At most 100,000 index entries considered, including unchanged entries.
- A cooperative 10-second deadline checked between units of work. It does not interrupt an individual library call or guarantee a hard runtime cap.
- Path displays are byte-escaped and limited to 4,096 bytes. Overlong changed paths make coverage incomplete.

The index, repository metadata and object headers must be loaded before these content budgets can be fully applied. Strict memory/time isolation against hostile repositories is not claimed. No exclusions silently hide vendor/lock/generated paths.

## Verification record

Tested on Richard's macOS arm64 machine with rustc/cargo 1.98.1; dependency versions are in [Cargo.lock](../Cargo.lock). This is compatibility evidence for this environment, not a benchmark or a Linux/Windows support claim.

The integration suite in [staged_scan.rs](../tests/staged_scan.rs) covers:

- Unborn HEAD and text/JSON redaction.
- Both directions of partially staged changes; unchanged sensitive lines are not re-reported.
- Missing working-tree files, clean indexes, deletion and conservative rename handling.
- Nonblocking assignment reviews and changed/unterminated private-key blocks.
- Binary/non-UTF-8 content, conflicts, missing Git objects, size/finding/index-entry limits and error priority.
- Combined baseline/staged byte accounting.
- Static CLI errors that do not echo an invalid argument.
- Report creation, refusal to overwrite files/symlinks, 0600 permissions and fallback output.
- Changed symlink/submodule disclosure.
- Escaping newline/ANSI/non-UTF-8 path bytes. On APFS the invalid-byte path is inserted into the index directly, not created as a filesystem name.
- Configured external diff/filter commands and a hook are not executed in the tested fixture; index/worktree snapshots remain unchanged in the partial-staging case.

Final check record for milestone 1A:

| Check | Outcome |
| --- | --- |
| cargo test --locked | 23 integration tests passed; no failures |
| cargo clippy --all-targets --locked -- -D warnings | Passed |
| cargo fmt --all --check | Passed |
| cargo build --release --locked | Passed on macOS arm64 |
| python3 scripts/check_plan.py | Passed: 24 source references and 161 local links/anchors |
| git diff --check | Passed |
| Release binary smoke scan of staged project changes | Complete within declared scope; one nonblocking authored-fixture review, no coverage issues |

These are regression tests against authored nonfunctional fixtures, not real-world detection accuracy or evidence of reduced review time.

## Remaining Phase One work

Milestone 1B must implement general bounded candidate spans, finalise report contracts and cover syntax/candidate-count cases. Milestone 1C must automate checks and deepen repository/resource/error-path validation. See the [phase gates](09-delivery-plan.md).

Residual risks include sensitive filenames (escaping is not anonymisation), local memory/crash dumps, hostile/corrupt metadata, alternate object stores and resource use inside library calls. The scanner does not validate providers, rotate secrets, scan history, install hooks or collect training data. Full Rust/Python feature parity and all ML work belong to later phases.

The illustrative [finding example](../examples/finding.example.json) remains a proposal for later model output. Current JSON has top-level scope/coverage fields and findings with model_status only. Final schema alignment is an explicit milestone 1B task.
