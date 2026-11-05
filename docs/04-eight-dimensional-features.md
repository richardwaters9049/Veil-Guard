# Eight-dimensional feature contract

Schema: veilguard.features.v1. Exactly eight coordinates, fixed order. This is a proposed contract to implement identically in Rust and Python.

## Input and candidate boundaries

**Provenance.** Discrete entropy has an established mathematical definition ([R06](13-sources.md#r06)); insertion/deletion/substitution edit distance is established ([R07](13-sources.md#r07)). The eight-feature selection, context grammar, dictionaries, normalisation and limits below are our proposed engineering choices. No cited thesis or professor has validated this exact representation.

For generic inference, v is a literal printable ASCII value of length L with 8 ≤ L ≤ 256. Strip only one recognised enclosing quote pair during candidate extraction. Do not trim, case-fold, decode escapes/base64, concatenate or Unicode-normalise v. Keep the original staged byte span for locating context. Unsupported inputs get review, never an imputed vector.

Supported generic extraction begins with quoted single-line values and simple unquoted assignment values; implement language-specific escape handling later behind a schema change. Quotes with ambiguous escapes are review-only in v1. Duplicate spans are deduplicated by location, not value.

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
Tokenise ASCII identifiers by underscores, hyphens and camel-case boundaries; case-fold tokens. Also compare concatenated adjacent tokens so api_key and privateKey match apikey and privatekey. Do not use arbitrary substring matches (tokeniser is not token).

For x6, find keyword spans outside the candidate span on the same physical line. d is the count of source bytes strictly between the end of the earlier span and start of the later span; adjacent spans give d=0. The nearest qualifying span wins. Newlines stop the search.

For x7, support simple full-line forms identifier = literal and identifier : literal with optional indentation, optional identifier quotes, optional terminal comma/semicolon and optional trailing comment outside the literal. The key may contain periods and underscores. Environment-style assignments are included. Nested expressions, calls, concatenation and multi-line strings yield x7=0 or unsupported review where extraction is ambiguous. Version and test the exact parser grammar before training.

For x8, P is the literal dictionary:
changeme, password, example, placeholder, dummy, test, your_api_key_here, replace_me, not_a_real_secret.
Use ordinary character-level Levenshtein distance with insertion/deletion/substitution cost 1. This is similarity to a placeholder vocabulary, not proof that a value is harmless.

## Validity and missing data

Require finite values, correct ranges and exactly eight elements. Missing context where a valid single-line candidate exists sets x6/x7 to 0 by definition, not learned imputation. Invalid/unsupported parsing leads to unranked review. Do not silently add filename, repository, language or provider ID as extra model coordinates. Such metadata may be used to evaluate slices, not train this v1 model.

## Parity and explanation

Golden fixtures must cover repeated characters, every character class, quote boundaries, keyword distances 0/80/81, camel-case keys, no context, placeholders, unsupported escapes and Unicode. Exported f64 features must match within 1e-9 absolute tolerance.

For a chosen neighbour, report each dimension's squared standardised difference, labelled as a distance contribution. This follows directly from the Euclidean squared-norm expansion (linear algebra background: [R05](13-sources.md#r05)). These explain similarity, not causation or universal feature importance. Default output omits raw feature vectors because length/character statistics can reveal information about a candidate.
