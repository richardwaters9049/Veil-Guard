# Research, alternatives and evidence
Reviewed 5 November 2026. These primary sources establish existing capabilities and mathematical practices, not performance evidence for Veil Guard.

## Existing security tooling
GitHub documents pattern/validation-based secret detection, paired-token handling and the false-positive tradeoffs affecting push-protection coverage:
https://docs.github.com/en/code-security/reference/secret-security/secret-scanning-scope

GitHub also documents AI-detected generic passwords. Therefore “uses AI for secrets” is not a novelty claim:
https://github.com/github/docs/blob/main/content/code-security/reference/secret-security/supported-secret-scanning-patterns.md

Gitleaks is an established CLI scanner with Git/file/stdin scanning and pre-commit integration. Its README currently states that new feature development has moved elsewhere; pin and record the exact release if used as a baseline:
https://github.com/gitleaks/gitleaks/blob/master/README.md

These sources support the existence of credential scanning and tradeoffs around ambiguous findings. They do not prove that Veil Guard's eight chosen features reduce false positives. That remains the core experiment.

## Positioning
| Approach | What it already addresses | Veil Guard's intended relationship |
| --- | --- | --- |
| GitHub secret scanning/push protection | Hosted detection and prevention with supported patterns and AI features | Different local deployment scope; do not claim replacement |
| Gitleaks | Mature CLI rules and developer integration | Baseline and inspiration; report scope/version differences |
| Entropy-only ranking | Simple local heuristic | Essential lightweight comparison |
| Veil Guard proposal | Redacted native staged-index workflow plus inspectable 8D KNN ranking | Test usefulness and publish reproducibility; benefit unproven |

No market-size estimate, cost-saving claim or product uniqueness assessment has been made. Before spending significant implementation time, validate with 3–5 consenting developers whether triage ordering actually helps; do not contact them automatically.

## ML and implementation references
scikit-learn nearest neighbours: classification, distance metrics, weighting and implementation choices:
https://scikit-learn.org/stable/modules/neighbors.html

StandardScaler: train-fitted means/scales and zero-variance handling:
https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html

scikit-learn common pitfalls: train/test isolation and preprocessing leakage:
https://scikit-learn.org/stable/common_pitfalls.html

Rust git2 Repository API: index/object access and tree-to-index comparison:
https://docs.rs/git2/latest/git2/struct.Repository.html

## Evidence boundaries
The mathematical description is an application of established KNN/linear algebra. Feature definitions, architecture, gates and expected benefits are project proposals. Synthetic experiments alone cannot demonstrate performance on real proprietary code. Review tool documentation and pinned dependency behaviour again when implementation begins.
