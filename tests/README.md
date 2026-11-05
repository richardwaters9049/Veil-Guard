# Verification

The [integration suite](staged_scan.rs) exercises the Phase One staged scanner using disposable, authored, nonfunctional fixtures. No credential is sent to a provider. See the [implementation record](../docs/15-phase-one.md) for the exact scope and current check record.

Git staged semantics are sourced to [R17](../docs/13-sources.md#r17). Train-only preprocessing isolation follows [R11](../docs/13-sources.md#r11) and is audited against frozen artifacts.

Run python3 scripts/check_all.py for the unified acceptance command, or cargo test --locked for scanner regressions. [Repository/automation details](../docs/17-repository-and-automation.md) distinguish these development checks from scanner runtime. Run [check_plan.py](../scripts/check_plan.py) for documentation links, source citations and the fabricated eight-dimensional arithmetic. These checks answer different questions; neither establishes real-world detection accuracy, AI benefit or external source entailment.

Repository/configuration refusal cases, packed storage, index v3/v4, corrupt baselines, output failures, metadata snapshots and panic redaction are now covered alongside candidate grammar, occurrence columns, budget priority and filename redaction; see the [candidate/report contract](../docs/16-candidate-and-report-contract.md). Rust/Python feature and model parity and adversarial model bundles are now checked. No-network instrumentation and supported-platform release tests remain pending. Keep unsupported scenarios visible rather than silently treating them as clean.

The [Phase Five integration suite](model_integration.rs) checks model status/fallback, staged-only inference, stable ranks/IDs, immutable rule decisions, saved report v3 explanations, malformed inputs and identifier/path redaction. The release smoke helper now runs scan, inspection and explanation together. See the [integration record](../docs/22-phase-five-native-inference.md) for commands and limits.
