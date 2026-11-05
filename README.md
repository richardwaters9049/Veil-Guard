# Veil Guard

## Explainable, offline credential triage for staged Git changes

**Status: Phase Five inference core in development — 5 November 2026.** The staged scanner and repository hardening are implemented, with independent Rust/Python eight-feature extractors and golden parity checks. The synthetic corpus and frozen connected-group splits are now implemented; the unified acceptance command and per-commit CI verify this scope. A frozen research model and sealed synthetic evaluation exist; the KNN benefit gate failed and the model remains experimental. A native inference library is implemented; scanner integration and CLI explanations remain pending. Veil Guard is a working project name; naming clearance is pending.

Veil Guard will be a native command-line developer security tool. It will read the Git index, identify possible hard-coded credentials, and use an eight-dimensional k-nearest neighbours model to rank ambiguous candidates for review. It will explain decisions using redacted locations, numerical feature differences and curated example IDs. It will have no web server, browser UI, dashboard or cloud inference.

### The industry problem

A 2019 NDSS study documented credential exposure in public GitHub repositories ([R01](docs/13-sources.md#r01)). A 2025 RIT master's thesis explores heuristic and ML secret detection beyond fixed patterns ([R02](docs/13-sources.md#r02)). These sources motivate this problem; they do not establish current prevalence or validate our proposed model. This project's testable hypothesis is that local KNN ranking can improve the order in which ambiguous candidates are reviewed. This is an engineering hypothesis, not a claim of proven superiority.

Existing tools already provide scanning and commit-workflow protection, including GitHub secret scanning ([R21](docs/13-sources.md#r21)) and Gitleaks ([R22](docs/13-sources.md#r22)). Veil Guard's portfolio contribution will be a reproducible experiment, privacy-conscious native implementation, transparent eight-dimensional inference and evidence of whether the additional AI helps. See [research and alternatives](docs/11-research-and-alternatives.md).

### Aim and expected outcome

Deliver a macOS arm64 CLI, followed by Linux x86_64 support, that scans staged text without executing repository code or transmitting source. High-confidence rules remain authoritative; the experimental model ranks generic findings and can abstain. A successful portfolio release includes an honest evaluation, reproducible dataset recipe, model card, threat model and a short terminal demonstration.

### Planned stack

Rust for the shipped CLI and inference; Python, NumPy and scikit-learn for offline experiments; versioned JSON for model exchange; GitHub Actions for checks and build artefacts. No database or JavaScript frontend.

### Evidence and academic foundation

Nearest-neighbour classification and distance-based learning are established methods ([R03](docs/13-sources.md#r03), [R04](docs/13-sources.md#r04)); vector/matrix notation follows standard linear algebra ([R05](docs/13-sources.md#r05)). Exactly eight features, offline operation and ranking-only policy are project choices. A narrow rule-only scanner now exists; independent eight-feature extraction and fixture parity are implemented. An authored synthetic corpus and frozen splits now exist; the [sealed evaluation](docs/21-phase-four-results.md) records a failed KNN benefit gate.

Start with the [annotated sources and professor profiles](docs/13-sources.md), including the RIT master's thesis and Weinberger's doctoral dissertation, then the [claims and evidence register](docs/14-claims-and-evidence.md). Each entry records its relevance, review scope and limits. University links are attribution, not endorsement.

### Documentation

| Document | Purpose |
| --- | --- |
| [Project brief](docs/01-project-brief.md) | Users, problem, scope, success and non-goals |
| [Requirements and CLI](docs/02-requirements-and-cli.md) | Behaviour, exit codes and examples |
| [Architecture and stack](docs/03-architecture-and-stack.md) | Native components and trust boundaries |
| [8D features](docs/04-eight-dimensional-features.md) | Exact ordered feature contract |
| [KNN and linear algebra](docs/05-knn-and-linear-algebra.md) | Matrices, scaling, distance and worked example |
| [Data and training](docs/06-data-and-training.md) | Ethical labelling, splits and export |
| [Evaluation](docs/07-evaluation-and-acceptance.md) | Baselines, metrics and release gates |
| [Ethics and threat model](docs/08-ethics-and-threat-model.md) | Authorisation, privacy and abuse boundaries |
| [Delivery plan](docs/09-delivery-plan.md) | Ordered implementation phases and effort |
| [Portfolio demonstration](docs/10-portfolio-demo.md) | Safe demo and evidence to publish |
| [Research and alternatives](docs/11-research-and-alternatives.md) | Primary sources and positioning |
| [Decisions and risks](docs/12-decisions-and-risks.md) | Rationale, uncertainties and mitigations |
| [Sources and academic reading](docs/13-sources.md) | Annotated references, professors, theses, dissertations and reading order |
| [Claims and evidence](docs/14-claims-and-evidence.md) | External evidence, choices, hypotheses, targets and pending results |
| [Phase One implementation](docs/15-phase-one.md) | Executable commands, milestone evidence and remaining work |
| [Candidate/report contract](docs/16-candidate-and-report-contract.md) | Implemented lexical grammar, byte spans, report v2 and filename policy |
| [Repository formats and automation](docs/17-repository-and-automation.md) | Supported layouts, refusal reasons and local/CI acceptance |
| [Phase Two feature parity](docs/18-phase-two-feature-parity.md) | Independent extractors, golden fixtures, distance contributions and reproduction |
| [Phase Three corpus](docs/19-phase-three-corpus.md) | Synthetic recipes, frozen splits, assisted reviews and staged fixture repositories |
| [Phase Four results](docs/21-phase-four-results.md) | Sealed synthetic evaluation and failed benefit gate |
| [Phase Five inference](docs/22-phase-five-native-inference.md) | Native library, validation, parity and remaining integration |
| [Research model card](models/MODEL_CARD.md) | Intended use, evidence and limitations |
| [Data card](data/DATA_CARD.md) | Provenance, consent and split accounting |

### Project contents

`schemas/feature-contract.json` is the machine-readable eight-feature contract.
`examples/illustrative-vectors.json` contains fabricated vectors to explain the mathematics, not training data.
`examples/finding.example.json` is an authored example of the current report-v2 contract; `schemas/report-v2.json` defines its JSON shape.
`scripts/check_plan.py` validates planning links, source citations and illustrative mathematics using Python's standard library. `docs/references.json` holds the structured source register. These checks do not verify source entailment, external link uptime or model performance.
`src/` contains the first Rust scanner; `tests/staged_scan.rs` exercises it. `research/` contains the independent Python reference, authored parity fixtures, the synthetic corpus generator/auditor and locked environment; frozen training and sealed evaluation artifacts are included.

### Build and run

From `/Users/richy/Documents/Github/veilguard`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: uv==0.13.7
python3 scripts/check_all.py
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository
cargo run --locked -- scan --staged --repo /absolute/path/to/owned-repository --format json
```

Replace the example repository path with a directory you own or have permission to inspect. The current scanner detects two narrow patterns and reports quoted/unquoted lexical candidates for review; it is not a comprehensive scanner or language parser. Exit 0 can include review findings and does not establish safety. See [current scope and limits](docs/15-phase-one.md).

Phase Two's [parity record](docs/18-phase-two-feature-parity.md) describes the implemented scope, locked environment and reproduction commands. The [Phase Three record](docs/19-phase-three-corpus.md) describes 6,200 synthetic examples, frozen splits and assisted review limits. The [Phase Four results](docs/21-phase-four-results.md) record the negative research outcome. The [Phase Five inference core](docs/22-phase-five-native-inference.md) is implemented; next is scanner and explanation integration under the [delivery plan](docs/09-delivery-plan.md).

### Run the current planning check

From this project directory:
```sh
python3 scripts/check_plan.py
```

The scan command is runnable from source. Explain, model inspection and hook commands remain proposals for later phases. No Git hooks are installed by scanning.
