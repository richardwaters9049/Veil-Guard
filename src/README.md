# Native implementation

The Phase One staged scanner, candidate/report contract and repository/automation gate are implemented for the declared scope. See the [implementation record](../docs/15-phase-one.md) for executable commands, scope and limitations, and the [delivery plan](../docs/09-delivery-plan.md) for all remaining phase gates.

Git index semantics are documented in [R17](../docs/13-sources.md#r17); the git2 API is [R18](../docs/13-sources.md#r18). Those sources inform the design. The integration suite supplies the limited project evidence.

| File | Responsibility |
| --- | --- |
| lib.rs | Scanner, feature and experimental model APIs |
| model.rs | Strict bounded research bundle loading, exact KNN, abstention and distance contributions |
| features.rs | Exactly eight validated coordinates, shared keyword spans, supplied-scaler arithmetic and distance contributions |
| git_index.rs | Index snapshot, bounded object reading and in-memory changed-line calculation |
| repository.rs | Preflight layout/configuration policy, bounded metadata, corrupt-baseline handling and control snapshots |
| rules.rs | Independent blocking pattern occurrences |
| candidates.rs | Bounded lexical candidates, byte spans and unsupported-review reasons |
| privacy.rs | Transient observed-value path scrubbing and incomplete-scan path withholding |
| report.rs | Redacted data contract, coverage state, escaped path display and text output |
| hooks.rs | Explicit owned hook installation/removal and manual integration; not called by scan |
| local_input.rs | Bounded regular-file inputs with nonblocking/no-follow open on Unix |
| explanation.rs | Saved-report numeric validation and source-free redacted explanations |
| main.rs | CLI parsing, redacted errors, output files and exit handling |

The scanner starts no subprocess and uses no provider-validation client. Explicit `--model` enables experimental feature extraction and KNN; missing/invalid inputs preserve rule-only scanning. See the [Phase Five record](../docs/22-phase-five-native-inference.md) for report v3, fallback and redacted commands. The reviewed libgit2 is vendored and networking features are disabled for git2; complete dependency/no-network audits remain release work.
