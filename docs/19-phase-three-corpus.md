# Phase Three: synthetic corpus and frozen splits

Updated: 5 November 2026. Branch: phase-three/safe-training-corpus. Base: merged main commit 204152d52987c8a25e042ce53b363325c80e3c8a.

The merged Phase Two baseline passed [macOS/Ubuntu acceptance](https://github.com/richardwaters9049/Veil-Guard/actions/runs/42018382777). This phase adds authored data and split-integrity checks. No model is fitted and no detection metric is measured.

Provenance reporting follows the questions in datasheets ([R15](13-sources.md#r15)); separation of related examples follows leakage guidance ([R11](13-sources.md#r11), [R14](13-sources.md#r14)) and grouped validation principles ([R12](13-sources.md#r12)). Our exact recipes, labels, grouping connections, counts and proportions are engineering choices. The sources do not validate this corpus or guarantee generalisation.

## Frozen composition

| Partition | Canonical examples | Connected groups | Sensitive / benign / uncertain |
| --- | --- | --- | --- |
| Train | 3,500 | 30 | 1,750 / 1,750 / 0 |
| Validation | 1,100 | 10 | 550 / 550 / 0 |
| Test | 1,400 | 10 | 700 / 700 / 0 |
| Challenge | 200 | 10 | 0 / 0 / 200 |
| Total | 6,200 | 60 | 3,000 / 3,000 / 200 |

There are 6,320 authored input records, 120 removed exact duplicates and 3,195 distinct values. The corpus has 120 labelled template families across 60 fixture repositories, plus 10 challenge families/repositories. The 50 core connected groups are the declared independent split units; 130 family IDs are not 130 statistically independent populations.

Group allocation is 60/20/20 for the labelled groups. Row proportions differ because some connected groups contain two repositories. A prespecified skewed test subset contains 66 sensitive and 700 benign examples (about 8.6% positive). It is a subset of the same held-out test groups, not another independent benchmark or an estimate of real-world prevalence.

All 6,000 labelled examples have eight eligible features. Of the 200 uncertain challenges, 60 are syntactically eligible and 140 remain unsupported without vectors. None enters a labelled matrix.

## Authored generation and labels

The [recipe](../research/synthetic-recipe.json) uses a fixed public test seed. [corpus.py](../research/corpus.py) creates opaque strings, hexadecimal/numeric identifiers, repeated patterns, UUID-shaped values, word combinations, encoded-looking digests, placeholder-like values and demo-marked strings. The same value-generation mechanisms occur in both labelled classes. A demo marker is not exclusive to positives.

Contexts include quoted/bare assignments, quoted keys, camel-case names, function arguments and following comments. Hard negatives include high-entropy identifiers and placeholders in credential-named fields. Positives include unfamiliar keys, word-like values and an intentionally all-zero simulated credential.

Labels express authored use: a simulated credential needing review, a deliberately nonsecret example/identifier, or an uncertain challenge. They are not derived from entropy, keyword matches, feature similarity or scanner output. A positive is not a valid provisioned credential. Context and feature collisions between classes are possible and must be reported during evaluation.

No real repositories, leaked material, user text or scanner findings are ingested. Values are generated locally and never provisioned or sent to a provider. The recipe is a predictable test-data generator, not a cryptographic randomness claim.

## Connected groups and deduplication

A union graph connects examples sharing any family, repository, exact copied value, derivation root or explicit copy reference. Ten authored cross-repository copy links join repository pairs. Connectivity is transitive. A shared public build seed is configuration; a derivation root identifies an actual shared candidate ancestor.

Exact source/span/intent/provenance duplicates become aliases in the [deduplication record](../data/synthetic-v1/deduplication.json). Same values in distinct contexts or with different authored intent are retained and connected. Silently discarding those cases would conceal difficult examples.

The first repeated-pattern recipe accidentally connected additional repositories through equal values. It was revised before freezing; the gate was not relaxed. The [review log](../data/synthetic-v1/label-review.json) records this correction.

The [split manifest](../data/synthetic-v1/split-manifest.json) freezes group members and the skewed subset before fitting. Core groups are ordered by a deterministic seed/group digest, then assigned 30/10/10. Challenge groups are always separate. Changing a source, label, seed, recipe, schema or relevant implementation invalidates the frozen check; future corpus revisions require an explicit new review/version rather than silent regeneration.

## Review and release status

The 32 [assisted sample reviews](../data/synthetic-v1/label-review.json) cover each label/value-kind/eligibility stratum plus an all-zero positive. The reviewer inspected the authored context and intent; no label correction was required. Unsupported and ambiguous challenges retain uncertainty.

This is Codex-assisted review, not independent human adjudication. Independent label review remains pending. Corpus licensing is recorded as NOASSERTION; no redistribution grant or legal approval is asserted. Recipes, aggregate composition, opaque split IDs and review metadata are committed. The generated raw corpus/worktrees are excluded from Git. See the completed [data card](../data/DATA_CARD.md) before any dataset release.

## Formats and reproducibility

| Artefact | Purpose |
| --- | --- |
| [Corpus row schema](../schemas/corpus-v1.json) | Strict row fields, eligibility state and exactly eight ordered coordinates |
| [Composition](../data/synthetic-v1/summary.json) | Actual counts and class/eligibility balance |
| [Frozen split manifest](../data/synthetic-v1/split-manifest.json) | Input hashes, source identity, groups, members and test subset |
| [Corpus auditor](../research/corpus_audit.py) | Source/span/features, grouping, aliases, labels, uncertainty and review checks |
| [Builder](../research/build_corpus.py) | Approved recipe only; new private output directory; no arbitrary corpus-import option |
| [Fixture materialiser](../research/fixture_repositories.py) | Disposable staged Git worktrees and staged-blob verification |
| [Acceptance check](../scripts/check_corpus.py) | Regeneration against frozen artefacts plus full fixture materialisation |

Source/provenance identity and split assignments are byte-stable. Floating-point vectors are compared within the established 1e-9 tolerance; whole corpus.jsonl bytes need not match across math libraries. A build's environment record includes Python/OS/architecture, input hashes, Rust/Cargo metadata hashes and that build's JSONL digest. The materialisation record includes the Git version.

matrix_for returns only an eight-column numeric matrix, labels and safe IDs separately, from previously audited rows. It refuses challenge partitions, invalid vectors and inconsistent split bindings. No filename, family, repository, label or seed becomes a ninth coordinate.

The Python auditor is the executable acceptance validator; schema-shape consistency is also checked. This does not implement a general-purpose JSON Schema engine.

## Reproduce and materialise fixtures

Directory: /Users/richy/Documents/Github/veilguard. Use the existing pinned development environment from [Phase Two](18-phase-two-feature-parity.md#reproduce).

~~~sh
python3 scripts/check_all.py --offline
mkdir -p data/generated
.venv/bin/uv run --locked --offline --project research --python "$(command -v python3)" python research/build_corpus.py --output data/generated/reproduction-01 --materialise-repositories
~~~

The current local build is data/generated/synthetic-v1-staged, including its 70 staged worktrees.

The output must be new; existing directories/symlinks/files are refused. JSONL files are created with mode 0600 and new output directories with mode 0700 on the supported Unix hosts. Partial output may remain after a failure; it is not an accepted build.

The optional materialisation step creates 70 ordinary SHA-1 Git repositories with unborn HEADs and authored files staged, ready for later end-to-end evaluation. It uses an explicit empty template, skips inherited Git overrides and global/system configuration, and disables hooks for staging. Git documents those controls and blob hashing ([R29](13-sources.md#r29)). These development subprocesses are separate from the scanner runtime and do not inspect existing user repositories.

Acceptance creates all 70 repositories in a temporary directory, checks every staged blob against its authored UTF-8/LF bytes, checks worktree bytes and removes its temporary output. It does not measure scanner recall. No hooks, network clients or model are installed by this phase.

## Local verification

The unified local acceptance command passed 66 Rust tests, 20 Python tests, the 56 feature/context and two distance fixtures, frozen-corpus regeneration, all 70 staged-worktree/blob checks, source/link checks and the optimized staged-only scanner smoke fixture. The original parity maximum remains 4.44e-16 against a 1e-9 tolerance. The [acceptance workflow](https://github.com/richardwaters9049/Veil-Guard/actions/workflows/phase-one.yml) is the authoritative per-commit macOS/Ubuntu result.

## Next gate

Phase Four can use the frozen train groups for grouped model selection, validation for thresholds, and the locked test groups only after configuration freeze. Test membership is already fixed; no performance has been inspected. The [evaluation contract](07-evaluation-and-acceptance.md) still governs any synthetic-only result and any later release claim.
