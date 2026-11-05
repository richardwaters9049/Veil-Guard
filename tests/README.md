# Verification

The [integration suite](staged_scan.rs) exercises the Phase One staged scanner using disposable, authored, nonfunctional fixtures. No credential is sent to a provider. See the [implementation record](../docs/15-phase-one.md) for the exact scope and current check record.

Git staged semantics are sourced to [R17](../docs/13-sources.md#r17). Future ML preprocessing isolation follows [R11](../docs/13-sources.md#r11); it is not yet implemented.

Run cargo test --locked for scanner regressions. Run [check_plan.py](../scripts/check_plan.py) for documentation links, source citations and the fabricated eight-dimensional arithmetic. These checks answer different questions; neither establishes real-world detection accuracy, AI benefit or external source entailment.

Future suites must add candidate grammar, Rust/Python feature parity, model parity, adversarial model bundles, no-network instrumentation and supported-platform tests as their phases begin. Keep unsupported scenarios visible rather than silently treating them as clean.
