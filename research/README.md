# Offline research

Phase Two implements the independent [Python feature reference](feature_reference.py), [shared authored fixtures](fixtures/features-v1.json) and [locked environment](uv.lock). No training corpus, fitted scaler, model or measured accuracy exists yet. The [Phase Two record](../docs/18-phase-two-feature-parity.md) gives setup, hand calculations and verification scope.

Entropy is grounded in [R06](../docs/13-sources.md#r06), edit distance in [R07](../docs/13-sources.md#r07), and environment locking in [R28](../docs/13-sources.md#r28). The exact eight-feature selection and lexical context remain project choices.

Follow the [data/training plan](../docs/06-data-and-training.md) and [evaluation contract](../docs/07-evaluation-and-acceptance.md). Training-only preprocessing is informed by [R11](../docs/13-sources.md#r11); non-overlapping validation groups by [R12](../docs/13-sources.md#r12). These sources do not validate our corpus generation or feature choices.

Use the [academic reading guide](../docs/13-sources.md) for KNN, linear algebra and dissertations. Record every experiment's source/configuration, split manifest and negative results. Never import a cited study's leaked-secret dataset or copy its performance figures as Veil Guard results. Print vectors only for approved synthetic fixtures; default scan reports omit them.
