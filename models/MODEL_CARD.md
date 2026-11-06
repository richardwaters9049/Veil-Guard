# Model card — synthetic-v1 research model

Status: experimental research only; benefit gate failed. Model ID: synthetic-v1-knn-initial. Feature schema: veilguard.features.v1.

## Evidence and status

This template adapts [Model Cards for Model Reporting, R16](../docs/13-sources.md#r16). KNN background is [R04](../docs/13-sources.md#r04), scaling is [R10](../docs/13-sources.md#r10), and calibration is a separate concern ([R23](../docs/13-sources.md#r23)). The eight features, thresholds and runtime policy are project choices. No author, professor or university has evaluated or endorsed this model. Measured synthetic evidence is recorded in the [Phase Four results](../docs/21-phase-four-results.md).

## Intended use

Offline prioritisation of ambiguous credential candidates in staged Git text. Human review required. No credential validity inference, autonomous remediation or MVP model-based blocking.

## Method

Exactly eight numeric coordinates; train-fitted standardisation; exact Euclidean KNN; inverse-distance vote with explicit zero-distance handling; review/abstention rules. Research inference is Python; a native Rust inference library and synthetic parity check are implemented. Explicit scanner integration, fallback and redacted explanation commands are implemented; all generic findings remain reviews.

## Training and evaluation

Dataset/recipe version: synthetic-v1; authored nonfunctional fixtures.
Provenance: authored synthetic recipes; licensing and independent human review remain pending in the [data card](../data/DATA_CARD.md).
Train: 3,500 rows / 30 connected groups. Validation: 1,100 / 10. Test: 1,400 / 10, spanning 14 repositories.
Binary partitions are balanced; this does not represent deployment prevalence. The 200 uncertain challenges have no binary truth.
k=3, inverse-distance weights, train-only population standardisation. Validation targets were unmet, so the policy reviews all candidates. Mean/scales and support bounds are in the [frozen export](../research/results/synthetic-v1/development/model.json).
Model JSON SHA-256: `f836afa4775dc04c248200d7499c39409886a76dfadf152232aa879017905479`.
Test macro Precision@20: 0.539286 versus entropy 0.500000; relative gain 7.857%. Paired absolute difference 95% exploratory interval: [-0.053846, 0.132173]. Full baseline/slice evidence is in the [results](../docs/21-phase-four-results.md). Classification coverage is zero; accepted metrics are undefined.
Native/reference feature parity is implemented; model inference parity is checked on eligible synthetic corpus vectors and authored toy cases.
Supported distributions and platform workload: not validated.

## Limitations

Feature collisions, unsupported syntax, unknown formats, synthetic distribution shift, uncalibrated votes, correlated coordinates and candidate extraction misses. A low score cannot certify safety.

## Privacy and governance

Only approved authored nonfunctional fixtures may populate the reference matrix. No live credentials, code upload, automatic retraining or user dismissal ingestion. Vectors are not guaranteed anonymous.

## Release decision

The AI usefulness gate failed on this synthetic benchmark. Keep the model experimental and optional; do not use it for model-based blocking or clearing findings. No real-world effectiveness or release readiness is established.
