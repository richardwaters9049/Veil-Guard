# Claims and evidence register

Evidence revision: 5 November 2026. Milestone 1A has a rule-only implementation and a [regression record](15-phase-one.md). The candidate/report slice is now implemented and [specified](16-candidate-and-report-contract.md); repository-format restrictions and automated checks are now [recorded](17-repository-and-automation.md). [Feature parity](18-phase-two-feature-parity.md) and the [synthetic corpus/split gate](19-phase-three-corpus.md) are implemented. Training and detection/performance benchmarks remain pending. This register governs README, documentation, demos and portfolio wording.

## How to read the labels

- **External evidence:** a limited statement supported by an identified source.
- **Derived:** follows from a stated mathematical definition/algorithm, not a measured outcome.
- **Design:** behaviour or policy we intend to implement.
- **Hypothesis:** a benefit we need to test.
- **Target:** an acceptance threshold or estimate chosen for planning.
- **Measured:** requires a reproducible project result. Corpus counts and engineering checks are recorded; no detection or model-performance measurement exists.

University profiles identify people; they are not evidence of endorsement. Papers about a method do not validate our implementation or selected features. Sources are indexed in [13-sources.md](13-sources.md).

## Traceable statements

| ID | Statement / type | Support | Scope and required project evidence |
| --- | --- | --- | --- |
| C01 | Credentials have been exposed in public code — external evidence | [R01](13-sources.md#r01) | Historical public-GitHub study; do not imply a current global rate |
| C02 | Heuristics and ML for secret detection have prior academic work — external evidence | [R02](13-sources.md#r02) | RIT thesis abstract; no replication or claim that its model equals ours |
| C03 | KNN classifies from nearby labelled examples — external evidence | [R03](13-sources.md#r03), [R04](13-sources.md#r04) | Requires meaningful distance and suitable data; no finite-sample project guarantee |
| C04 | Candidates use exactly eight coordinates — implemented design | [Feature contract](04-eight-dimensional-features.md) | User-requested constraint; usefulness needs ablation/collision analysis |
| C05 | Standardisation uses train-only means/scales — method/design | [R10](13-sources.md#r10), [R11](13-sources.md#r11) | Supplied-scaler arithmetic parity and corpus split checks pass; fitting training-only statistics remains Phase Four |
| C06 | Squared Euclidean distance is a sum of coordinate squares — derived | [R05](13-sources.md#r05); [our derivation](05-knn-and-linear-algebra.md) | Distance contributions describe similarity, not causal importance |
| C07 | Character entropy/edit distance have mathematical definitions — external evidence | [R06](13-sources.md#r06), [R07](13-sources.md#r07) | Their use as our security features is unvalidated |
| C08 | Group-disjoint evaluation helps address related-example leakage — method/design | [R12](13-sources.md#r12), [R14](13-sources.md#r14) | Connected group/manifest checks pass on authored synthetic examples; all latent-factor independence is unproven |
| C09 | Precision/recall analysis addresses class-imbalance questions — external evidence | [R13](13-sources.md#r13) | Report prevalence, supports, coverage and exact metric definitions |
| C10 | A weighted vote is not established here as a calibrated probability — limitation | [R23](13-sources.md#r23); no calibration experiment | Do not say “75% chance this is a live key” |
| C11 | The index represents staged content compared with HEAD — external evidence | [R17](13-sources.md#r17) | Partial-staging/unborn-HEAD and repository/output hardening regressions pass locally; per-commit macOS/Linux results are in the acceptance workflow |
| C12 | Pickle-based persistence carries code-execution risk — external evidence | [R19](13-sources.md#r19) | JSON avoids that mechanism; strict parsing still needs testing |
| C13 | Offline/redacted operation will protect source privacy — design goal | [Threat model](08-ethics-and-threat-model.md); relevant logging guidance [R20](13-sources.md#r20) | Capture outputs, instrument network/process behaviour, disclose local residual risk; no absolute guarantee |
| C14 | KNN will reduce review effort/false positives — hypothesis | No project evidence | Baseline ranking study plus a separate consenting-user study before time-saving claims |
| C15 | 5,000–10,000 rows, 50 families, 20 repositories — collection targets | [Data plan](06-data-and-training.md) | Prototype has 6,200 rows, 130 families and 70 fixture repositories; no academic sample-size guarantee |
| C16 | 10% Precision@20 improvement, 2s p95, 150 MiB RSS — release targets | [Evaluation plan](07-evaluation-and-acceptance.md) | No achievement claimed; publish actual workload/hardware and intervals |
| C17 | 90–150 hours / 6–8 part-time weeks — estimate | [Delivery plan](09-delivery-plan.md) | Planning judgement; no literature-derived productivity claim |
| C18 | Existing scanners already address this space — external evidence | [R21](13-sources.md#r21), [R22](13-sources.md#r22) | No novelty or replacement claim; comparisons need pinned versions |
| C19 | Data/model documentation should record intended use and limits — framework adaptation | [R15](13-sources.md#r15), [R16](13-sources.md#r16) | Data card records actual composition and pending review/licensing; model card remains a template; neither is a certification |
| C20 | Computing all n eight-coordinate distances is O(8n) — derived | [Architecture](03-architecture-and-stack.md) | Sorting/selection and extraction add cost; no measured latency follows |

## Wording to withhold

No “industry-leading”, “first AI secret scanner”, “guaranteed secure”, “detects all leaks”, “eliminates false positives”, “trained AI” or numerical accuracy claim at the planning stage. Do not describe numerical feature vectors as anonymous, a local hook as tamper-proof, or university researchers as collaborators.

## Promoting a target to a measured claim

Record commit/tag, feature/model/data versions, pinned baselines, independent groups, exact metric code, denominators, uncertainty, workload/hardware, failures and reproduction commands. Link the result from this table and the completed cards. Retain negative findings and distinguish synthetic performance from external validity. A new implementation or dataset invalidates inherited claims until rechecked.
