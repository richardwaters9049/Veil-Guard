# Sources and academic reading

Evidence revision: 5 November 2026. Owner: Richard Waters.

This is an annotated source register, not evidence that Veil Guard works. Each entry states exactly what the source supports and what it does not. In-text citations link to stable R-number anchors below. Project choices, targets and measured results are separated in the [claim register](14-claims-and-evidence.md).

Research papers and official documentation are used for technical claims. University profiles establish attribution only. Access dates describe this review, not publication dates. “Reviewed” records the material inspected; it does not imply a full systematic review, independent replication or review of an entire thesis.

## University researchers and reading order

These links identify authors, supervisors and teaching resources. They do not imply collaboration, permission to use a dataset, or endorsement of Veil Guard. Profiles were checked on 5 November 2026.

| Researcher | University profile | Connection to this plan |
| --- | --- | --- |
| Bradley Reaves | [NC State Secure Computing Institute](https://sci.ncsu.edu/faculty/reaves/) | Co-author of the credential-leakage study, R01 |
| Kilian Q. Weinberger | [Cornell Computer Science](https://www.cs.cornell.edu/~kilian/) | Metric-learning researcher; author of R08 and doctoral dissertation R09 |
| Stephen P. Boyd | [Stanford Electrical Engineering](https://web.stanford.edu/~boyd/) | Co-author of the linear algebra textbook, R05 |
| Ivona Bezakova | [RIT faculty directory](https://www.rit.edu/directory/ixbvcs-ivona-bezakova) | Listed advisor of the RIT master's thesis, R02; supervisor credit is not authorship |

Suggested order: R01 for the security problem; R02 for closely related work; R04 and R05 for KNN and linear algebra; R10–R14 for experiment design; R15–R16 for reporting. R08 and R09 are advanced reading for a possible future metric-learning experiment.

## Dissertations and theses

- **Master's thesis:** Jesse Burdick-Pless, RIT, May 2025, R02. The institutional record provides its abstract, degree, advisor, committee and a download link. Only that record/abstract was used here; no numerical findings are adopted.
- **Doctoral dissertation:** Kilian Q. Weinberger, University of Pennsylvania, 2007, R09. [Author's publication record](https://www.cs.cornell.edu/~kilian/publications/publications.html) corroborates the title/year and supervisor. The 32 MB PDF exceeded the research viewer's retrieval limit. Its indexed title page and publication record were checked; its unreviewed chapters are further reading, not evidence for our claims.

## Annotated references

<a id="r01"></a>

### R01: Michael Meli, Matthew R. McNiece and Bradley Reaves (2019). How Bad Can It Git? Characterizing Secret Leakage in Public GitHub Repositories. NDSS.

- Type: Peer-reviewed conference paper.
- [Primary source](https://www.ndss-symposium.org/ndss-paper/how-bad-can-it-git-characterizing-secret-leakage-in-public-github-repositories/); [DOI](https://doi.org/10.14722/ndss.2019.23418).
- Supports: Historical evidence of credential leakage in public GitHub repositories; motivates defensive scanning.
- Limits: Does not measure today's leakage rate, private repositories or Veil Guard performance.
- Review scope: Abstract and paper introduction. Checked 2026-11-05.

<a id="r02"></a>

### R02: Jesse Burdick-Pless (2025). Beyond RegEx – Heuristic-based Secret Detection. MS thesis, Rochester Institute of Technology.

- Type: Master's thesis.
- [Primary source](https://repository.rit.edu/theses/12111/).
- Supports: Related work on heuristic/vector and neural-network approaches to secret detection; advisor listed as Ivona Bezakova.
- Limits: Not a KNN validation, not the source of our eight features; full thesis experiments have not been independently assessed.
- Review scope: Institutional record and abstract. Checked 2026-11-05.

<a id="r03"></a>

### R03: Thomas M. Cover and Peter E. Hart (1967). Nearest Neighbor Pattern Classification. IEEE Transactions on Information Theory 13(1), 21–27.

- Type: Peer-reviewed journal paper.
- [Primary source](https://isl.stanford.edu/~cover/papers/transIT/0021cove.pdf); [DOI](https://doi.org/10.1109/TIT.1967.1053964).
- Supports: Foundational nearest-neighbour classification.
- Limits: Asymptotic results under assumptions do not guarantee finite-data accuracy for this project.
- Review scope: Original paper, introductory definitions and stated asymptotic result. Checked 2026-11-05.

<a id="r04"></a>

### R04: Cornell University CS4780 (2018). Lecture 2: k-nearest neighbors / Curse of Dimensionality.

- Type: University teaching material.
- [Primary source](https://www.cs.cornell.edu/courses/cs4780/2018fa/lectures/lecturenote02_kNN.html).
- Supports: KNN classification, distance choice and geometric limitations.
- Limits: Illustrative teaching material; does not endorse eight dimensions or our application.
- Review scope: Algorithm, metric and dimensionality sections. Checked 2026-11-05.

<a id="r05"></a>

### R05: Stephen Boyd and Lieven Vandenberghe (2018). Introduction to Applied Linear Algebra: Vectors, Matrices, and Least Squares. Cambridge University Press.

- Type: Academic textbook.
- [Primary source](https://www.web.stanford.edu/~boyd/vmls/).
- Supports: Background for vectors, norms, matrices and linear transformations.
- Limits: Our eight-feature representation and worked example are project constructions.
- Review scope: Author-hosted book page and linked teaching resources. Checked 2026-11-05.

<a id="r06"></a>

### R06: Claude E. Shannon (1948). A Mathematical Theory of Communication. Bell System Technical Journal 27, 379–423 and 623–656.

- Type: Foundational research paper.
- [Primary source](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf).
- Supports: Mathematical background for discrete Shannon entropy.
- Limits: Character-frequency entropy of one string is not a measure of credential validity or a password-strength guarantee.
- Review scope: Original paper, discrete entropy formulation. Checked 2026-11-05.

<a id="r07"></a>

### R07: Robert A. Wagner and Michael J. Fischer (1974). The String-to-String Correction Problem. Journal of the ACM 21(1), 168–173.

- Type: Peer-reviewed journal paper.
- [Primary source](https://computingbiology.github.io/docs/wagner1974.pdf); [DOI](https://doi.org/10.1145/321796.321811).
- Supports: Insertion, deletion and substitution edit distance.
- Limits: The normalised placeholder similarity and dictionary are our choices, not a proven security classifier.
- Review scope: Original article, abstract and edit-distance definition. Checked 2026-11-05.

<a id="r08"></a>

### R08: Kilian Q. Weinberger and Lawrence K. Saul (2009). Distance Metric Learning for Large Margin Nearest Neighbor Classification. JMLR 10, 207–244.

- Type: Peer-reviewed journal paper.
- [Primary source](https://jmlr.org/papers/v10/weinberger09a.html).
- Supports: Related work on learned distance metrics and linear transformations before nearest-neighbour classification.
- Limits: Veil Guard v1 uses fixed standardisation and Euclidean distance; it does not implement LMNN.
- Review scope: Journal abstract and author publication record. Checked 2026-11-05.

<a id="r09"></a>

### R09: Kilian Quirin Weinberger (2007). Metric Learning with Convex Optimization. PhD dissertation, University of Pennsylvania; supervisor Lawrence K. Saul.

- Type: Doctoral dissertation.
- [Primary source](https://www.cs.cornell.edu/~kilian/papers/dissertation.pdf).
- [Corroborating author record](https://www.cs.cornell.edu/~kilian/publications/publications.html).
- Supports: Further academic reading on metric learning; bibliographic details corroborated by the author.
- Limits: Background reading only; no implementation or performance claim relies on unreviewed chapters.
- Review scope: Title-page metadata and author's publication listing; full dissertation not reviewed. Checked 2026-11-05.

<a id="r10"></a>

### R10: scikit-learn developers. StandardScaler API documentation.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).
- Supports: Train-fitted centring/scaling, ddof=0 and scale 1 for zero variance.
- Limits: Standardisation does not guarantee better detection or remove feature correlation.
- Review scope: Formula, scale handling and Notes. Checked 2026-11-05.

<a id="r11"></a>

### R11: scikit-learn developers. Common pitfalls and recommended practices.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/common_pitfalls.html).
- Supports: Separate training/test data and fit preprocessing only on training data.
- Limits: Our connected-family split design is a project adaptation, not a claim that a library discovers leakage automatically.
- Review scope: Data leakage and preprocessing guidance. Checked 2026-11-05.

<a id="r12"></a>

### R12: scikit-learn developers. GroupKFold API documentation.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html).
- Supports: Cross-validation with group-disjoint folds.
- Limits: We must construct correct groups and verify them; GroupKFold alone cannot identify related fixtures.
- Review scope: Non-overlapping group definition. Checked 2026-11-05.

<a id="r13"></a>

### R13: Takaya Saito and Marc Rehmsmeier (2015). The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets. PLOS ONE 10(3), e0118432.

- Type: Peer-reviewed journal paper.
- [Primary source](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432); [DOI](https://doi.org/10.1371/journal.pone.0118432).
- Supports: Rationale for precision/recall-based assessment under class imbalance.
- Limits: Does not prescribe our Precision@20, acceptance threshold or bootstrap protocol.
- Review scope: Abstract and evaluation discussion. Checked 2026-11-05.

<a id="r14"></a>

### R14: Sayash Kapoor and Arvind Narayanan (2023). Leakage and the reproducibility crisis in machine-learning-based science. Patterns 4(9), 100804; preprint first submitted 2022.

- Type: Peer-reviewed journal paper with author preprint.
- [Primary source](https://arxiv.org/abs/2207.07048); [DOI](https://doi.org/10.1016/j.patter.2023.100804).
- Supports: Evidence that leakage can create overoptimistic ML evaluations.
- Limits: General ML methodology, not a benchmark of credential detectors.
- Review scope: Author preprint abstract and journal publication metadata. Checked 2026-11-05.

<a id="r15"></a>

### R15: Timnit Gebru et al. (2021). Datasheets for Datasets. Communications of the ACM; preprint first submitted 2018.

- Type: Research paper.
- [Primary source](https://arxiv.org/abs/1803.09010).
- Supports: Document dataset motivation, composition, collection and intended uses.
- Limits: Our data card adapts the framework; it is not a complete datasheet or a data-quality certification.
- Review scope: Author abstract and publication metadata. Checked 2026-11-05.

<a id="r16"></a>

### R16: Margaret Mitchell et al. (2019). Model Cards for Model Reporting. FAT* 2019; preprint first submitted 2018.

- Type: Research paper.
- [Primary source](https://arxiv.org/abs/1810.03993).
- Supports: Document intended use, evaluation conditions and limitations.
- Limits: An empty card does not establish model quality or safety.
- Review scope: Author abstract and publication metadata. Checked 2026-11-05.

<a id="r17"></a>

### R17: Git project. git-diff documentation.

- Type: Official technical documentation.
- [Primary source](https://git-scm.com/docs/git-diff).
- Supports: Staged changes compare the index with a commit, normally HEAD.
- Limits: Not proof that our future reader handles partial staging or untrusted repositories correctly.
- Review scope: Description of --cached/--staged and unborn HEAD. Checked 2026-11-05.

<a id="r18"></a>

### R18: git2 maintainers. Repository API documentation.

- Type: Official technical documentation.
- [Primary source](https://docs.rs/git2/latest/git2/struct.Repository.html).
- Supports: Available Rust interfaces for staged index/object access.
- Limits: Use of git2 does not by itself guarantee no external behaviour; audit the pinned version and call path.
- Review scope: Index, object and diff_tree_to_index APIs. Checked 2026-11-05.

<a id="r19"></a>

### R19: scikit-learn developers. Model persistence.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/model_persistence.html).
- Supports: Untrusted pickle/joblib deserialisation can execute code.
- Limits: Our bounded JSON loader still needs implementation and adversarial tests.
- Review scope: Security considerations for pickle-based formats. Checked 2026-11-05.

<a id="r20"></a>

### R20: OWASP Cheat Sheet Series. Secrets Management Cheat Sheet.

- Type: Security engineering guidance.
- [Primary source](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).
- Supports: Secret lifecycle handling and avoiding secret exposure in logs.
- Limits: Our offline-only scope and synthetic-only data policy are project decisions, not an OWASP certification.
- Review scope: Lifecycle, rotation, revocation and logging guidance. Checked 2026-11-05.

<a id="r21"></a>

### R21: GitHub. Secret scanning and supported secret scanning patterns.

- Type: Official product documentation.
- [Primary source](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning).
- [Additional official page](https://docs.github.com/en/code-security/reference/secret-security/supported-secret-scanning-patterns).
- Supports: Existing hosted scanning; supported-patterns documentation includes AI-detected patterns.
- Limits: Features and access can change; no superiority, pricing or completeness claim is made.
- Review scope: Concepts and supported-patterns pages. Checked 2026-11-05.

<a id="r22"></a>

### R22: Gitleaks maintainers. Gitleaks repository and README.

- Type: Primary software documentation.
- [Primary source](https://github.com/gitleaks/gitleaks).
- Supports: An existing CLI scanner with commit-workflow integration.
- Limits: Pin version/configuration for any future comparison; documentation is not an independent benchmark.
- Review scope: README usage and pre-commit sections. Checked 2026-11-05.

<a id="r23"></a>

### R23: scikit-learn developers. Probability calibration.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/modules/calibration.html).
- Supports: Probability interpretation requires assessment of calibration.
- Limits: No source establishes our vote as calibrated; we deliberately label it an uncalibrated score.
- Review scope: Calibration concepts. Checked 2026-11-05.

<a id="r24"></a>

### R24: scikit-learn developers. average_precision_score API documentation.

- Type: Official technical documentation.
- [Primary source](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).
- Supports: Average precision uses recall-increment weights and differs from trapezoidal PR area.
- Limits: Does not prescribe our top-k policy or establish project performance.
- Review scope: AP definition and comparison with trapezoidal integration. Checked 2026-11-05.

<a id="r25"></a>

### R25: Git project. gitrepository-layout documentation.

- Type: Official technical documentation.
- [Primary source](https://git-scm.com/docs/gitrepository-layout).
- Supports: Git supports multiple metadata and object-storage layouts.
- Limits: Veil Guard's refusal policy is narrower and project-specific; Git compatibility does not establish confinement.
- Review scope: Repository structure, Git files, common directories, objects/alternates and repository-format description. Checked 2026-11-05.

<a id="r26"></a>

### R26: libgit2 maintainers. git_repository_open_ext reference and repository implementation, v1.9.7.

- Type: Official technical documentation and primary source code.
- [Primary source](https://libgit2.org/docs/reference/v1.9.7/repository/git_repository_open_ext.html).
- [Pinned implementation](https://github.com/libgit2/libgit2/blob/v1.9.7/src/libgit2/repository.c).
- Supports: Explicit open flags control discovery/environment use; the implementation distinguishes normal versus environment-driven opening.
- Limits: Library opening can read standard global/system config; the project's preflight and local-config attachment are not a filesystem sandbox.
- Review scope: Explicit open flags; pinned crate source for config loading and environment-dependent object/index paths. Upstream tag corroborated through GitHub API.. Checked 2026-11-05.

<a id="r27"></a>

### R27: GitHub. Workflow syntax and GitHub-hosted runners reference.

- Type: Official technical documentation.
- [Primary source](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- [Additional official page](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
- Supports: Official workflow configuration and hosted-runner labels used by the acceptance pipeline.
- Limits: A defined workflow or available runner is not a passing CI result; verify the per-commit run.
- Review scope: Push/pull-request workflow configuration, permissions, matrix/timeout controls and supported runner labels. Checked 2026-11-05.

<a id="r28"></a>

### R28: Astral. uv project guide and locking/syncing documentation.

- Type: Official technical documentation.
- [Primary source](https://docs.astral.sh/uv/concepts/projects/sync/).
- [Project guide](https://docs.astral.sh/uv/guides/projects/).
- Supports: Project manifests/environments, committed lockfiles and locked mode that refuses automatic lock changes.
- Limits: A dependency lock does not pin the interpreter, establish network isolation or validate feature parity.
- Review scope: Project structure and locked-mode consistency checks. Checked 2026-11-05.

<a id="r29"></a>

### R29: Git project. git-init, Git environment variables and Pro Git: Git Objects.

- Type: Official technical documentation.
- [Initialisation reference](https://git-scm.com/docs/git-init).
- [Environment reference](https://git-scm.com/docs/git).
- [Object storage and hashing](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects).
- Supports: Explicit templates/SHA-1 object format, configuration overrides and header-plus-content blob identity used by authored fixture verification.
- Limits: These controls do not establish an OS sandbox, corpus label quality or measured scanner recall.
- Review scope: Initialisation options, GIT_CONFIG_GLOBAL/SYSTEM overrides, Git location variables and blob header/hash construction. Checked 2026-11-05.

## Stack documentation

These official pages describe component capabilities. They do not establish that our integration is secure or that one language/tool is superior. Phase One runtime versions are pinned in Cargo.lock and rust-toolchain.toml; the Phase Two research manifest and uv lockfile are committed; ML dependencies remain future work.

| Component | Primary documentation | Use in this plan |
| --- | --- | --- |
| Rust | [Ownership](https://doc.rust-lang.org/book/ch04-01-what-is-ownership.html) | Memory-management background; no claim of automatic secret erasure |
| clap | [Crate documentation](https://docs.rs/clap/latest/clap/) | Argument parsing/help |
| regex | [Crate documentation](https://docs.rs/regex/latest/regex/) | Regex syntax/performance limits; still bound input and pattern sizes |
| Serde | [Project documentation](https://serde.rs/) | Typed serialisation; strict validation is our responsibility |
| Cargo | [Manifest and lockfile](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) | Exact dependency-resolution record |
| uv | [Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) | Research environment locking |

## Citation maintenance

Before adding a factual claim, record its source, the relevant section, the scope of the evidence and any project inference. Cite the source near the claim. Avoid promotional claims, unattributed statistics and citations used as decoration. Historical measurements must keep their date, population and study scope.

Prefer publisher, university, author or official project pages. Keep author/title/year and DOI where available so a moved link can be repaired. For changing API/product pages, recheck at implementation and pin the version used in experiments. Do not copy third-party papers or datasets into this repository without permission/licence review.

The planning checker verifies local links, R-number anchors and source-register consistency. It does not validate external availability, research quality, source entailment or model performance. External pages were reviewed through the research browser; no blanket claim that every DOI resolves in every environment is made.
