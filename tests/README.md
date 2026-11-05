# Planned verification

Reserved for Git-index, privacy, feature parity and model parity integration tests. The [planning checker](../scripts/check_plan.py) validates local documentation links, R-number citations, source metadata, eight-dimensional metadata and the fabricated arithmetic. It does not test scanner functionality or model performance.

Future tests must cover the [evaluation gates](../docs/07-evaluation-and-acceptance.md). Staged-index semantics are grounded in [R17](../docs/13-sources.md#r17); preprocessing isolation in [R11](../docs/13-sources.md#r11). Tests need independent fixtures and expected outcomes rather than assertions copied from the implementation.

Manual source review remains necessary: a working link is not proof a claim is supported. The source register records limited review scopes, including theses whose full experiments were not assessed.
