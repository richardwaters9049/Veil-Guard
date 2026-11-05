# Eight-dimensional feature contract

Schema: veilguard.features.v1. Exactly eight coordinates, fixed order. Implemented independently in Rust and Python; the [Phase Two record](18-phase-two-feature-parity.md) defines the fixture evidence and limits.

## Input and candidate boundaries

**Provenance.** Discrete entropy has an established mathematical definition ([R06](13-sources.md#r06)); insertion/deletion/substitution edit distance is established ([R07](13-sources.md#r07)). The eight-feature selection, context grammar, dictionaries, normalisation and limits below are our engineering choices. No cited thesis or professor has validated this exact representation.

For generic inference, v is a literal printable ASCII value of length L with 8 ≤ L ≤ 256. Strip only one recognised enclosing quote pair during candidate extraction. Do not trim, case-fold, decode escapes/base64, concatenate or Unicode-normalise v. Keep the original staged byte span for locating context. Unsupported inputs get review, never an imputed vector.

The implemented [candidate grammar](16-candidate-and-report-contract.md) extracts quoted single-line values and simple unquoted assignment values. It labels unsupported cases for review; language-specific escape handling remains future work behind a grammar/schema revision. Quotes with ambiguous escapes are review-only in v1. Duplicate spans are deduplicated by location, not value.

## Ordered vector

Let x = [x1, x2, x3, x4, x5, x6, x7, x8]^T in R^8.

| Index | Name | Definition | Raw range |
| --- | --- | --- | --- |
| 1 | log_length | ln(1 + L), natural logarithm | [ln 9, ln 257] |
| 2 | shannon_entropy | -Σ p(c) log2 p(c), over observed ASCII characters | [0, log2 min(95,L)] |
| 3 | digit_ratio | Count of characters 0–9 / L | [0,1] |
| 4 | uppercase_ratio | Count of characters A–Z / L | [0,1] |
| 5 | symbol_ratio | Count of printable characters outside A–Z, a–z and 0–9 / L | [0,1] |
| 6 | keyword_proximity | Nearest credential keyword outside v on the same staged line: 1/(1+d), if d ≤ 80; otherwise 0 | [0,1] |
| 7 | sensitive_assignment | 1 if v is the entire literal RHS of a supported assignment whose identifier contains a credential keyword; otherwise 0 | {0,1} |
| 8 | placeholder_similarity | max over dictionary P of 1 - Lev(lower(v),p)/max(L,len(p)) | [0,1] |

Spaces count as symbols if they occur inside v. Lowercase letters are deliberately not a ninth feature. Ratios are correlated with entropy/length; report ablation and correlation checks. Exactly eight dimensions are a design constraint, not a mathematical claim that eight is optimal.

## Precise context rules

Credential keyword vocabulary: password, passwd, secret, token, credential, apikey, privatekey.
Take maximal ASCII alphanumeric runs, splitting additionally between an ASCII lowercase letter and a following uppercase letter. Every non-ASCII-alphanumeric byte is a separator, including underscores, hyphens, periods, whitespace and punctuation. Case-fold tokens; uppercase runs are not split internally. Compare single tokens and concatenated adjacent token pairs, retaining the span from the first token start to the second token end, including intervening separators. Thus api_key and privateKey match apikey/privatekey; tokenizer is not token. The same tokenisation is used for assignment keys.

For proximity, tokenise the entire physical line, including other literals and comments, then discard keyword spans that overlap v. Do not clip a token at the value boundary or join across an overlapping value. Coordinates describe lexical context, without AST/semantic ownership.

For x6, find keyword spans outside the candidate span on the same physical line. d is the count of source bytes strictly between the end of the earlier span and start of the later span; adjacent spans give d=0. The nearest qualifying span wins. Newlines stop the search.

For x7, support simple full-line forms identifier = literal and identifier : literal with optional indentation, optional identifier quotes, optional terminal comma/semicolon and optional trailing comment outside the literal. The key may contain periods and underscores. Environment-style assignments are included. Nested expressions, calls, concatenation and multi-line strings yield x7=0 or unsupported review where extraction is ambiguous. The versioned candidate grammar and shared parity fixtures define the supported parser before training.

For x8, P is the literal dictionary:
changeme, password, example, placeholder, dummy, test, your_api_key_here, replace_me, not_a_real_secret.
Use ordinary character-level Levenshtein distance with insertion/deletion/substitution cost 1. This is similarity to a placeholder vocabulary, not proof that a value is harmless.

## Validity and missing data

Require finite values, correct ranges and exactly eight elements. Missing context where a valid single-line candidate exists sets x6/x7 to 0 by definition, not learned imputation. Invalid/unsupported parsing leads to unranked review. Do not silently add filename, repository, language or provider ID as extra model coordinates. Such metadata may be used to evaluate slices, not train this v1 model.

## Parity and explanation

Golden fixtures must cover repeated characters, every character class, quote boundaries, keyword distances 0/80/81, camel-case keys, no context, placeholders, unsupported escapes and Unicode. Exported f64 features must match within 1e-9 absolute tolerance.

For a chosen neighbour, report each dimension's squared standardised difference, labelled as a distance contribution. This follows directly from the Euclidean squared-norm expansion (linear algebra background: [R05](13-sources.md#r05)). These explain similarity, not causation or universal feature importance. Default output omits raw feature vectors because length/character statistics can reveal information about a candidate.
