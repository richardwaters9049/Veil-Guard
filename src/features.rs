//! Exactly eight coordinates; values and vectors are never included in scan reports.
use crate::candidates;
use std::collections::BTreeSet;
use std::ops::Range;

pub const SCHEMA: &str = "veilguard.features.v1";
pub const NAMES: [&str; 8] = [
    "log_length",
    "shannon_entropy",
    "digit_ratio",
    "uppercase_ratio",
    "symbol_ratio",
    "keyword_proximity",
    "sensitive_assignment",
    "placeholder_similarity",
];
pub const KEYWORDS: [&str; 7] = [
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "apikey",
    "privatekey",
];
pub const PLACEHOLDERS: [&str; 9] = [
    "changeme",
    "password",
    "example",
    "placeholder",
    "dummy",
    "test",
    "your_api_key_here",
    "replace_me",
    "not_a_real_secret",
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FeatureError {
    InvalidContext,
    UnsupportedLiteral,
    InvalidVector,
}

/// Deliberately has no Debug/Serialize implementation.
pub struct Features([f64; 8]);
impl Features {
    /// Explicit research/export access. Do not log vectors from private source.
    pub fn coordinates(&self) -> &[f64; 8] {
        &self.0
    }
}

pub(crate) fn keyword_spans(text: &str) -> Vec<Range<usize>> {
    let bytes = text.as_bytes();
    let mut tokens = Vec::new();
    let mut start = None;
    for (i, &b) in bytes.iter().enumerate() {
        if !b.is_ascii_alphanumeric() {
            if let Some(s) = start.take() {
                tokens.push(s..i);
            }
        } else {
            if b.is_ascii_uppercase()
                && i > 0
                && bytes[i - 1].is_ascii_lowercase()
                && let Some(s) = start.take()
            {
                tokens.push(s..i);
            }
            start.get_or_insert(i);
        }
    }
    if let Some(s) = start {
        tokens.push(s..bytes.len());
    }
    let mut matches = Vec::new();
    for token in &tokens {
        if token.len() <= 10
            && KEYWORDS.contains(&text[token.clone()].to_ascii_lowercase().as_str())
        {
            matches.push(token.clone());
        }
    }
    for pair in tokens.windows(2) {
        if pair[0].len() + pair[1].len() <= 10 {
            let joined = format!("{}{}", &text[pair[0].clone()], &text[pair[1].clone()]);
            if KEYWORDS.contains(&joined.to_ascii_lowercase().as_str()) {
                matches.push(pair[0].start..pair[1].end);
            }
        }
    }
    matches
}

fn context(line: &str, span: &Range<usize>) -> Result<(), FeatureError> {
    if line.len() > 1_048_576
        || line.contains(['\n', '\r'])
        || span.start >= span.end
        || line.get(span.clone()).is_none()
    {
        return Err(FeatureError::InvalidContext);
    }
    Ok(())
}

/// Span geometry helper; unlike from_line, this does not assert candidate syntax.
pub fn keyword_proximity(line: &str, span: Range<usize>) -> Result<f64, FeatureError> {
    context(line, &span)?;
    let nearest = keyword_spans(line)
        .into_iter()
        .filter_map(|keyword| {
            if keyword.end <= span.start {
                Some(span.start - keyword.end)
            } else if keyword.start >= span.end {
                Some(keyword.start - span.end)
            } else {
                None
            }
        })
        .min();
    Ok(nearest
        .filter(|&d| d <= 80)
        .map_or(0.0, |d| 1.0 / (1.0 + d as f64)))
}

fn edit_distance(left: &[u8], right: &[u8]) -> usize {
    let mut row: Vec<usize> = (0..=right.len()).collect();
    for (i, &a) in left.iter().enumerate() {
        let mut diagonal = row[0];
        row[0] = i + 1;
        for (j, &b) in right.iter().enumerate() {
            let old = row[j + 1];
            row[j + 1] = (row[j] + 1)
                .min(old + 1)
                .min(diagonal + usize::from(a != b));
            diagonal = old;
        }
    }
    row[right.len()]
}

/// A UTF-8 byte span excluding enclosing quotes on one physical source line.
/// Requires an exact, eligible occurrence under veilguard.candidates.v1.
pub fn from_line(line: &str, span: Range<usize>) -> Result<Features, FeatureError> {
    context(line, &span)?;
    let candidate = candidates::extract(line, &BTreeSet::from([1]), usize::MAX)
        .candidates
        .into_iter()
        .find(|c| c.span == span && c.reason == "model_not_available")
        .ok_or(FeatureError::UnsupportedLiteral)?;
    let value = &line[span.clone()];
    let length = value.len() as f64;
    let mut counts = [0_usize; 95];
    for b in value.bytes() {
        counts[usize::from(b - 0x20)] += 1;
    }
    let entropy = counts
        .into_iter()
        .filter(|&n| n > 0)
        .map(|n| {
            let p = n as f64 / length;
            -p * p.log2()
        })
        .sum::<f64>();
    let lower = value.to_ascii_lowercase();
    let similarity = PLACEHOLDERS
        .iter()
        .map(|p| {
            1.0 - edit_distance(lower.as_bytes(), p.as_bytes()) as f64
                / value.len().max(p.len()) as f64
        })
        .fold(0.0_f64, f64::max);
    let vector = [
        length.ln_1p(),
        entropy,
        value.bytes().filter(u8::is_ascii_digit).count() as f64 / length,
        value.bytes().filter(u8::is_ascii_uppercase).count() as f64 / length,
        value.bytes().filter(|b| !b.is_ascii_alphanumeric()).count() as f64 / length,
        keyword_proximity(line, span)?,
        f64::from(candidate.sensitive),
        similarity,
    ];
    let entropy_limit = (95_usize.min(value.len()) as f64).log2();
    if vector.iter().any(|n| !n.is_finite())
        || vector[0] < 9.0_f64.ln()
        || vector[0] > 257.0_f64.ln()
        || vector[1] < 0.0
        || vector[1] > entropy_limit + 1e-12
        || vector[2..].iter().any(|&n| !(0.0..=1.0).contains(&n))
    {
        return Err(FeatureError::InvalidVector);
    }
    Ok(Features(vector))
}

fn eight(values: &[f64]) -> Result<[f64; 8], FeatureError> {
    let vector: [f64; 8] = values.try_into().map_err(|_| FeatureError::InvalidVector)?;
    if vector.iter().any(|v| !v.is_finite()) {
        return Err(FeatureError::InvalidVector);
    }
    Ok(vector)
}

/// Apply an explicitly supplied scaler; this does not fit a model or scaler.
pub fn standardise(
    values: &[f64],
    means: &[f64],
    scales: &[f64],
) -> Result<[f64; 8], FeatureError> {
    let (values, means, scales) = (eight(values)?, eight(means)?, eight(scales)?);
    if scales.iter().any(|&v| v <= 0.0) {
        return Err(FeatureError::InvalidVector);
    }
    let result: [f64; 8] = std::array::from_fn(|i| (values[i] - means[i]) / scales[i]);
    eight(&result)
}

/// Each term sums to squared Euclidean distance in standardised coordinates.
pub fn squared_distance_contributions(
    left: &[f64],
    right: &[f64],
) -> Result<[f64; 8], FeatureError> {
    let (left, right) = (eight(left)?, eight(right)?);
    let result: [f64; 8] = std::array::from_fn(|i| (left[i] - right[i]).powi(2));
    let result = eight(&result)?;
    if !result.iter().sum::<f64>().is_finite() {
        return Err(FeatureError::InvalidVector);
    }
    Ok(result)
}
