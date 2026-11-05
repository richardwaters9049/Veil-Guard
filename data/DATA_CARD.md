# Data card — collection plan
Status: no training corpus collected. Teaching vectors in examples are not a dataset.

## Scope
Authored nonfunctional credential-shaped fixtures, placeholders and nonsecret hard negatives in disposable local repositories.

## Required records
Recipe/fixture/schema version; author/permission; licence; safe example ID; template/family/repository/derivation group; label and rationale; review status; split assignment; deduplication record.

## Exclusions
No live/stolen/leaked credentials, breached datasets, scraped code, proprietary user source or personal data. No provider API testing. Never import actual scan findings automatically.

## Split controls
Group connected examples by fixture repository, template family, copied values and derivation seed. Keep groups disjoint across train/validation/test. Freeze test manifest before tuning. Report actual group and class counts.

## Collection targets — not achieved
5,000–10,000 candidates, at least 50 independent template families and 20 fixture repositories. Include hard negatives and low-entropy positives; evaluate under realistic class imbalance too.

## Release checklist
Provenance reviewed: pending.
Nonfunctional fixture review: pending.
Licence approved: pending.
Labels reviewed and uncertainty isolated: pending.
Groups/splits/deduplication checked: pending.
Synthetic-only limitations recorded: pending.
