# Offline research

Phase Two implements the independent [Python feature reference](feature_reference.py), [shared authored fixtures](fixtures/features-v1.json) and [locked environment](uv.lock). Phase Three adds the [synthetic corpus and frozen splits](../docs/19-phase-three-corpus.md). Phase Four now includes a frozen train-only scaler/model and a sealed synthetic evaluation. The benefit gate failed; see the [results and reproduction record](../docs/21-phase-four-results.md). The [Phase Two record](../docs/18-phase-two-feature-parity.md) gives setup, hand calculations and verification scope.

Entropy is grounded in [R06](../docs/13-sources.md#r06), edit distance in [R07](../docs/13-sources.md#r07), and environment locking in [R28](../docs/13-sources.md#r28). The exact eight-feature selection and lexical context remain project choices.

Follow the [data/training plan](../docs/06-data-and-training.md) and [evaluation contract](../docs/07-evaluation-and-acceptance.md). Training-only preprocessing is informed by [R11](../docs/13-sources.md#r11); non-overlapping validation groups by [R12](../docs/13-sources.md#r12). These sources do not validate our corpus generation or feature choices.

Use the [academic reading guide](../docs/13-sources.md) for KNN, linear algebra and dissertations. Record every experiment's source/configuration, split manifest and negative results. Never import a cited study's leaked-secret dataset or copy its performance figures as Veil Guard results. Print vectors only for approved synthetic fixtures; default scan reports omit them.

The approved recipe can generate 6,200 canonical examples into a new private directory. Optional materialisation creates 70 staged Git fixtures; the acceptance command verifies every staged source blob. Raw generated values stay in ignored data/generated directories. Frozen identities, composition and assisted review metadata are in data/synthetic-v1. Corpus licensing and independent human label review remain pending for release; see the [data card](../data/DATA_CARD.md).
