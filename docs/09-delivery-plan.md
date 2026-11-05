# Delivery plan

Estimate: 90–150 focused engineering hours, roughly 6–8 part-time weeks. Planning estimate only; revise after the first prototype. No calendar commitment or scheduled automation is created.

| Phase | Effort | Deliverable | Acceptance / dependency |
| --- | --- | --- | --- |
| 0 — planning baseline | This scaffold | Brief, contracts, ethics, research and roadmap | Plans consistent; no claim of implemented software |
| 1 — rule-only native scanner | 18–28 h | Cargo project, staged object reader, bounded extraction, redacted text/JSON | Exact-index and privacy integration tests; no model needed |
| 2 — 8D parity | 12–20 h | Rust and Python feature implementations, shared golden fixtures | Exact order/range agreement; unsupported inputs review |
| 3 — safe corpus | 15–25 h | Versioned fixture generator, data card, leakage-resistant split manifest | Provenance/labels reviewed; independent groups sufficient |
| 4 — KNN research | 15–25 h | Reference pipeline, baselines, validation, frozen test evaluation | Honest metrics/intervals; no test-driven tuning |
| 5 — native inference | 12–20 h | Strict JSON loader, f64 KNN, abstention/explanations | Python/Rust parity; corrupted-model and limits tests |
| 6 — integration and hardening | 12–20 h | Explicit hooks, packaging, performance and privacy verification | Existing hooks preserved; end-to-end flow correct |
| 7 — portfolio release | 6–12 h | Tagged release, demo, case study, completed cards/results | Reproducible offline run; measured claims only |

## Implementation order

**Why these gates.** Git semantics need implementation tests ([R17](13-sources.md#r17)); ML preprocessing needs isolation ([R11](13-sources.md#r11)); published models need documented intended use and limitations ([R16](13-sources.md#r16)). The phase order and hour estimates are our planning judgements, not numbers taken from those sources.

The first useful slice is the rule-only staged scanner. Do not begin with a UI, model training or a broad regex catalogue. Prove Git semantics and redaction first. Then settle the eight-feature contract with fixtures, collect data, research KNN, export it and integrate native inference.

## Milestone demonstrations

M1: A partially staged fixture shows that only index content is inspected.
M2: One supported candidate maps to exactly eight reproducible numbers in both languages.
M3: A frozen grouped experiment reports whether KNN helps.
M4: A packaged native binary explains a redacted finding with the Python environment absent.

## Go/no-go points

- If extraction misses too many supported cases, improve extraction before tuning KNN.
- If data groups are too few or labels unclear, do not publish accuracy claims.
- If KNN underperforms entropy/logistic regression, keep it experimental and report the result.
- If benchmark limits fail, reduce workload or optimise exact search based on profiling; document tradeoffs.
- Do not add model-based blocking, live provider checks, cloud inference or external training collection to meet a demo deadline.

## Backlog after a measured first release

Expanded syntax coverage with schema migration; narrow expiring suppressions; Linux packaging; reproducible signed model artefacts; independently authorised external evaluation. AST parsers, Windows, learned metrics and calibrated thresholds are later experiments, not MVP promises.

## Project workflow

Use small reviewable commits in Richard's preferred form, for example “Feat/Scanner: Read staged blobs without working-tree fallback”. Commit lockfiles when implementation begins. Document a behaviour change and its evidence in the relevant design document. The planning repository was subsequently published at [richardwaters9049/Veil-Guard](https://github.com/richardwaters9049/Veil-Guard). This is a documentation baseline, not a scanner/model release. Implementation and release gates remain outstanding.
