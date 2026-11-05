# Phase Two: eight-dimensional feature parity

Updated: 5 November 2026. Branch: phase-two/eight-dimensional-features. Development version: 0.1.0-dev.4.

This phase implements the [eight-coordinate contract](04-eight-dimensional-features.md) independently in Rust and Python. Entropy follows [R06](13-sources.md#r06), edit distance follows [R07](13-sources.md#r07), and the distance decomposition follows the squared Euclidean norm ([R05](13-sources.md#r05)). Feature selection, dictionaries, lexical context and tolerances are project choices. These references do not validate detection quality.

## Implementation boundary

| Component | Implemented behaviour |
| --- | --- |
| Rust library | [features.rs](../src/features.rs): from_line validates an exact eligible candidate occurrence, then returns eight f64 coordinates |
| Python reference | [feature_reference.py](../research/feature_reference.py): independent lexical parsing, character counting and full-table edit distance |
| Rust edit distance | Rolling-row dynamic programming, independently checked against the Python table and golden cases |
| Candidate grammar | Existing candidates.v1; Rust assignment recognition and proximity share keyword tokenisation |
| Context | One physical UTF-8 line, source byte offsets excluding enclosing quotes, at most 1 MiB |
| Unsupported input | Fixed error codes/unranked review; no padded or imputed vector |
| Numeric helpers | Apply an explicitly supplied mean/positive scale; eight squared distance contributions |
| Runtime reports | Report v2 remains unchanged; no vectors, source values, scores or neighbours |
| Model | Still not_implemented; no corpus, fitted scaler, training, inference or accuracy result |

The scanner's feature_eligible_candidates field still counts eligible syntax. Scan does not invoke the research extractor or rank findings. Native model integration belongs to Phase Five. A valid feature vector does not establish whether a value is a real credential.

Features has no Rust Debug/Serialize implementation. Explicit coordinate access exists for research/export; callers must not log vectors derived from private source. This is an API precaution, not secure memory erasure.

The [fixture harness](../examples/feature_fixtures.rs) has only compile-time authored examples. It accepts no input, source path or arbitrary fixture file, reads no repository and outputs fixture IDs/numbers only. Cargo does not include this example in the normal CLI build.

## Golden evidence

The [shared fixtures](../research/fixtures/features-v1.json) are authored, nonfunctional test strings. They are neither training data nor a test corpus for detection metrics. Expected vectors were written from frequencies, ratios, explicit byte gaps and edit matches; they are not populated from either extractor's outputs.

Representative hand calculations:

| Case | Expected calculation |
| --- | --- |
| password, length 8 | log length ln(9); one repeated s gives entropy 3 - 2/8 = 2.75; placeholder similarity 1 |
| Aa1!Aa1! | Four characters occur twice: entropy 2; digit, uppercase and symbol ratios each 1/4 |
| Eight spaces | Length stays 8; entropy 0; symbol ratio 1; placeholder similarity 0 |
| A repeated 256 times | ln(257); entropy 0; uppercase ratio 1; best dictionary match retains two a characters, similarity 2/256 |
| passw0rd | One substitution from password: similarity 1 - 1/8 |
| passworrd | One insertion from password: similarity 1 - 1/9 |
| placeholde | One deletion from placeholder: similarity 1 - 1/11; two l and two e give entropy log2(10) - 4/10 |
| Context gap 80 / 81 | Proximity 1/81 / 0 |
| Explicit diagonal scaler | z = [2,1,0.5,4,2,1,0.5,4]; zero-neighbour terms [4,1,0.25,16,4,1,0.25,16], sum 42.5 |

The zero-gap cases exercise the span-geometry helper directly: adjacent word/candidate spans give proximity 1. They do not claim that every arbitrary span is a valid lexical candidate. End-to-end cases separately require recognised syntax and test gaps 79/80/81 with quotes included in the byte gap.

Coverage includes case folding, every character class, preserved inner spaces, length 7/8/256/257, quoted/bare/camel/snake/hyphen keys, false substring matches, both context directions, repeated occurrences, Unicode context, invalid byte boundaries, escapes, expressions, templates and incomplete literals. Another quoted value can supply a keyword outside the selected occurrence; this lexical rule does not infer semantic ownership of context.

Numeric tests reject seven/nine coordinates, NaN/infinity, nonpositive scales and overflow. A zero-variance training column must later be exported with scale 1; this phase accepts positive supplied scales and does not fit training statistics.

The parity gate checks fixture/schema versions, the exact ordered names and indices, vocabulary, input limits, ranges, unsupported status, numerical agreement and hand-worked distance contributions. Gate regression tests deliberately alter schemas, ordering, dimension, coordinates and numeric validity to verify rejection. Passing fixtures establish agreement on these examples, not universal semantic equivalence or measured detection accuracy.

## Reproduce

Directory: /Users/richy/Documents/Github/veilguard. Rust is pinned by rust-toolchain.toml; Python 3.12 or newer is required. CI uses Python 3.12; local checks use 3.14.5.

Create the development tool environment once:

~~~sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: uv==0.13.7
python3 scripts/check_all.py
~~~

The acceptance script finds uv on PATH or in the root .venv. The [research manifest](../research/pyproject.toml) and [uv lockfile](../research/uv.lock) currently have no third-party research dependencies. uv's locked mode checks consistency and refuses automatic lock changes ([R28](13-sources.md#r28)). The lock records dependencies and the supported Python range; it does not pin the interpreter to one patch version.

Run only the parity gate:

~~~sh
.venv/bin/uv run --locked --offline --project research --python "$(command -v python3)" python scripts/check_feature_parity.py --offline
~~~

The final --offline applies to Cargo. The uv environment has no package downloads in this phase. Initial installation of Python, Rust, uv and Cargo dependencies may need network access; these development checks are not a network sandbox.

## Acceptance and next phase

Local verification passed 66 Rust tests and 7 Python tests, 56 feature/context fixtures and two distance fixtures. Maximum absolute error across Rust, Python and golden values was 4.44e-16, below 1e-9. This is fixture evidence, not a detection metric.

The acceptance command includes all Rust regression tests, Python reference/gate tests, golden parity, format/lint checks, optimized build, source/link checks and staged-only smoke scans. [CI runs](https://github.com/richardwaters9049/Veil-Guard/actions/workflows/phase-one.yml) record macOS/Linux results for the exact commit; the historical workflow filename is retained while its displayed name is Acceptance checks.

This branch is stacked on accepted Phase One commit dc4723515043046b94a8daecba3a464be5af553d. Main has not been merged or released as part of this phase.

Next is [Phase Three](09-delivery-plan.md#phase-3-ethical-synthetic-corpus-and-split-manifest): an ethical synthetic corpus, labels and grouped split manifest. Ranking remains gated on later training and evaluation.
