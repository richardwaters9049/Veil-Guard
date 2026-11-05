# Phase Five — native inference core

Status: core implementation; scanner integration and CLI inspection/explanation commands remain pending. Entry evidence is the [failed synthetic benefit gate](21-phase-four-results.md) and frozen train-only model export. This phase does not change that decision or refit a model.

The library implements exact Euclidean KNN ([R04](13-sources.md#r04)) with train-fitted preprocessing ([R10](13-sources.md#r10), [R11](13-sources.md#r11)). Eight coordinates, tie ordering and abstention semantics are project contracts.

## Implemented scope

`model::Model` loads the existing `veilguard.knn-model.v1` export. Reads are bounded to 16 MiB plus one detection byte; model references are limited to 10,000. Loading rejects unknown fields, incorrect versions/feature order/label encoding, unsafe IDs, duplicate reference IDs, invalid labels, nonfinite values, nonpositive scales, inverted support bounds, invalid policy values and k outside the reference count. Errors use fixed enum codes without input contents. Deserialisation has its default recursion limit. Model and reference containers have no Debug implementation.

Inference standardises queries with exported means/scales and accumulates squared differences in coordinate order. It sorts by computed distance then opaque ID. Every exact match participates in a uniform vote even beyond k; conflicting exact labels require review. Nonzero matches use the exported uniform or inverse-distance weighting. Nonfinite queries, standardisation overflow, distance overflow and invalid votes return errors.

Abstention priority matches the frozen Python reference: review-all policy, exact conflict, outside raw training support, nearest-distance limit, then vote margin. The frozen standardised model retains review-all because validation targets failed. Diagnostic output exposes at most k approved example IDs with squared coordinate contributions; all exact matches still affect the score. Contributions explain distance, not causal importance or credential validity.

JSON parsing enables `serde_json`'s `float_roundtrip` feature to preserve exported f64 values. Initial corpus parity found an exact-match conflict mismatch without this feature. This corrects native loading only; the frozen Python implementation and sealed results are unchanged.

## Verification

```sh
cargo test --locked --offline --test model
.venv/bin/uv run --locked --offline --project research/experiments python scripts/check_model_parity.py --offline
python3 scripts/check_all.py --offline
```

Native tests cover hand-worked weighted/uniform votes, ties, all-zero conflicts beyond k, policy priority/boundaries, strict corrupt-bundle refusal, size limits, overflow and frozen export loading. The research-only example bridge accepts approved synthetic model/vectors and is not a shipped CLI command. The parity script compares both frozen exports on every eligible corpus vector, plus toy ties/conflicts, checking scores, nearest distances, neighbours, labels, abstention and coordinate contributions. No fitting or configuration selection occurs. The local run passed 12,132 predictions (6,060 eligible rows through each frozen export plus 12 toy predictions), with maximum score/nearest-distance absolute difference 2.22e-16.

The unified acceptance command includes the model tests and parity check. These demonstrate arithmetic/contract consistency on synthetic inputs; they do not establish model usefulness or real-world detection accuracy.

## Remaining phase gate

The scan command still uses its existing report contract and does not load a model. Next steps are explicit model selection/status, safe absent/corrupt-model fallback, model inspection and redacted explanation commands, scanner/report integration and end-to-end tests proving deterministic findings remain authoritative. Phase Five is incomplete until that integration and its privacy/parity checks pass. No hook is installed and no network inference is introduced.
