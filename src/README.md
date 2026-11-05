# Native implementation

Phase One milestone 1A and the candidate/report portion of 1B are implemented. See the [implementation record](../docs/15-phase-one.md) for executable commands, scope and limitations, and the [delivery plan](../docs/09-delivery-plan.md) for all remaining phase gates.

Git index semantics are documented in [R17](../docs/13-sources.md#r17); the git2 API is [R18](../docs/13-sources.md#r18). Those sources inform the design. The integration suite supplies the limited project evidence.

| File | Responsibility |
| --- | --- |
| lib.rs | Scanner API |
| git_index.rs | Index snapshot, bounded object reading and in-memory changed-line calculation |
| rules.rs | Independent blocking pattern occurrences |
| candidates.rs | Bounded lexical candidates, byte spans and unsupported-review reasons |
| privacy.rs | Transient observed-value path scrubbing and incomplete-scan path withholding |
| report.rs | Redacted data contract, coverage state, escaped path display and text output |
| main.rs | CLI parsing, redacted errors, output files and exit handling |

The runtime starts no subprocess, uses no provider-validation client and loads no model. There is no eight-feature extractor or KNN implementation yet. Networking features are disabled for the git2 dependency; this is not a complete audit of all dependency code or hostile repository behaviour.
