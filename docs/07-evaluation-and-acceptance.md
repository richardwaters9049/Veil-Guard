# Evaluation and acceptance
All numbers below are proposed targets. No benchmark has been run and no metric has been achieved.

## Two separate questions
1. Does candidate extraction plus deterministic scanning surface the fixture credentials in staged changes?
2. Among extracted generic candidates, does KNN put useful reviews earlier than baselines?

Report end-to-end misses separately from candidate-level classification. A classifier cannot recover a credential the extractor never emits. Model gains must not be inferred from prefiltered candidate-only results.

## Comparisons
Use the same staged fixtures and candidate set for rules-only generic severity ordering, entropy ranking, standardised logistic regression and standardised KNN. Also run a pinned Gitleaks release as an external scanner reference, with safe fixtures and documented configuration. It is not an identical scope comparison; report coverage differences and versions rather than a misleading single winner.

## Metrics and experiments
| Area | Evidence |
| --- | --- |
| End-to-end detection | Fixture credential recall, rule/generic split, miss reasons, false alerts per repository and per 1,000 changed lines |
| Ranking | Precision@20 and Recall@20 per eligible repo, average precision/PR-AUC, review ordering with score ties handled deterministically |
| Classification | Precision/recall/F1 on non-abstained predictions, confusion matrix, class support |
| Abstention | Coverage, abstention rate and error rate among accepted predictions; report errors at fixed coverage |
| Generalisation | Unseen family/repository results and hard-negative/low-entropy slices |
| AI value | Paired differences versus entropy and rule baselines, grouped bootstrap intervals |
| Performance | Cold/warm p50/p95 wall time, peak RSS, bytes/candidates/reference rows and hardware |
| Privacy | Adversarial fixture output captures show zero exact candidate values or source lines across text/JSON/errors |
| Native parity | Feature, neighbour/vote and distance-contribution agreement against reference fixtures |

For repositories with fewer than 20 candidates, use all candidates and report their count; publish that slice separately. Bootstrap repositories/independent groups, not correlated rows. Report 95% intervals and denominators. Do not call weighted KNN votes calibrated probabilities; calibration needs a separate study.

## Proposed release gates
- Every deterministic positive in the supported locked regression suite remains visible with AI enabled or disabled.
- No changes to source, index or existing hooks during scans.
- Every partial scan or skip is disclosed; exit-code tests match policy.
- Unsupported/corrupt models never cause generic candidates to be silently cleared.
- Candidate feature parity ≤1e-9 absolute error; vote/distance parity within documented f64 tolerance; tie behaviour identical.
- No exact synthetic candidate values in output captures, including malicious filenames and deliberately triggered errors.
- Native binary scans 1 MiB / up to 1,000 generic candidates using 10,000 reference rows with warm p95 ≤2 seconds and peak RSS ≤150 MiB on the recorded M4 16 GB Mac. These workloads/targets need profiling and may be revised transparently before release.
- AI benefit target: ≥10% relative improvement in mean per-repository Precision@20 over entropy ranking, while showing Recall@20 and confidence intervals. Require a positive lower confidence bound for a release claim of improvement; otherwise mark the model experimental.
- A synthetic-only test permits only synthetic-benchmark claims. Real-world usefulness remains unproven until an ethical independent evaluation.

MVP may ship a useful rule scanner with experimental optional ranking if the AI benefit gate fails. It must not advertise a successful AI improvement. No model-based blocking in MVP.

## Important test cases
Unborn HEAD, partial staging, staged rename, filenames with newlines/ANSI escapes, deleted files, symlink/submodule entries, merge conflicts, inaccessible blobs, binary/oversized blobs, resource limits, missing/corrupt model, zero-variance scaling, identical vectors with conflicting labels, exact ties, out-of-distribution candidates, empty candidate list and paths outside scope.

## Required evaluation report
Record actual corpus sizes, splits, exact configs, hardware and dependency versions; show confusion tables and grouped intervals; include missed cases and representational collisions. Publish a blank results template until experiments are complete. Do not replace missing measurements with estimates.
