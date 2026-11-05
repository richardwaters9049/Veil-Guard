# Phase One implementation record

Updated: 5 November 2026. Branch: phase-one/staged-scanner. Status: milestone 1A and the candidate/report portion of 1B implemented. Repository-format review and milestone 1C remain open in the [programme plan](09-delivery-plan.md).

Git's staged/index semantics are grounded in [R17](13-sources.md#r17), with object/index interfaces in [R18](13-sources.md#r18). Project evidence comes from this repository's regression fixtures, not those references. This is a development scanner with narrow patterns, lexical candidate reviews and no AI model.

## Current implementation

| Area | Behaviour |
| --- | --- |
| Content | Index snapshot and bounded Git object bytes; no working-tree substitution |
| Comparison | HEAD versus staged bytes; empty baseline for unborn HEAD |
| Diff | In-memory buffer diff, no repository-supplied source-path argument |
| Blocking | Individual GitHub-PAT-shaped occurrences and private-key markers, including changed block bodies |
| Generic candidates | Quoted values and simple unquoted assignment literals, with distinct locations/counts |
| Unsupported candidates | Explicit review reasons; no feature imputation or automatic clearance |
| Reports | Version 2, start/end byte columns, separate candidate counts, no value/hash/feature fields |
| Privacy | Escaped paths plus observed-value scrubbing; all paths withheld on incomplete scans |
| Output files | New private file only; no replacement, including symlinks; 0600 on tested macOS |
| Limits | Blob/aggregate bytes, index entries, independent candidate/finding budgets and cooperative deadline |
| AI | not_implemented; no feature extractor, training, inference, model or model-based policy |

The exact grammar, scope, report migration and filename policy are in the [candidate/report contract](16-candidate-and-report-contract.md). Rule patterns do not establish validity or provider access. Generic reviews can be noisy; lexical extraction is not a complete language parser.

Renames remain conservative additions, so existing content may be re-reported at a new path. Binary/non-UTF-8 staged blobs, changed symlinks/submodules, conflicts, object failures and resource limits are disclosed. Exit 0 can still contain reviews and never certifies that a repository has no secrets.

## Run from the project directory

Directory: /Users/richy/Documents/Github/veilguard.

~~~sh
cargo build --locked
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo fmt --all --check
python3 scripts/check_plan.py
~~~

Scan an owned repository; replace the example path with the actual directory:

~~~sh
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --format json
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --format json --output findings.json
~~~

The output file must be new. On a file-write failure, the protected report goes to stdout and the command returns 2. Initial dependency builds may need network access; the scan path does not fetch or validate credentials. Non-Unix platforms are explicitly refused until supported, rather than using lossy path interpretation.

Exit 0: complete within declared scope, no blocking patterns; exit 1: blocking patterns; exit 2: invalid arguments, scan/output failure or incomplete coverage; exit 3: caught internal panic or report-serialisation failure. These are project policies.

## Budgets and residual risks

Default limits: 1 MiB per old/new blob; 20 MiB combined inspected object bytes; 10,000 generic candidates; 10,000 retained findings; 100,000 considered index entries; 4,096-byte source paths before display escaping/substitution; 4 MiB of transient escaped redaction patterns.

The 10-second deadline is cooperative. Repository metadata/index/object headers and individual library/matcher calls are not hard-interrupted. These content limits do not prove strict process-level memory/time isolation.

Local memory/crash dumps, unrecognised sensitive filename metadata, hostile/corrupt repository configuration, alternate object stores and full error-path/resource behaviour remain hardening concerns. The scanner does not rotate credentials, scan history, install hooks or collect training data.

## Verification history

Milestone 1A, commit e1083e5: 23 integration tests, format/lint checks and macOS arm64 release build passed. Its staged self-scan completed with one nonblocking authored-fixture review. This historical record applies to that commit.

Candidate/report slice, development version 0.1.0-dev.2:

| Check | Outcome |
| --- | --- |
| cargo test --locked | 41 integration tests and 1 privacy-budget unit test passed |
| cargo clippy --all-targets --locked -- -D warnings | Passed |
| cargo fmt --all --check | Passed |
| cargo build --release --locked | Passed on macOS arm64 |
| python3 scripts/check_plan.py | Passed: 24 source references, 170 local links/anchors |
| git diff --check | Passed |
| Release smoke scan of staged changes | Report v2; complete within declared scope; 244 lexical reviews, zero blocking patterns, no coverage issues, index unchanged |

No accuracy, runtime benchmark or AI benefit has been measured.

| Evidence area | Current regression coverage |
| --- | --- |
| Git semantics | Unborn HEAD, both partial-staging directions, missing worktree file, unchanged lines, deletions and renames |
| Literal grammar | Multiple/repeated values, quoted keys, CRLF, internal spaces, comments, URL slashes, escapes, Unicode, expressions and length boundaries |
| Rule priority | Multiple token occurrences, generic overlap deduplication, independent candidate budget and reserved blocking priority |
| Privacy | Redacted outputs, same/cross-file filenames, inner expression literals, pattern-shaped filenames, incomplete-path withholding and redaction-budget fallback |
| Coverage/failure | Binary/non-UTF-8 data, conflicts, missing objects, byte/finding/index-entry limits and error priority |
| Output safety | Static argument errors, private new report files, refusal to overwrite files/symlinks, fallback stdout |
| Execution | Configured external diff/filter commands and hook are not executed in the tested fixture |
| Contract | Example/live report field sets match; byte-span/count assertions; JSON contains no value/feature fields |

Tests use disposable, authored, nonfunctional fixtures. APFS-invalid byte names are inserted into the index directly, not created as filesystem names. The recorded environment is Richard's macOS arm64 machine with rustc/cargo 1.98.1 and the committed [lockfile](../Cargo.lock). This does not establish Linux/Windows compatibility or real-world detection performance.

## Remaining work

The candidate/report slice of 1B is implemented; the repository-format/alternate-object-store review is still pending. Milestone 1C must add automated checks and complete the scoped adversarial/error/resource acceptance work. Then Phase 2 can implement independent Rust/Python eight-feature parity. No phase is promoted merely because its implementation branch is pushed.
