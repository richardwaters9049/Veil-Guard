# Requirements and proposed CLI

## Functional requirements

**Design status.** FR1–FR10 describe the target programme. The [Phase One record](15-phase-one.md) identifies the implemented scan subset and regression evidence; [Phase Five](22-phase-five-native-inference.md) implements experimental model integration; hook requirements remain pending. Git defines staged/index-versus-commit comparison ([R17](13-sources.md#r17)); git2 documents APIs that can implement it ([R18](13-sources.md#r18)). Tests must establish whether our implementation meets these requirements.

- FR1: Default to an explicitly selected local repository, discovered from the current directory. No remote clone or network fetch.
- FR2: Compare HEAD to the index; for an unborn branch compare the index to an empty tree. Read staged blob bytes, never substitute working-tree content.
- FR3: Scan changed text blobs to find candidates; retain/report only candidates intersecting added or modified lines. Use the full staged blob for bounded local context and multi-line deterministic private-key rules.
- FR4: Handle renames, spaces, non-UTF-8 paths, deletions, partially staged files, empty commits, submodules and symlinks deliberately. Symlink targets are not followed; submodule content is out of scope.
- FR5: Deterministic high-confidence rules always produce visible findings. Generic candidates receive a model rank or review state; none are silently erased by the model.
- FR6: All outputs redact values and source snippets, including errors, trace mode, JSON, terminal and CI.
- FR7: Output a scan-completeness summary and skip reasons. Paths may be escaped/redacted, or withheld when incomplete coverage prevents reliable filename scrubbing. Escape terminal control bytes in every displayed repository-derived field.
- FR8: Import only a version-compatible, bounded, local model bundle. Missing, corrupt or incompatible models leave rules available and mark generic results unranked.
- FR9: Explicit hook installation only. Preserve an existing hook and refuse to overwrite it; provide manual integration instructions.
- FR10: No automatic source changes, credential validation, network calls or online learning.

## Commands and implementation status

The first three scan forms work in the Phase One source build; use `cargo run --locked --` before `scan` until installed:

```sh
veilguard scan --staged
veilguard scan --staged --repo /absolute/path/to/owned-repository
veilguard scan --staged --format json --output findings.json
```

Experimental model commands are implemented:

```sh
veilguard explain --report findings.json --finding finding-00001
veilguard model inspect ./models/release-model.json
```
Hook install/uninstall commands remain Phase Six proposals.

Text-only reports are default; JSON output is explicit and contains no candidate value. Explain reads an existing redacted report, never an argument containing a secret. The current [report-v3 contract](22-phase-five-native-inference.md) includes explicit model status, optional scores/ranks and opt-in numerical neighbour details. No values or raw vectors are present. Use `scan --model /path/to/approved-model.json --explanations --format json --output findings.json` to retain explanation details.

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

Target budgets: 1 MiB per blob, 20 MiB aggregate inspected bytes, 10,000 candidates and a 10-second deadline. The current implementation counts old and staged bytes together and independently caps 10,000 generic candidates and 10,000 retained findings; its deadline is cooperative, not a hard interruption. These implementation limits are detailed in the [Phase One record](15-phase-one.md). Exceeding any limit reports incompleteness; do not silently truncate and report success. Binary blobs are skipped and reported, not interpreted as clean. Refuse unresolved index conflicts. Dependency locks/vendor/generated paths are not auto-suppressed; explicit user exclusions appear in the coverage summary.

## Reporting and remediation

Each current finding includes a synthetic occurrence ID, protected path, staged start/end line and byte columns, rule ID, severity/policy decision, model status and nullable review reason. An optional uncalibrated vote ranks retained generic reviews and never changes policy or exit status. Do not output complete lines, token fragments, token hashes or a reproducible hash of the candidate value.

Advise the user to remove a staged credential and follow its provider's revocation/rotation process if it may have been exposed. OWASP describes secret lifecycle management and rotation/revocation ([R20](13-sources.md#r20)). Never claim removing it from a new commit revokes an existing credential or clears Git history.

## Suppressions

Post-MVP only: explicit, local, narrow entries bound to path, staged blob object ID, rule and line, with reason/expiry. No automatic wildcard exemptions or learning from dismissed findings. A changed blob invalidates the suppression. Public reports do not expose repository object IDs by default.
