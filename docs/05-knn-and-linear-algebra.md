# KNN and linear algebra in R^8

## What is trained

**Mathematical sources.** Nearest-neighbour classification is established ([R03](13-sources.md#r03), [R04](13-sources.md#r04)). Matrix/norm notation follows standard linear algebra ([R05](13-sources.md#r05)); preprocessing follows StandardScaler ([R10](13-sources.md#r10)). The application-specific eight coordinates, abstention policy, tie rules and example below are our design/derivation. Classical asymptotic results are not a finite-sample guarantee for this corpus.

KNN is supervised instance-based learning. It stores labelled reference vectors rather than learning neural-network weights through back-propagation. Training here consists of collecting and labelling safe examples, fitting preprocessing on training groups, selecting k by grouped training-fold validation and decision thresholds using the separate validation groups and exporting reference vectors plus preprocessing parameters.

Each candidate is one point in an eight-dimensional vector space. Training data form X in R^(n×8); labels y in {sensitive_candidate, benign_fixture}^n. An uncertain label is never forced into either training class.

## Standardisation as a linear/affine transformation

For coordinate j, compute the training mean μj and population standard deviation σj (ddof=0), consistent with StandardScaler's documented convention ([R10](13-sources.md#r10)). Set sj=σj when σj>0 and sj=1 otherwise. With D=diag(s1,...,s8):

z = D^(-1)(x - μ)

For the full row-oriented matrix:

Z = (X - 1_n μ^T) D^(-1)

This preserves exactly eight dimensions. Centering is affine; diagonal scaling supplies the linear part. The same frozen μ and D apply to validation, test and runtime points. Never refit on user code. Zero-variance training features are noted in the model card; out-of-range queries can trigger review.

## Distance and neighbours

Baseline metric is Euclidean distance in the standardised space:

d(z,z_i) = ||z-z_i||_2 = sqrt((z-z_i)^T(z-z_i))
         = sqrt(Σ(j=1..8) (z_j-z_ij)^2)

No learned feature weights are used in the first experiment. Weinberger and Saul study learned metrics ([R08](13-sources.md#r08)); Weinberger's dissertation is further reading ([R09](13-sources.md#r09)), not a method implemented in v1. A later positive diagonal metric W would give sqrt((z-z_i)^T W(z-z_i)); any such change requires fresh grouped validation and a model-version change. Do not tune W on the test set.

Find the k smallest distances using exact brute-force search. Sort equal distances by stable safe example ID so Python and Rust are deterministic. Candidate k values are 3,5,7,11,15, restricted to k ≤ the smallest training fold. k is the neighbour count; 8 is the dimensionality. They are different quantities.

The [Phase Four protocol](20-phase-four-protocol.md) also compares uniform weighting during training-only model selection. The inverse-distance definition below applies when that weighting is selected.

## Inverse-distance vote

For a query with no exact matches, use w_i=1/d_i over its k neighbours.
The sensitive vote is:
s = Σ w_i * I(y_i=sensitive_candidate) / Σ w_i.

If one or more training rows have exactly zero distance, vote only among all zero-distance rows in the training set, with equal weights. Conflicting labels at identical vectors produce review. This explicitly avoids division by zero and duplicate-order dependence; the custom reference must match the native rule rather than assume every library's default is identical.

s is an uncalibrated weighted vote, not the probability a credential is real, usable or compromised. Probability calibration is a separate evaluation question ([R23](13-sources.md#r23)). Retain both rule verdict and model status.

## Abstention

Return review if the model is absent/incompatible, input is unsupported, identical vectors have conflicting labels, nearest distance is above a validation-selected threshold τ_distance, or |2s-1| is below τ_margin. Check raw feature support ranges from training to flag extrapolation, recognising that range checks alone do not detect all distribution shifts.

Thresholds are unset until validation. Abstentions retain a visible candidate with no automatic clearance. In MVP even a strong benign vote only changes ordering, never high-confidence rules or commit policy.

## Worked example — fabricated standardised coordinates

Query q = [0,0,0,0,0,0,0,0].
A sensitive = [1,0,0,0,0,0,0,0], distance 1.
B sensitive = [0,2,0,0,0,0,0,0], distance 2.
C benign    = [0,0,2,0,0,0,0,0], distance 2.
For k=3, weights are [1,0.5,0.5], so s=(1+0.5)/2=0.75.
For A, coordinate 1 contributes all of its squared distance; the other seven contribute 0.

These are teaching vectors after hypothetical scaling. They are not extracted feature rows, valid credentials, training data or evidence of performance. The example file and planning checker reproduce the arithmetic.

## Why KNN and where it may fail

It is small, inspectable and supports example-based explanations. Distance choice and dimensionality can undermine nearest-neighbour similarity ([R04](13-sources.md#r04)). For this project we additionally hypothesise risks from correlated features, class imbalance, synthetic data and unfamiliar formats; these require our own slice tests. Similar-looking benign and sensitive strings may share all eight features; no classifier can recover information discarded by that representation.

Use a simple exact implementation as the reference. Consider an index only after profiling and parity checks; an approximate nearest-neighbour service would add complexity without proving usefulness at this scale.
