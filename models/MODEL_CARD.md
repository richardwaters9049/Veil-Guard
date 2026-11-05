# Model card — untrained template
Status: no model exists. Model ID: unset. Feature schema: veilguard.features.v1.

## Intended use
Offline prioritisation of ambiguous credential candidates in staged Git text. Human review required. No credential validity inference, autonomous remediation or MVP model-based blocking.

## Method
Exactly eight numeric coordinates; train-fitted standardisation; exact Euclidean KNN; inverse-distance vote with explicit zero-distance handling; review/abstention rules. Runtime Rust, independent reference Python.

## Training and evaluation — complete before release
Dataset/recipe version: unset.
Provenance and licence/permission: unset.
Train/validation/test independent groups and rows: unset.
Class balance and prevalence assumptions: unset.
k, μ, scales, thresholds and model hash: unset.
Baselines, metrics, intervals and slice results: not measured.
Native/reference parity: not tested.
Supported distributions and platform workload: not validated.

## Limitations
Feature collisions, unsupported syntax, unknown formats, synthetic distribution shift, uncalibrated votes, correlated coordinates and candidate extraction misses. A low score cannot certify safety.

## Privacy and governance
Only approved authored nonfunctional fixtures may populate the reference matrix. No live credentials, code upload, automatic retraining or user dismissal ingestion. Vectors are not guaranteed anonymous.

## Release decision
Unset. Record whether the AI usefulness gate passed, failed or remains unproven. Keep experimental status until evidence exists.
