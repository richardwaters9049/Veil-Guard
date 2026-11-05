# Veil Guard

## Explainable, offline credential triage for staged Git changes

**Status: planning baseline — 5 November 2026.** No scanner, trained model or measured detection results exist yet. Veil Guard is a working project name; naming clearance is pending.

Veil Guard will be a native command-line developer security tool. It will read the Git index, identify possible hard-coded credentials, and use an eight-dimensional k-nearest neighbours model to rank ambiguous candidates for review. It will explain decisions using redacted locations, numerical feature differences and curated example IDs. It will have no web server, browser UI, dashboard or cloud inference.

### The industry problem

A 2019 NDSS study documented credential exposure in public GitHub repositories ([R01](docs/13-sources.md#r01)). A 2025 RIT master's thesis explores heuristic and ML secret detection beyond fixed patterns ([R02](docs/13-sources.md#r02)). These sources motivate this problem; they do not establish current prevalence or validate our proposed model. This project's testable hypothesis is that local KNN ranking can improve the order in which ambiguous candidates are reviewed. This is an engineering hypothesis, not a claim of proven superiority.

Existing tools already provide scanning and commit-workflow protection, including GitHub secret scanning ([R21](docs/13-sources.md#r21)) and Gitleaks ([R22](docs/13-sources.md#r22)). Veil Guard's portfolio contribution will be a reproducible experiment, privacy-conscious native implementation, transparent eight-dimensional inference and evidence of whether the additional AI helps. See [research and alternatives](docs/11-research-and-alternatives.md).

### Aim and expected outcome

Deliver a macOS arm64 CLI, followed by Linux x86_64 support, that scans staged text without executing repository code or transmitting source. High-confidence rules remain authoritative; the experimental model ranks generic findings and can abstain. A successful portfolio release includes an honest evaluation, reproducible dataset recipe, model card, threat model and a short terminal demonstration.

### Planned stack

Rust for the shipped CLI and inference; Python, NumPy and scikit-learn for offline experiments; versioned JSON for model exchange; GitHub Actions for checks and build artefacts. No database or JavaScript frontend.

### Evidence and academic foundation

Nearest-neighbour classification and distance-based learning are established methods ([R03](docs/13-sources.md#r03), [R04](docs/13-sources.md#r04)); vector/matrix notation follows standard linear algebra ([R05](docs/13-sources.md#r05)). Exactly eight features, offline operation and ranking-only policy are project choices. No scanner, training corpus, trained model or benchmark result exists yet.

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
| [Model card template](models/MODEL_CARD.md) | Intended use, evidence and limitations |
| [Data card template](data/DATA_CARD.md) | Provenance, consent and split accounting |

### Project contents

`schemas/feature-contract.json` is the machine-readable eight-feature contract.
`examples/illustrative-vectors.json` contains fabricated vectors to explain the mathematics, not training data.
`examples/finding.example.json` shows a fully redacted proposed output.
`scripts/check_plan.py` validates planning links, source citations and illustrative mathematics using Python's standard library. `docs/references.json` holds the structured source register. These checks do not verify source entailment, external link uptime or model performance.
`src/`, `research/` and `tests/` reserve implementation locations.

### First build task

Implement Rust reading of staged Git blobs, including partially staged files, and a rule-only redacted report. Validate that no working-tree-only changes are scanned. Only then implement feature parity and training.

### Run the current planning check

From this project directory:
```sh
python3 scripts/check_plan.py
```

The CLI commands shown in the plans are interface proposals. They are not installed or runnable yet. No Git hooks are installed by this planning scaffold.
