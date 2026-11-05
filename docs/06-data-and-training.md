# Ethical data and training plan

## Data policy

**Methodological basis.** Dataset provenance/composition reporting is informed by datasheets ([R15](13-sources.md#r15)); leakage controls by ML methodology ([R11](13-sources.md#r11), [R14](13-sources.md#r14)) and group-disjoint cross-validation ([R12](13-sources.md#r12)). Synthetic-only collection, specific group connections, corpus sizes and split proportions are our choices. None is a proven minimum sample size or guarantee of real-world generalisation.

No breach dumps, public leaked credentials, active credentials or background harvesting from user repositories. Start with deliberately authored local synthetic fixture projects. Include secret-shaped values only as nonfunctional, unprovisioned strings authored for this lab; never call provider APIs to test them. Use an obvious synthetic marker where rules permit it and otherwise use a documented fake-only generation recipe. Real credential formats may be represented structurally without using someone's actual access material.

Public code is not automatically a safe or licensed training source. Any later external corpus needs documented licence, consent/permission, provenance and a review confirming it contains no live secrets or personal data. Repository scans never become training submissions.

## Labels and classes

- sensitive_candidate: fixture intentionally represents a credential requiring developer review; not a claim of validity.
- benign_fixture: intentionally authored placeholder, checksum, UUID, asset identifier, random test ID, sample prose or nonsecret constant.
- uncertain: insufficient ground truth; held out as an abstention challenge set.

Record fixture ID, authoring recipe version, provenance, family/template group, repository group, label, labelling rationale, features and feature-schema version. Raw lab fixture values live only in the separate safe fixture corpus; shipped model bundles contain vectors and safe IDs only. Labels must come from authoring intent and review, not from entropy/rule/model outputs. Otherwise the evaluation merely reproduces its own labelling rules.

## Corpus design

Target an initial 5,000–10,000 candidates across at least 50 independent fixture/template families and 20 fixture repositories. This collection goal is now met by the [Phase Three prototype](19-phase-three-corpus.md): 6,200 canonical examples, 130 authored families, 70 fixture repositories and 50 connected core split groups. Family counts do not guarantee statistical independence. Include common config/source contexts plus hard negatives, low-entropy credential-shaped fixtures, high-entropy checksums, placeholders in sensitive assignments and unfamiliar naming styles. Add a prevalence-skewed evaluation set resembling a normal repository; a balanced training set alone is misleading.

Review a stratified sample manually and maintain a correction log. Do not add templates until the generator passes safety and determinism checks. Do not promise a real-world benchmark from synthetic-only evidence.

## Split unit and leakage prevention

Build connected groups so candidates sharing a template family, fixture repository, copied value or derivation seed never cross splits. If grouping collapses into too few independent groups, revise the corpus rather than relax isolation. Approximate 60/20/20 group allocation is a target; report actual sizes and class balance.

Lock the test group list before fitting anything. On training groups use grouped cross-validation for k, weighting and any feature variants. Use validation groups to select abstention thresholds and final ranking configuration. Means/scales are fitted only on the relevant training fold via a pipeline, following guidance against preprocessing leakage ([R11](13-sources.md#r11)). No seed variants of a test template in training; deduplicate before splitting. Keep an unseen-format challenge set.

## Implemented corpus status

[synthetic-v1](../data/DATA_CARD.md) freezes 3,500/1,100/1,400 labelled train/validation/test rows and 200 isolated uncertain challenges. Its 32 assisted sample reviews are recorded; independent human review and the corpus redistribution licence remain release decisions. The synthetic skewed test subset is prespecified; production prevalence and real-world usefulness remain unmeasured. No model has been fitted.

## Training procedure

1. Version fixture recipe, feature contract and split manifest; record seeds.
2. Generate safe fixtures; label/review them; extract exactly eight features.
3. Create grouped train/validation/test assignments without inspecting test performance.
4. Compare rules-only, raw-feature KNN, standardised KNN and a standardised logistic-regression baseline.
5. Tune on training folds; choose the final configuration/abstention rules using validation only.
6. Freeze model configuration and artefact hash. Evaluate the test set once for the release decision.
7. Export validated JSON, model card and aggregate metrics; publish the limits.
8. Verify Rust/Python parity independently before bundling the model.

Do not refit using validation groups after choosing thresholds in this first release: that changes distances and invalidates those thresholds. A future refit requires a new independent calibration set. A disappointing result is recorded, not fixed by retuning against test labels.

## Export and reproducibility

Save feature order, μ, s, Z_train, labels, safe IDs, k and exact-vote/abstention rules. Record Python/Rust versions, lockfile hashes, OS, seeds, recipe revision, split digest and training artefact digest. Keep no pickle/joblib dependency at runtime. Export makes no claim that vectors are anonymous: they still carry aggregate information and must originate from the approved safe corpus.

## Later maintenance

No automatic feedback ingestion. Model changes require deliberate curated examples, a new model version and fresh group-disjoint tests. Introduce drift warnings only after establishing a baseline; user repositories cannot silently update the reference set.
