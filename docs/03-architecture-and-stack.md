# Architecture and tech stack

## Runtime data flow

**Proposed architecture.** This sequence describes software to build. Git index semantics ([R17](13-sources.md#r17)) and git2 object/index APIs ([R18](13-sources.md#r18)) inform the reader design; neither source certifies the future implementation. Component capabilities are linked in the [stack references](13-sources.md#stack-documentation).

1. CLI parses arguments and establishes local repository scope.
2. Git reader snapshots the index, compares against HEAD and reads object bytes.
3. Bounded candidate extractor and high-confidence rule engine inspect staged text in memory.
4. Feature extractor maps supported generic candidates to eight ordered numbers.
5. Local model loader validates the artefact; standardisation and exact KNN return rank or abstention.
6. Policy merges immutable rule findings with model annotations.
7. Redaction/output layer writes escaped locations and explanations.

The Rust scan process owns sensitive source bytes. Offline research receives only deliberately authored synthetic examples. There is no telemetry collector, daemon, HTTP endpoint, LLM API or database.

## Proposed stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Runtime | [Rust](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) stable, edition 2024 | Native distribution and explicit data handling |
| CLI | [clap](https://docs.rs/clap/latest/clap/) | Argument parsing/help, no frontend |
| Git index/object access | [git2/libgit2](https://docs.rs/git2/latest/git2/struct.Repository.html) | Read staged objects without shell interpolation or external diff helpers |
| Rules | [Rust regex](https://docs.rs/regex/latest/regex/), versioned rule metadata | Bounded regular expressions and auditable rules |
| Serialisation | [serde / serde_json](https://serde.rs/) | Non-executable model and report contracts |
| Inference | Small f64 exact brute-force KNN module | Eight features, inspectable mathematics, no Python runtime |
| Research | Python 3.12+, NumPy, scikit-learn | Reference pipeline, split/tuning/evaluation |
| Python environment | [uv](https://docs.astral.sh/uv/concepts/projects/sync/) with committed lockfile | Reproducible research environment once dependencies are chosen |
| Rust builds | [Cargo](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) with committed lockfile | Reproducible application dependency resolution |
| Testing | cargo test, pytest, golden parity fixtures | Native correctness plus independent reference |
| Automation | GitHub Actions | CI checks and native artefacts; workflows added later |
| Storage | Local JSON/JSONL and small CSV experiment summaries | No server or database requirement |

Exact dependency versions must be selected, audited and locked at implementation time. These are design choices, not claims about the newest releases. Initial support: macOS arm64. Next: Linux x86_64. Windows is deferred until path/index handling is tested.

## Intended source layout

- src/cli.rs: commands and exit handling.
- src/git_index.rs: repository/index snapshot and staged blob reading.
- src/repository.rs: layout/config policy, bounded metadata, baseline tree walking and control stamps.
- src/candidates.rs: bounded candidate extraction.
- src/rules.rs: deterministic rules and IDs.
- src/features.rs: eight-feature contract.
- src/knn.rs: scaling, exact search, voting and abstention.
- src/model.rs: strict JSON validation.
- src/report.rs: redaction, terminal escaping and output.
- research/: corpus recipe, training pipeline, evaluation and model exporter.
- tests/: staged-index integration, privacy and parity fixtures.

Milestone 1A implements `lib.rs`, `main.rs`, `git_index.rs`, `rules.rs` and `report.rs`. The index reader compares bounded object buffers in memory. `candidates.rs` now extracts bounded lexical spans and `privacy.rs` protects displayed paths. Eight-feature, model and KNN modules remain pending. See the [implementation record](15-phase-one.md) for the narrower current scope.

## Model bundle

Use JSON with schema/model versions, ordered feature names, train-only means/scales, transformed reference vectors of shape n×8, binary labels, safe example IDs, k, weighting policy, abstention thresholds, dataset manifest digest and build metadata. No raw candidate values, source text or paths from user repositories.

Reject non-finite values, unknown schemas, malformed dimensions, non-positive scales, unknown labels, invalid k and excessive rows/file sizes. Proposed caps: 50,000 rows and 32 MiB JSON. From the eight-coordinate sum, computing n distances costs O(8n) per query; fully sorting them adds O(n log n) work. This is an algorithmic derivation, not a latency measurement; cap candidates and benchmark the combined worst case before release. Reject a bundle or scan workload that exceeds configured resources rather than exhausting memory.

Never unpickle or load joblib artefacts in the shipped CLI. scikit-learn warns that pickle-based loading can execute arbitrary code ([R19](13-sources.md#r19)). Bounded JSON is our design response; it still needs parser/resource validation. Verify bundled model SHA-256 against release metadata for accidental corruption. A hash bundled beside a model is not authenticity protection; signed releases/attestation and a pinned verification key are a later distribution gate. User-provided models are explicitly marked untrusted/experimental.

## Trust boundaries

Repository bytes and repo configuration are untrusted. Do not execute hooks, build scripts, filters, textconv, external diffs or repository-defined commands. Do not recurse into submodules or follow repository metadata symlinks. Source blobs must come from the verified local object store. Initial library open may consult standard trusted user/system Git configuration; the [repository boundary](17-repository-and-automation.md) documents this distinction and the residual race risk. Treat Git configuration that enables external behaviour as disabled in the reader.

Training artefacts cannot grant file/network actions. Reports can contain sensitive paths; store explicit output with restrictive permissions where supported, refuse symlink destinations and use atomic writes. Redact before formatting and serialisation. Rust memory safety does not guarantee zeroisation of every allocation or crash dump; document the remaining local-machine exposure.
