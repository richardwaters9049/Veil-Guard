# Phase Five — native inference and scanner integration

Status: implemented for the declared experimental scope; release hardening remains Phase Six. Entry evidence is the [failed synthetic benefit gate](21-phase-four-results.md) and frozen train-only model export. This phase does not change that decision or refit a model.

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

## Scanner, fallback and commands

```sh
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --model research/results/synthetic-v1/development/model.json --format json --explanations --output findings.json
cargo run --locked -- model inspect research/results/synthetic-v1/development/model.json
cargo run --locked -- explain --report findings.json --finding finding-00001
cargo run --locked -- explain --report findings.json --finding finding-00001 --format json
```

Only explicit `--model` enables inference. No repository model/config discovery occurs. CLI model/report inputs must be regular local files, at most 16 MiB; symlinks and special files are refused, with nonblocking/no-follow open on Unix. Failed model loading leaves a usable rule-only scan. The public `scan` library API remains rule-only; `scan_with_model` accepts an explicit selection. No hook is installed, no source is modified and no provider/network inference is introduced.

| Top-level model status | Meaning |
| --- | --- |
| not_requested | No model was selected; rule-only scan |
| unavailable | Explicit input could not be read as a bounded regular file |
| invalid | Bytes were read but failed model validation |
| experimental | Model loaded; eligible generic findings can be ranked |
| degraded | A candidate inference failed or exceeded the cooperative budget; reviews remain visible |

Blocking findings always have `not_applicable` status and no model evidence. Unsupported lexical findings keep their original reason and `unsupported` status. Scored generic findings have `ranked_experimental` status; numerical failures yield `inference_failed`. Missing/corrupt models do not mark lexical coverage incomplete or change exit codes. Deadline exhaustion still marks coverage incomplete and returns 2. Deadlines remain cooperative, including individual KNN calls.

The scanner extracts features from the original staged physical line and byte span, never the worktree. Deterministic rules run first and retain their existing cap priority. Every generic candidate remains policy `review`, including a zero vote or a model-accepted negative. The frozen standardised model still reports `validation_policy_unmet` for all eligible candidates. Models never clear findings or add blocking decisions.

## Report v3 and redacted evidence

The new [schema](../schemas/report-v3.json) and [example](../examples/finding-v3.example.json) supersede v2 for current scans. Report v2 remains unchanged for historical Phase Four artifacts. Each v3 finding adds nullable `model` evidence: score, rank, nearest distance, zero-match count, conflict and outside-support flags, and nullable neighbour details. Raw values, source snippets, value hashes and feature vectors remain excluded. An uncalibrated vote is not a credential-validity probability.

Occurrence IDs and location order remain stable relative to a rule-only scan; model scores do not reorder the finding array. Rank 1 is the highest raw vote among retained scored reviews, with occurrence order breaking ties. Blocking/unscored/unsupported findings are outside this ranking. Abstention never removes an eligible score from ranking. Finding caps and incomplete coverage mean ranks do not describe omitted candidates.

Neighbour details are retained only with explicit `--explanations` (requires `--model`), in text or JSON output. At most five of the selected k neighbours are shown, with labels, distances and eight squared standardised contributions. All exact matches still vote even beyond k. Reference identifiers are one-based positions in the selected artifact, rendered as `reference-00001` in text. They deliberately replace model-supplied strings; ordinal aliases are only meaningful with the same selected artifact. Inspection prints validated structural/configuration metadata and thresholds, excluding model IDs, reference IDs/vectors and preprocessing arrays. Bundle provenance is not authenticated by loading.

`explain` accepts v3 reports only, validates the selected occurrence and numerical evidence, and prints fixed labels/numbers only. It withholds report paths and arbitrary strings even if the file has been tampered with. It never reopens a repository or recomputes predictions. Reports are unauthenticated saved claims; consistent numeric evidence is not proof of a genuine scan. If neighbour details were not retained, explanation shows the summary and says so. Invalid versions, duplicate requested IDs, unknown statuses/reasons or invalid evidence fail with a fixed redacted error. Larger reports must be reduced before explanation; the command refuses inputs above its size ceiling.

## Integration verification and gate

`tests/model_integration.rs` exercises the actual CLI and library with authored nonfunctional fixtures: staged/worktree disagreement and immutability; a zero vote that remains review; blocking priority; unsupported literals; absent/corrupt/oversized inputs; numerical failure fallback; the frozen review-all policy; opt-in diagnostics; rank/ID stability; saved output and refusal to overwrite; inspection; source-free explanation; malicious report text, invalid numerical evidence, duplicate IDs and legacy reports; symlink/FIFO refusal. Existing scanner, panic/output and corpus parity suites remain required.

The historical Phase Four `finalise` harness intentionally expects the v2 scanner and its recorded binary/source identities. Reproduce that original external/native extraction with the Phase Four checkout at `ea1b5a8`, not the new v3 scanner. Sealed metric replay and frozen development audits run on the current checkout without modifying any frozen implementation or result.

Nine integration tests pass locally. The Phase Five scope is integrated and tested locally. CI execution on the supported platform matrix, no-network instrumentation, packaging, model authenticity/distribution controls, benchmarks, hooks and release licensing/review remain Phase Six/Seven work. The failed AI usefulness gate remains unchanged.
