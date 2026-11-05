# Phase One candidate grammar and report contract

Updated: 5 November 2026. Grammar: veilguard.candidates.v1. Report: veilguard.report.v2. Development build: 0.1.0-dev.2.

This is our implemented lexical contract, not a language parser or trained model. Git staged semantics are sourced to [R17](13-sources.md#r17); index/object interfaces to [R18](13-sources.md#r18). The grammar and limits below are project decisions verified by authored regression fixtures. The [eight-feature contract](04-eight-dimensional-features.md) is now implemented independently for research; [Phase Two](18-phase-two-feature-parity.md) records parity and its limits.

## Extraction scope

Only added/modified physical lines from staged UTF-8 text are candidates for generic extraction. Source byte spans remain local to the scanner; values are not fields in a finding. Private-key pattern detection independently inspects the complete bounded blob so a changed body can still trigger a warning.

| Input form | Current handling |
| --- | --- |
| Single- or double-quoted string | Record the contents between one enclosing quote pair |
| Simple full-line assignment | Recognise ASCII identifier, quoted identifier or bare identifier, followed by colon or equals |
| Unquoted assignment value | Eligible lexical alphabet: ASCII letters/digits and underscore, period, slash, colon, at sign, percent and hyphen |
| Optional terminator | Remove one syntactic trailing comma or semicolon, outside the value |
| Trailing comment | Hash or double slash outside quotes, at a whitespace/beginning boundary or immediately after a closing quote |
| URL in a bare value | Slashes after the colon stay part of the value |
| Quoted assignment key | Key span is excluded; value is not emitted twice |
| Function argument strings | Lexical quoted values can be generic candidates; no function is executed |
| Repeated value at different locations | Distinct occurrences, distinct synthetic IDs |
| Non-sensitive value shorter than 8 bytes | Omitted from generic candidate scope |
| Sensitive-key value, including empty/short values | Visible unranked review even outside the feature length range |

Identifiers start with an ASCII letter or underscore; subsequent identifier bytes may also include digits, periods and hyphens. Credential keywords are password, passwd, secret, token, credential, apikey and privatekey. Separator/camel-case tokens and concatenated adjacent tokens are compared case-insensitively; arbitrary substrings such as token within tokenizer do not count.

The whole-line assignment grammar does not recognise language declarations such as typed variables, nested objects or every assignment syntax. Quoted strings in those lines may still be generic candidates, without a sensitive-assignment verdict.

For a supported literal, preserve all bytes inside quotes, including spaces. Do not unescape, decode, concatenate or normalise. CRLF is treated as a physical line ending. Columns are one-based byte columns, not visual or Unicode-character columns; end columns are exclusive.

## Feature eligibility and unsupported review

feature_eligible_candidates counts syntactically supported printable-ASCII literals of 8–256 bytes. It does not mean scan computes a vector or model score. The Phase Two feature API is tested separately. Every eligible generic finding currently has reason model_not_available.

| Condition | Review reason | Feature eligible |
| --- | --- | --- |
| Printable ASCII, length 8–256, supported literal | model_not_available | Yes, syntactically |
| Sensitive value shorter than 8, including empty | short_literal | No |
| Value longer than 256 | long_literal | No |
| Unicode or control byte inside a quoted value | non_ascii_or_control_literal | No |
| Backslash escape | escaped_literal | No |
| Concatenation, function/expression RHS or unsupported bare punctuation | unsupported_expression | No |
| Unterminated single-line quote | unterminated_literal | No |
| Triple-quoted assignment | multiline_delimiter_unsupported | No |
| Template/backtick or triple-quoted generic form | multiline_or_template_unsupported | No |

A sensitive unsupported RHS is emitted as one expression span, rather than being falsely labelled as a complete literal. Bare values containing plus signs or equals signs are review-only in this grammar. This deliberately includes some legitimate encoded values; broader parsing requires an explicit grammar revision.

Generic comments starting with hash/double slash are ignored according to the boundaries above. Deterministic credential-pattern rules still scan those lines. Block comments, multiline generic-string state, interpolation, escaped/encoded semantics, archives and language ASTs are not implemented. In particular, a changed body of a generic multiline string with an unchanged opening delimiter is outside generic coverage; do not infer otherwise from the private-key rule.

## Counts, limits and blocking priority

The 10,000-candidate budget is distinct from the 10,000-finding budget. Candidate counts include supported/unsupported lexical occurrences, including a candidate that overlaps a blocking pattern; the duplicate generic finding is omitted when that pattern already explains its span.

Blocking patterns are detected independently of candidate extraction. Exhausting the candidate budget marks coverage incomplete but does not stop later rule scans. At a full finding budget, a later blocking warning can replace a review slot. If any finding cannot be retained, finding_limit_exceeded remains explicit. These are partial-result semantics, not a promise to enumerate unlimited inputs.

One line may contain multiple token patterns and multiple quoted candidates. IDs are assigned in deterministic source-location order; IDs are neither credential hashes nor proof of value uniqueness.

## Report v2

The [JSON schema](../schemas/report-v2.json) and [authored example](../examples/finding.example.json) define the current Phase One shape. The example is synthetic documentation, not a benchmark result.

Top-level fields include schema/version/grammar, scope, model status, path status, coverage, inspected bytes, file/candidate counts, findings and issues. Each finding includes an occurrence ID, protected path, start/end line and byte column, rule, severity, policy, model status and nullable review reason.

There is no value, token hash, raw source line, feature vector, neighbour list or model score. Model integration will require an explicit compatible extension or a new report version. The earlier development report v1/example is superseded; consumers must check report_schema before reading a report.

The integration suite compares example/live report field sets and tests span/count/privacy behaviour. This is not a claim of a full JSON Schema validator or a security audit.

## Filename privacy

Paths are byte-escaped first, then scrubbed against recognised pattern shapes and a bounded set of observed candidate/quoted-component values across the scan. A transient dictionary is limited to 4 MiB of escaped pattern bytes; it is dropped after report construction. This does not guarantee secure erasure of heap allocations.

[Aho-Corasick](https://docs.rs/aho-corasick/1.1.5/aho_corasick/struct.AhoCorasick.html) supplies the literal multi-pattern matcher. The library describes its matching APIs; our redaction policy and regression evidence are project-specific.

| path_status | Meaning |
| --- | --- |
| escaped | Display paths are escaped and no observed-value substitution was needed |
| redacted | At least one display path had a recognised value/pattern replaced |
| withheld | All finding/issue paths are replaced with a fixed marker because the scan was incomplete or redaction was unavailable |

Withholding an incomplete scan's paths avoids relying on a redaction dictionary that may have missed source values. Findings, issue codes and completeness state remain available. Precise paths may therefore be unavailable until the source/coverage problem is resolved.

This is not anonymisation. Complete scans can still reveal ordinary directory names and unrecognised sensitive metadata; the scanner has no knowledge of arbitrary secrets that were not recognised within its declared scope. A recognised source value may coincide with a static metadata word; no claim of universal substring secrecy is made.

## Phase One acceptance

General candidate extraction, occurrence columns, independent budgets, current schema/example alignment and the tested filename policy are implemented. The [repository/automation gate](17-repository-and-automation.md) now defines refused layouts, corrupt-baseline handling, control-file change detection and automated acceptance. Phase Two adds the separately tested feature API. Training data and AI inference remain unimplemented.
