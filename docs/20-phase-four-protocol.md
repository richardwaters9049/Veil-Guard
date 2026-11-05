# Phase Four protocol — frozen before test evaluation

Created: 5 November 2026. Base: merged Phase Three commit 1ff1ef95cf514c54aeff7f47733385e2463612b3. Machine-readable protocol: [protocol.json](../research/experiments/protocol.json).

The experiment uses the frozen synthetic-v1 corpus. It cannot establish real-world credential validity, generalisation or time saved. Corpus licensing and independent human label adjudication remain recorded release items in the [data card](../data/DATA_CARD.md).

Scaling and leakage controls follow [R10](13-sources.md#r10), [R11](13-sources.md#r11), grouped splitting [R12](13-sources.md#r12), and held-out evaluation concerns [R14](13-sources.md#r14). PR/AP reporting follows [R13](13-sources.md#r13), [R24](13-sources.md#r24); logistic-regression and metric APIs are documented in [R30](13-sources.md#r30). The exact grids, risk targets, bootstrap procedure and success gate are project choices.

## Development and freezing

Only the 3,500 train and 1,100 validation examples enter development. Train has 30 connected groups; validation has 10. Five seeded GroupKFold splits use only train groups. Every fold fits its own StandardScaler on that fold's training rows. No uncertain examples enter fitting.

Compare raw and standardised exact KNN with k in 3,5,7,11,15 and uniform/inverse-distance weighting. Select by mean per-repository average precision from training out-of-fold scores. AP is rounded to 12 decimal places for selection ties, then smaller k and inverse-distance weighting win. The logistic baseline uses a StandardScaler/LogisticRegression pipeline, C in 0.1,1,10, lbfgs, tolerance 1e-8 and at most 2,000 iterations; smaller C wins equal rounded AP.

Exact search keeps eight coordinates. Squared distances accumulate in coordinate order; equal computed distances use opaque ID order. Every exactly zero-distance reference participates, even beyond k. Their vote is uniform and conflicting labels require review. These are the project's explicit semantics, not an assumption about a library default.

After choosing configurations, fit scalers and references on train only. Select the standardised KNN abstention policy on validation: prespecified margin/distance-quantile grids, raw training support limits and exact-conflict review. A feasible policy needs at least 50% coverage and at most 20% accepted error on validation. Prefer lower error, then greater coverage, then lower margin and larger distance limit. If no policy meets both targets, retain all candidates as review. These are validation targets, not guarantees.

Freeze model JSON, baselines, development results and hashes before invoking finalise. Do not refit on validation or change configuration after observing test performance. A separate locked [experiment environment](../research/experiments/pyproject.toml) preserves the Phase Three corpus lock and source identity.

## Ranking and classification

Rank every extracted eligible test candidate by the model's raw vote, including abstained cases. Abstention governs selective binary classification; it never clears findings or overrides deterministic rules. Rules-only ordering uses native severity with opaque ID ties. Entropy uses coordinate two.

Precision@20 and Recall@20 are per repository with at least 20 candidates. Smaller repositories use m=min(20,n) and a separate Precision@m/Recall@m slice. AP uses score-threshold tie grouping, while top-m ties use opaque IDs. Trapezoidal PR area is separately labelled. Empty scopes are undefined; scopes without positives have undefined recall/AP/PR area and zero nonempty precision.

Report accepted/abstained supports, coverage, confusion counts, precision/recall/F1 and error on accepted predictions. Raw KNN retains conflict/support review; logistic uses threshold 0.5 without abstention. Their differing coverage must remain visible. A separate confidence-coverage diagnostic is hypothetical classification at fixed margin-ordered fractions, not the deployed review policy.

The primary comparison is standardised KNN versus entropy mean repository Precision@20. Resample the 10 test connected groups with replacement, retaining every member repository, for 2,000 paired percentile replicates. Report the 2.5/97.5 percentiles and denominators. These few synthetic groups support exploratory intervals only. The benefit gate requires at least 10% relative improvement and a positive lower paired bound; otherwise report failed/unproven benefit and keep experimental status.

## Diagnostics and external reference

Training-only correlations and eight single-coordinate-zeroed ablations are diagnostic. Ablation retains eight columns and the selected full-model configuration; it cannot select a new feature set from test results.

The 200 uncertain challenges remain outside fitting/tuning. Predict eligible challenges without assuming a binary truth; unsupported inputs remain review. Report supports/reasons, not challenge accuracy.

Native scanner coverage is measured separately on staged fixtures, with source/index immutability and output redaction checked. A model cannot recover a candidate the scanner misses.

[Gitleaks v8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1) is checksum-pinned in [the tool lock](../research/experiments/gitleaks-lock.json). It scans a directory snapshot of verified staged test source using version-embedded defaults and full redaction, without Git metadata. This differs from Veil Guard's native index scanner and generic-candidate policy; publish coverage differences and rule IDs, not a single misleading winner.

## Verification

Unit tests use authored toy vectors and hand-worked metrics. CI verifies frozen training membership, scalers/export shape, protocol/artifact identity and replay of sealed prediction metrics. Replaying recorded predictions is a consistency check; it does not reselect a model or expose test outcomes to tuning. Any implementation correction affecting the final predictions must be disclosed rather than silently replacing a failed result.
