# Research, alternatives and evidence

Evidence revision: 5 November 2026. This is a focused planning review, not a systematic review or independent replication. Full citations, source links, university profiles, dissertations and review limits are in the [annotated sources](13-sources.md). The [claim register](14-claims-and-evidence.md) separates external evidence, mathematical derivations and project hypotheses.

## The security problem

Meli, McNiece and Reaves document credential leakage in public GitHub repositories in their 2019 NDSS study ([R01](13-sources.md#r01)). This is historical evidence of a real security problem. We do not extrapolate its counts to 2026, to all companies or to private repositories.

Our proposed intervention is local review before a commit. Whether developers need another triage tool, and whether its ordering reduces review effort, remain product hypotheses. Validate those with 3–5 consenting developers using safe examples before committing to broad implementation. This sample is an exploratory interview target, not statistical proof of market demand. Do not contact people automatically.

## Closely related academic work

Burdick-Pless's 2025 RIT MS thesis proposes heuristic/vector and neural-network approaches for distinguishing potential secrets from other strings ([R02](13-sources.md#r02)). Its institutional abstract is directly relevant to our problem. We have not reviewed its full experiments, adopted its dataset or reproduced any result. It cannot be cited as proof that our exact feature set or KNN works.

This prior work means “using ML for secret detection” is not a defensible novelty claim. Our portfolio contribution should be a reproducible implementation and experiment: staged-index behaviour, redacted outputs, an explicit eight-feature contract and a candid baseline comparison.

## KNN and linear algebra

Cover and Hart provide foundational nearest-neighbour research ([R03](13-sources.md#r03)); Cornell's lecture explains neighbourhood voting, distance choice and dimensionality effects ([R04](13-sources.md#r04)). Boyd and Vandenberghe provide the vector/matrix background ([R05](13-sources.md#r05)). StandardScaler documents the centring/scaling convention we propose ([R10](13-sources.md#r10)).

The choice of exactly eight coordinates comes from the project brief. No source establishes that eight is optimal or sufficient. Likewise, the keyword dictionary, context rules, placeholder score, k search and abstention thresholds are our design decisions. They must be versioned and tested.

Weinberger and Saul's learned-metric work ([R08](13-sources.md#r08)) and Weinberger's doctoral dissertation ([R09](13-sources.md#r09)) provide a route for future study. The first implementation uses fixed standardised Euclidean distance, not learned Mahalanobis metrics or LMNN. The dissertation is further reading; its unreviewed chapters do not support implementation claims.

## Evaluation rather than borrowed accuracy

Leakage can make ML results overoptimistic ([R14](13-sources.md#r14)). Training-only preprocessing ([R11](13-sources.md#r11)) and group-disjoint validation ([R12](13-sources.md#r12)) inform our experiment. Precision/recall analysis is appropriate to investigate in imbalanced settings ([R13](13-sources.md#r13)). These sources motivate controls and metrics; our corpus construction and thresholds still need justification through actual experiments.

No accuracy, time saving, false-positive reduction, leak-prevention rate or runtime figure has been measured for Veil Guard. Published results from a different system or dataset must not be transferred to this project. Synthetic-only results, when available, will support synthetic-only claims.

## Existing tools and comparison scope

| Approach | Established capability / source | Planned comparison and limit |
| --- | --- | --- |
| GitHub secret scanning | Hosted scanning, including history; supported patterns include AI-based detection ([R21](13-sources.md#r21)) | Context for prior art; different deployment and policy scope |
| Gitleaks | Existing CLI and pre-commit integration ([R22](13-sources.md#r22)) | Pin exact release/configuration, report supported-pattern and scope differences |
| Entropy-only ranking | Uses a statistic grounded in Shannon entropy ([R06](13-sources.md#r06)) | Our simple heuristic baseline; entropy is not ground truth |
| Standardised logistic regression | Proposed simple alternative model | Same group split and features; record actual configuration |
| Veil Guard KNN | Proposed eight-feature, offline ranking | Rule-only prototype exists; no KNN implementation or demonstrated AI benefit yet |

Do not describe Gitleaks or GitHub as inferior on the strength of documentation. Do not label our different scanning scope a detection improvement. Pin versions before benchmarking rather than relying on a moving README or product page.

## Responsible engineering and reporting

OWASP provides secret-management guidance ([R20](13-sources.md#r20)); scikit-learn warns about unsafe pickle-based persistence ([R19](13-sources.md#r19)). Our response is an offline scanner with a bounded JSON model format and no credential validation. These are design choices requiring verification, not external certification.

Data cards ([R15](13-sources.md#r15)) and model cards ([R16](13-sources.md#r16)) inform provenance and limitations reporting. A source citation or a completed template cannot substitute for tests and measured results.

## Research gaps and decisions to revisit

- Does the staged candidate extractor cover enough supported syntax to be useful?
- Can the eight features separate difficult fixtures without leaking labels through generation templates?
- Does standardised KNN improve ordering against entropy and logistic regression on unseen groups?
- How often does it abstain, and what errors remain at each coverage level?
- Does any observed improvement survive an independently authorised, privacy-preserving evaluation beyond synthetic data?

The literature establishes relevant problems and methods. It does not answer these project-specific questions.
