# Programme delivery plan

Updated: 5 November 2026. Owner: Richard Waters. Programme: Veil Guard.

The goal is a native offline credential-review CLI with an evaluated eight-dimensional KNN component, reproducible evidence and a portfolio release. There is no web application or dashboard in this programme. All effort figures are planning estimates, not research findings or calendar commitments.

## Phase status and branch policy

| Phase | Status | Dedicated branch | Planned lead commit |
| --- | --- | --- | --- |
| 0: evidence-backed planning | Complete baseline | main | Feat/Docs: Sources added |
| 1: staged rule-only scanner | Implemented; per-commit acceptance gate | phase-one/staged-scanner | Feat/PhaseOne: Add staged scanner and programme roadmap |
| 2: eight-dimensional feature parity | Implemented; per-commit parity/acceptance gate | phase-two/eight-dimensional-features | Feat/PhaseTwo: Add eight-dimensional feature parity |
| 3: safe training corpus | Prototype implemented; release review items recorded | phase-three/safe-training-corpus | Feat/PhaseThree: Add safe corpus and grouped splits |
| 4: KNN research and evaluation | Evaluated; benefit gate failed, experimental only | phase-four/knn-evaluation | Feat/PhaseFour: Add reproducible KNN evaluation |
| 5: native model inference | Integrated experimental inference; local acceptance gate | phase-five/native-inference | Feat/PhaseFive: Add native KNN inference |
| 6: hardening and packaging | Hooks, local evidence and development packaging implemented; release gates open | phase-six/hardening-and-packaging | Feat/PhaseSix: Harden and package offline scanner |
| 7: portfolio release | Draft case study and terminal recording available | phase-seven/portfolio-release | Feat/PhaseSeven: Publish evaluated portfolio release |

Each phase has its own branch and commits. Phases One and Two are merged into main. Phase Three starts from merged commit 204152d52987c8a25e042ce53b363325c80e3c8a. Future branches start from the accepted preceding work; do not create empty or placeholder commits. Review each phase diff and evidence before integration into main. A phase may have several focused commits. Do not merge or tag a release merely because its branch exists.

## Dependencies and effort

Baseline estimate: 90–150 focused engineering hours, approximately 6–8 part-time weeks. Re-estimate after each gate. Phases 1–5 are sequential because each defines the inputs required by the next. Packaging preparation can begin earlier, but release approval requires the final integrated checks.

Git staged semantics motivate the first gate ([R17](13-sources.md#r17)); preprocessing isolation motivates the experiment gates ([R11](13-sources.md#r11)); data/model reporting informs the evidence gates ([R15](13-sources.md#r15), [R16](13-sources.md#r16)). Specific scope, hour estimates and acceptance thresholds are project choices.

## Phase 1: rule-only native scanner

Estimated effort: 18–28 hours. Goal: a useful scanner before ML exists.

### Milestone 1A: staged-index foundation

- Create a Cargo binary/library with a committed dependency lockfile.
- Read an index snapshot and Git objects; compare new bytes to HEAD bytes in memory.
- Handle unborn HEAD, partial staging, staged deletions and conservative rename-as-add behaviour.
- Detect GitHub-PAT-shaped strings and private-key markers as blocking pattern findings. Report sensitive-key assignments as unranked review.
- Return redacted text/JSON reports, static error codes, escaped paths and coverage reasons.
- Bound blob bytes, aggregate inspected bytes, findings and index entries; check a cooperative deadline.
- Refuse conflicts; disclose binary/non-UTF-8 blobs, changed symlinks and submodules.
- Write new report files privately without replacing existing files or symlinks.
- Verify the above with integration fixtures. Current evidence and remaining limitations: [Phase One record](15-phase-one.md).

Status: implemented in this branch, subject to recorded verification. This is a narrow rule-only milestone, not completion of the phase.

### Milestone 1B: candidate extraction and coverage contract

- [x] Implement quoted-literal and simple unquoted-assignment extraction.
- [x] Track bounded spans and occurrence IDs without serialising values; keep ambiguous inputs as review.
- [x] Cover escapes, comments, CRLF, repeated/multiple candidates, unsupported delimiters, Unicode and length boundaries.
- [x] Separate candidate/finding budgets and protect blocking-warning priority.
- [x] Align the report-v2 schema with an authored example and test its field contract.
- [x] Test observed-value filename scrubbing, budget fallback and incomplete-scan path withholding.
- [x] Review and restrict repository layouts, metadata redirects and corrupt baselines; record supported formats and residual race/resource limits.

The [candidate/report contract](16-candidate-and-report-contract.md) records what is implemented and the limits of this lexical grammar. The [repository/automation record](17-repository-and-automation.md) completes the scoped layout review and records the acceptance pipeline. Milestones 1B and 1C are implemented; the per-commit checks remain the acceptance gate.

### Milestone 1C: phase acceptance

- [x] Automate format/lint/test/documentation/release-smoke checks locally and in a macOS/Linux CI matrix.
- [x] Exercise input budgets, invalid metadata, panic-payload redaction, broken stdout and report-file failures.
- [x] Verify exact-index behaviour and no repository hook/filter/diff/fsmonitor execution in authored fixtures.
- [x] Record supported layouts, rules, exclusions, residual risks and the pinned toolchain/library.
- [x] Local Phase One checks pass for the declared scope; require a passing CI run for the accepted commit. No AI is implied.

The gate is complete for the documented prototype scope when local and CI checks pass. Packaging, strict process isolation, benchmarks and all ML gates remain later work; this is not a claim of complete protection against an active local attacker.

Exit artefacts: source, lockfile, executable instructions, rule/report contracts, regression fixtures and evidence record. No hooks, model or research dataset required.

## Phase 2: exactly eight features in Rust and Python

Estimated effort: 12–20 hours. Entry: accepted Phase 1 extractor. Implementation/evidence: [Phase Two record](18-phase-two-feature-parity.md).

- [x] Implement the [ordered feature contract](04-eight-dimensional-features.md) independently in Rust and Python.
- [x] Cover length, empirical character entropy, character ratios, context proximity, sensitive assignment and placeholder edit similarity.
- [x] Add reviewed hand-worked fixtures for every coordinate and boundary, including distances 0/80/81.
- [x] Establish a locked Python environment with uv; commit its lockfile.
- [x] Validate finite values, exact order/ranges, unsupported inputs and schema versions.
- [x] Write feature-level distance explanation fixtures without printing candidate values.

Gate: eight coordinates only; absolute cross-language error at most 1e-9 on golden fixtures; no context/label/filename leakage as hidden extra coordinates. This tolerance is a project target. Exit: independent extractors, fixtures, parity evidence and updated contract.

## Phase 3: ethical synthetic corpus and split manifest

Estimated effort: 15–25 hours. Entry: frozen feature semantics. Implementation and review status: [Phase Three record](19-phase-three-corpus.md).

- [x] Build deterministic authored fixture generators; never collect live, leaked or user-repository credentials.
- [x] Define labels from fixture intent and review, not scanner outputs.
- [x] Add hard negatives, low-entropy positives, placeholders in sensitive assignments and unfamiliar contexts.
- [x] Record recipe, author/permission, licence, safe IDs, seeds, families and repository groups.
- [x] Connect related families, copied values and derivations into independent split groups; inspect deduplication.
- [x] Freeze a train/validation/test manifest and an unseen-format challenge set.
- [x] Complete the [data card](../data/DATA_CARD.md), including composition, intended use, exclusions and maintenance.

Collection goals: 5,000–10,000 candidates, at least 50 families and 20 fixture repositories. These are provisional targets, not a proven sufficient sample size.

Prototype gate: authored nonfunctional corpus, explicitly identified assisted label sample, adequate connected split groups and no overlap. Independent human adjudication and a redistribution licence remain dataset-release gates. If groups collapse or labels are ambiguous, revise the corpus before training. Exit: recipes, manifest, reviewed data card and aggregate counts; no private source.

## Phase 4: KNN research and measured evaluation

Estimated effort: 15–25 hours. Entry: frozen Phase 3 corpus/test groups.

- Fit means/scales only on training folds; keep eight-dimensional matrix operations explicit.
- Compare rules, entropy ranking, standardised logistic regression, raw KNN and standardised KNN.
- Tune k on grouped training folds; select abstention thresholds using validation groups.
- Implement deterministic tie ordering, inverse-distance voting and the project's all-zero-distance rule.
- Freeze configuration, then evaluate the held-out groups once for the release decision.
- Report end-to-end extraction misses separately from candidate ranking.
- Publish exact metric definitions, sample sizes, group counts, prevalence, intervals, abstention and failures.
- Compare a pinned Gitleaks release with scope/configuration differences stated.
- Complete the experiment report and initial [model card](../models/MODEL_CARD.md).

Gate: reproducible results, no test-driven tuning, and an explicit pass/fail/unproven decision against the [evaluation contract](07-evaluation-and-acceptance.md). The proposed 10% Precision@20 target is not a promised result.

If KNN fails to improve ranking, retain optional experimental status and report that result. Do not replace it with an invented success. Exit: scripts, environment, frozen configs, results and model export specification.

## Phase 5: native inference and explanations

Estimated effort: 12–20 hours. Entry: documented Phase 4 decision and a frozen export.

- Export bounded JSON containing only approved reference vectors, labels, safe IDs and preprocessing/configuration.
- Implement strict schema, shape, finite-number, scale, k, size and version validation.
- Implement exact f64 standardisation, distance search, ties, voting and abstention in Rust.
- Keep deterministic rule findings authoritative and generic reviews visible.
- Implement model inspection and explanation commands with redacted reports.
- Support absent/corrupt models with usable rule-only scanning and explicit AI status.
- Verify reference/native neighbours, votes, zero distances and explanation contributions.

Gate: feature parity, deterministic inference parity and adversarial bundle tests pass. No pickle/joblib runtime or online learning. No model-based blocking. Exit: native inference, schema/exporter, completed parity record and updated report examples.

## Phase 6: integration, hardening and supported packages

Estimated effort: 12–20 hours. Entry: integrated Phase 5 candidate scanner.

- Add explicit hook installation/uninstallation that preserves existing hooks and supports manual integration.
- Validate end-to-end CLI, model degradation, report retention and remediation wording.
- Audit dependency/security/licence status and lockfiles; assess supply-chain and model distribution integrity.
- Benchmark cold/warm latency and peak memory on recorded hardware and workload.
- Test no-network operation and repository-defined-command non-execution; inspect crash/error/report paths.
- Package macOS arm64 first, then add Linux x86_64 CI and compatibility tests before claiming support.
- Document build/install/uninstall, upgrades, model provenance and release verification.
- Keep Windows, broad syntax expansion and automatic model updates out of this initial release.

Gate: all release checks pass and the [threat model](08-ethics-and-threat-model.md) reflects residual risk. Proposed 2s p95 / 150 MiB targets require actual measurements. Exit: packages, reproducible build/CI evidence, benchmark results and user guide.

## Phase 7: measured portfolio release

Estimated effort: 6–12 hours. Entry: accepted packages and evidence.

- Review all [claims](14-claims-and-evidence.md) against measured release evidence and source scope.
- Complete data/model cards and document negative findings.
- Confirm release naming/licence, supported platforms and distribution integrity.
- Record a 90–120 second demonstration using disposable nonfunctional fixtures.
- Show partial staging, redacted findings, eight-dimensional mathematics, inference and real benchmark limitations.
- Publish build/reproduction instructions and a case study with links to sources, code and evidence.
- Create the versioned release after the gates are satisfied; do not present a planning branch as finished software.

Gate: a fresh supported machine can reproduce an offline scan and the published experiment. Synthetic-only evidence supports synthetic-only claims. Exit: tagged native release, honest case study, demonstration and maintenance backlog.

## Definition of programme completion

All seven phase gates are recorded as passed or explicitly constrained; installation and offline staged scanning work on the claimed platforms; model results and limitations are reproducible; deterministic findings remain visible; no actual credentials enter demos/training; and the released claims match evidence.

AI benefit is an experimental outcome, not a mandatory positive finding. The programme can complete with a useful rule scanner and optional experimental KNN if the research result is negative. It cannot complete by omitting that result.

## Maintenance after release

Track supported syntax/rules, dependencies, reported regressions and model/schema compatibility. Every model change needs curated provenance and fresh independent validation. External evaluation requires permission and a privacy review. Expansion to Windows, AST parsing, learned metrics, calibrated probabilities or model blocking is a new scoped decision, not an unfulfilled requirement of this initial programme.
