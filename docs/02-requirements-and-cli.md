# Requirements and proposed CLI

## Functional requirements
- FR1: Default to an explicitly selected local repository, discovered from the current directory. No remote clone or network fetch.
- FR2: Compare HEAD to the index; for an unborn branch compare the index to an empty tree. Read staged blob bytes, never substitute working-tree content.
- FR3: Scan changed text blobs to find candidates; retain/report only candidates intersecting added or modified lines. Use the full staged blob for bounded local context and multi-line deterministic private-key rules.
- FR4: Handle renames, spaces, non-UTF-8 paths, deletions, partially staged files, empty commits, submodules and symlinks deliberately. Symlink targets are not followed; submodule content is out of scope.
- FR5: Deterministic high-confidence rules always produce visible findings. Generic candidates receive a model rank or review state; none are silently erased by the model.
- FR6: All outputs redact values and source snippets, including errors, trace mode, JSON, terminal and CI.
- FR7: Output a scan-completeness summary with skipped paths and reasons. Escape terminal control bytes in every repository-derived field.
- FR8: Import only a version-compatible, bounded, local model bundle. Missing, corrupt or incompatible models leave rules available and mark generic results unranked.
- FR9: Explicit hook installation only. Preserve an existing hook and refuse to overwrite it; provide manual integration instructions.
- FR10: No automatic source changes, credential validation, network calls or online learning.

## Proposed commands — not implemented
```sh
veilguard scan --staged
veilguard scan --staged --format json --output findings.json
veilguard explain --report findings.json --finding finding-001
veilguard model inspect ./models/release-model.json
veilguard hooks install
veilguard hooks uninstall
```
Text-only reports are default; JSON output is explicit and contains no candidate value. Explain reads an existing redacted report, never an argument containing a secret. A report has model/schema identifiers and feature contributions but not the raw eight-feature vector by default.

## Exit code contract
| Code | Meaning |
| --- | --- |
| 0 | Completed to declared coverage limits; no blocking rule findings |
| 1 | One or more blocking high-confidence rule findings |
| 2 | Invalid arguments, repository/model I/O failure preventing usable scanning, or incomplete coverage |
| 3 | Internal invariant violation; safe redacted error |

Priority is 3 > 2 > 1 > 0; incomplete scans with findings return 2 and retain the findings in the report. Missing models alone do not prevent a rule-only scan and are reported as degraded AI status. Generic model rankings never change the exit code in MVP. Code 0 does not assert the repository contains no secrets. Model-based blocking is a later decision requiring independent validation.

## Initial coverage limits
Supported generic candidates: printable ASCII strings of 8–256 characters. Extract quoted string spans and unquoted assignment values using bounded parsers for simple source/config lines. A credential-labelled assignment shorter than 8 or longer than 256 is emitted as unranked review. Multi-line private keys use independent rules. Unicode literals, concatenation, generated values, encoded/nested payloads and archives are unsupported by generic inference.

Budget proposals: 1 MiB per text blob, 20 MiB aggregate staged bytes, 10,000 candidates and 10 seconds wall time. Exceeding any limit reports incompleteness; do not silently truncate and report success. Binary blobs are skipped and reported, not interpreted as clean. Refuse unresolved index conflicts. Dependency locks/vendor/generated paths are not auto-suppressed; explicit user exclusions appear in the coverage summary.

## Reporting and remediation
Each finding includes a synthetic occurrence ID, escaped relative path, staged line, rule ID, severity/policy decision, model status and optional uncalibrated vote. Do not output complete lines, token fragments, token hashes or a reproducible hash of the candidate value.

Advise the user to remove a staged credential and rotate it through its provider if it may have been exposed. Never claim removing it from a new commit revokes an existing credential or clears Git history.

## Suppressions
Post-MVP only: explicit, local, narrow entries bound to path, staged blob object ID, rule and line, with reason/expiry. No automatic wildcard exemptions or learning from dismissed findings. A changed blob invalidates the suppression. Public reports do not expose repository object IDs by default.
