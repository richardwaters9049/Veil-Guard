# Decisions, assumptions and risk register

## Decisions

**Evidence status.** This register records project decisions and qualitative risk judgements. Likelihood/impact labels are not empirical estimates. Git semantics inform D02 ([R17](13-sources.md#r17)); established KNN/scaling informs D05 ([R04](13-sources.md#r04), [R10](13-sources.md#r10)); persistence guidance informs D08 ([R19](13-sources.md#r19)). The user requirement determines D01/D04; these are not research findings.

| ID | Decision | Rationale |
| --- | --- | --- |
| D01 | Native CLI, no web UI | Fits the requested software format and developer workflow |
| D02 | Scan the index, not working tree | Matches what is actually about to be committed |
| D03 | Rust runtime, Python research | Native distribution with an independent scientific reference |
| D04 | Exactly eight explicit numeric features | Satisfies the requested KNN foundation and remains auditable |
| D05 | Standardised Euclidean exact KNN | Simple reproducible baseline before optimisation |
| D06 | KNN ranks generic candidates only in MVP | Keeps experimental model errors out of blocking/suppression policy |
| D07 | Synthetic, authored nonfunctional data first | Avoids exposure/use of real credentials |
| D08 | Strict JSON model, no pickle | Avoids executable model deserialisation |
| D09 | No provider validation or cloud calls | Source/credential privacy and clear ethical boundary |
| D10 | Working name, licence undecided | Do not imply brand clearance or an unchosen licence |

## Risks and responses

| Risk | Likelihood / impact | Planned response |
| --- | --- | --- |
| Eight features cannot separate classes | High / high | Measure collisions/ablations; keep claims narrow; publish failure |
| Synthetic corpus has unrealistic patterns | High / high | Hard negatives, grouped unseen families; no real-world claims |
| Candidate extraction limits dominate recall | High / high | Report end-to-end misses before model metrics |
| KNN latency with many rows/candidates | Medium / medium | Benchmark exact search, bound work and disclose incompleteness |
| Context features overlap | Medium / medium | Correlation/ablation study within training groups |
| Git semantics differ across edge cases | Medium / high | Unborn HEAD, partial staging, rename/symlink/conflict tests |
| Error path leaks source bytes | Medium / high | Central redaction, captured-output tests and minimal diagnostics |
| Existing scanners outperform the project | High / medium | Treat as baseline result and learning; avoid novelty claims |
| Developers infer “safe” from low rank | Medium / high | Review language, all findings visible, no model clearance |
| Distribution/brand conflict | Unknown / medium | Check naming and decide licence before distributing a software/model release |

## Assumptions to revisit

The first user is a consenting developer working in a local Git repository. macOS arm64 is the first platform. Candidate triage is useful enough to test, but adoption is unproven. No need for server infrastructure, native GUI, LLM integration or a database has been established.

Repository name resolved: **Veil-Guard**, with **Veil Guard** in documentation. [Published planning repository](https://github.com/richardwaters9049/Veil-Guard). Naming/trademark clearance is not implied.

## Open decisions

Licence; exact dependency versions; final grammar/rule set; achievable corpus independence; optimal k/abstention thresholds; whether measured ranking improvement justifies shipping AI by default. Do not fill these gaps with invented results.
