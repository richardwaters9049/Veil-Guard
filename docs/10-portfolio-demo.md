# Portfolio demonstration and case study

## One-sentence description

**Publication rule.** Support background claims with the [source register](13-sources.md) and performance claims with actual [evaluation evidence](07-evaluation-and-acceptance.md). Model cards describe intended uses and limitations ([R16](13-sources.md#r16)); a portfolio description should keep that distinction visible.

Veil Guard reviews staged Git content locally and evaluates whether an eight-dimensional KNN model can prioritise ambiguous credential candidates.

After an implemented and evaluated release, the case study may describe demonstrated behaviour using the measured release/version.

Add “experimental” to the model description until it passes the evaluation gates.

## Terminal demonstration

1. Show a disposable authored fixture repository with a fake secret-shaped value, placeholder and checksum. All are nonfunctional.
2. Stage the fixture, then alter only the working-tree copy. Explain why the index is the content that would be committed.
3. Run the staged scan. Show a redacted rule warning, ranked generic review and completeness summary.
4. Explain one finding: which safe exemplar IDs were closest and which standardised feature differences contributed.
5. Show eight coordinates and the Euclidean distance formula using fabricated teaching vectors.
6. Stage the clean replacement and repeat the scan.
7. Show a real measured benchmark table with sample sizes and limits; if AI did not help, say so.
8. End with the defensive scope, reproducibility and next research question.

Build and rehearse from the repository root with the pinned dependencies available.

```sh
cargo build --release --locked --offline
python3 scripts/portfolio_demo.py
```

The rehearsal stages an authored pattern fixture, cleans only its working-tree copy, and confirms that the scanner still blocks on the staged version. It explains the top-ranked generic review using redacted output and then stages the cleaned copy. The last scan confirms that the blocking finding disappears while generic reviews remain. Use the [worked eight-feature example](05-knn-and-linear-algebra.md) and [benchmark table](24-phase-six-evidence.md) alongside this terminal sequence for the recording.

The [105-second terminal recording](demo/veilguard.cast) is a paced replay of output from the rehearsal. It includes the rule finding, all eight distance contributions, the held-out result and the measured performance limit. The file uses the [asciicast v2 format](https://docs.asciinema.org/manual/asciicast/v2/).

Replay or regenerate it from the repository root.

```sh
asciinema play docs/demo/veilguard.cast
python3 scripts/portfolio_demo.py --record /tmp/veilguard-demo.cast
```

## Evidence to include on the portfolio

- Downloadable native binary for supported platforms and build instructions.
- Architecture illustration without any web UI.
- Threat model and no-network design.
- Eight-feature contract and worked vector example.
- Corpus/data card, grouped split manifest and reference-vs-native parity evidence.
- Baseline comparison including negative results and limitations.
- Short terminal recording with redacted outputs.
- Links to the eventual source repository, release and complete docs.

## Case study structure

A developer can edit a file after staging it. Veil Guard scans staged blobs and reports the locations Git would commit. Deterministic rules can block a commit. Generic candidates remain visible for review, with optional experimental ranking. See the [scanner architecture](03-architecture-and-stack.md).

The experiment fitted the model on authored synthetic training groups and selected its settings before evaluating 1,400 held-out candidates across 14 fixture repositories. Standardised KNN reached mean repository Precision@20 of 0.539 against entropy's 0.500. The 7.86% relative gain missed the 10% target, and the paired interval crossed zero. Validation also failed to find a policy that met its coverage and error targets, so the frozen model leaves every candidate in review. These results describe the synthetic fixtures. See the [sealed evaluation](21-phase-four-results.md) and [model card](../models/MODEL_CARD.md).

Exact partial selection reduced measured p95 from 3.052 seconds to 0.506 seconds at 10,000 model-scored candidates on the local Apple M4, with 30.5 MiB peak RSS after the change. The native implementation matched the Python reference across 12,132 parity predictions. See the [benchmark and runtime record](24-phase-six-evidence.md).

The merged Phase Six workflow passed runtime instrumentation and native development package checks on macOS arm64 and Ubuntu x86_64. Public distribution still requires the owner’s licence and naming decisions, native library patch review, and signing and verification evidence. See the [merged CI run](https://github.com/richardwaters9049/Veil-Guard/actions/runs/42275367282) and [development installation guide](25-install-and-verification.md).

## Claims to avoid

“AI proves credentials are valid”, “zero false positives”, “prevents every leak”, “trained on real credentials”, “unique first secret scanner” or any percentage without its benchmark denominator. Existing scanners remain relevant; explain the specific experiment honestly.
