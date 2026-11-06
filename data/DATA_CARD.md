# Data card — Veil Guard synthetic-v1

Status: authored prototype corpus and frozen splits implemented on 5 November 2026. No model has been trained or evaluated.

The reporting structure is informed by [Datasheets for Datasets, R15](../docs/13-sources.md#r15). Leakage prevention follows [R11](../docs/13-sources.md#r11), [R12](../docs/13-sources.md#r12) and [R14](../docs/13-sources.md#r14). Specific recipes, labels, counts and groups are project choices; these sources do not validate this dataset.

## Provenance, purpose and permission

Created for Veil Guard at Richard Waters' direction using project-authored generator code. Codex authored the recipes and performed the recorded assisted sample review; no label is attributed to an independent human reviewer. No third-party corpus, user repository, breached credential, scraped text or personal data is imported.

Purpose: reproducible internal experiments with the eight-feature credential-review hypothesis. sensitive_candidate means intended simulated credential use requiring review, not validity. benign_fixture means authored nonsecret identifier/example use. uncertain means no reliable binary class is asserted.

Values are generated from a fixed public test seed and have never been provisioned by this project. No provider API is contacted. Synthetic generation/provenance is the safety basis; shape checks do not prove provider validity or invalidity.

## Composition

| Partition | Rows | Groups | Sensitive | Benign | Uncertain |
| --- | --- | --- | --- | --- | --- |
| Train | 3,500 | 30 | 1,750 | 1,750 | 0 |
| Validation | 1,100 | 10 | 550 | 550 | 0 |
| Test | 1,400 | 10 | 700 | 700 | 0 |
| Challenge | 200 | 10 | 0 | 0 | 200 |

6,320 pre-deduplication records yield 6,200 canonical examples and 120 recorded aliases. There are 3,195 distinct values, 130 authored template families and 70 fixture repositories. These comprise 50 connected core split groups and 10 challenge groups. Family counts do not establish statistical independence.

Recipes cover opaque strings, hex/numeric identifiers, repeated values, UUID shapes, passphrases, prose, encoded-looking digests, placeholder-like values and demo markers. They include high-entropy hard negatives, low-entropy positives, credential-named benign fields and unfamiliar positive keys.

All 6,000 labelled rows have eight eligible features. Challenges include 60 eligible uncertain cases and 140 unsupported cases with no vector. The synthetic skewed test subset has 66 sensitive and 700 benign rows; it reuses held-out groups and does not estimate real-world prevalence.

## Records and controls

Each row records its schema, opaque ID, recipe, provenance, template family, repository group, derivation root, copy reference, intent label/rationale, authored source/value/span, feature schema, eligibility, eight coordinates where supported and split/group binding. The [row schema](../schemas/corpus-v1.json) and [implementation record](../docs/19-phase-three-corpus.md) specify the contract.

Related families, repositories, exact copied values, derivations and copy references remain in one connected component. Exact source/span/intent/provenance duplicates are recorded as aliases. Same values in distinct contexts remain connected, not silently discarded. The [split manifest](synthetic-v1/split-manifest.json) was frozen before any model fitting.

Source and split identities are portable. f64 vectors use numerical tolerance rather than a cross-platform byte-identity claim. Per-build environment/hash records accompany generated files.

## Review and corrections

The [sample review](synthetic-v1/label-review.json) contains 32 assisted reviews covering label/value-kind/eligibility strata and a targeted all-zero positive. No label correction was required. A repeated-pattern grouping defect and a multiline challenge-format defect were corrected before freezing.

This is assisted intent review, not independent human adjudication. Automatic checks verify schema, authored-label consistency, spans, feature values, deduplication, all grouping relations, held-out uncertainty and frozen identities. They do not establish real-world label quality.

## Distribution and maintenance

Corpus licence: NOASSERTION. No redistribution grant or licence approval is claimed; an owner decision remains required before distributing the generated dataset. The project contains no third-party corpus requiring imported permissions. This card is not legal advice or a compliance certification.

Committed: recipe, code, row contract, opaque split IDs, aggregate composition and assisted review metadata. Generated raw source/values and staged worktrees remain in ignored data/generated directories; output is private by default. The shipped scanner/model does not collect or export user scan findings into this corpus.

Future changes require deliberate curation, versioned recipes, a new frozen manifest and review updates. Never retune against current test outcomes or silently ingest feedback. No automatic collection is enabled.

## Limitations and release checklist

Synthetic labels describe authored intent. Templates share low-level string mechanisms and supported lexical syntax. Holdout groups do not prove independence of all latent factors or represent production repositories. Feature collisions, unknown formats, extraction misses, altered prevalence and real-world usefulness need separate evaluation.

| Gate | Status |
| --- | --- |
| Source/provenance and synthetic-only generation | Recorded and checked |
| Eight-coordinate and unsupported-input contract | Checked |
| Group isolation, aliases and frozen test membership | Checked |
| Stratified label sample | 32 assisted reviews recorded |
| Independent human label adjudication | Pending |
| Corpus redistribution licence | Owner/release decision pending |
| Synthetic-only limitations | Recorded |
| Detection/AI benefit measurements | [Synthetic evaluation](../docs/21-phase-four-results.md) recorded; AI benefit gate failed |
