//! Experimental exact KNN. Loading never executes model-supplied code.
//! Vectors and model contents deliberately have no Debug implementation.
use crate::features;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;

pub const MAX_MODEL_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_REFERENCES: usize = 10_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModelError {
    Unavailable,
    SizeLimit,
    InvalidBundle,
    InvalidQuery,
    NumericOverflow,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Reference {
    id: String,
    label: u8,
    vector: [f64; 8],
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Policy {
    review_all: bool,
    margin: f64,
    distance_limit: f64,
    selection_status: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Bundle {
    schema: String,
    feature_schema: String,
    feature_names: [String; 8],
    label_encoding: BTreeMap<String, String>,
    status: String,
    model_id: String,
    corpus_source_sha256: String,
    protocol_sha256: String,
    training_partition: String,
    k: usize,
    weights: String,
    mean: [f64; 8],
    scale: [f64; 8],
    raw_min: [f64; 8],
    raw_max: [f64; 8],
    policy: Policy,
    references: Vec<Reference>,
}

pub struct Model(Bundle);

/// Explicit inference output; never automatically attached to scanner reports.
#[derive(Serialize)]
pub struct Prediction<'a> {
    pub score: f64,
    pub nearest: f64,
    pub conflict: bool,
    pub outside: bool,
    pub zero_count: usize,
    pub prediction: Option<u8>,
    pub review_reason: Option<&'static str>,
    /// At most k neighbours. All exact matches vote even if omitted here.
    pub neighbours: Vec<Neighbour<'a>>,
}

#[derive(Serialize)]
pub struct Neighbour<'a> {
    pub id: &'a str,
    pub label: u8,
    pub distance: f64,
    /// Squared, standardised coordinate differences; not causal importance.
    pub contributions: [f64; 8],
}

fn safe_id(value: &str) -> bool {
    (1..=128).contains(&value.len())
        && value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-')
}
fn hash(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
fn finite(vector: &[f64; 8]) -> bool {
    vector.iter().all(|v| v.is_finite())
}

impl Model {
    /// Read at most the size ceiling plus one byte, including non-seekable input.
    pub fn from_reader(reader: impl Read) -> Result<Self, ModelError> {
        let mut bytes = Vec::new();
        reader
            .take((MAX_MODEL_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|_| ModelError::Unavailable)?;
        Self::from_json(&bytes)
    }

    pub fn from_json(bytes: &[u8]) -> Result<Self, ModelError> {
        if bytes.len() > MAX_MODEL_BYTES {
            return Err(ModelError::SizeLimit);
        }
        let b: Bundle = serde_json::from_slice(bytes).map_err(|_| ModelError::InvalidBundle)?;
        let expected_labels = BTreeMap::from([
            ("0".to_owned(), "benign_fixture".to_owned()),
            ("1".to_owned(), "sensitive_candidate".to_owned()),
        ]);
        let policy = &b.policy;
        if b.schema != "veilguard.knn-model.v1"
            || b.feature_schema != features::SCHEMA
            || b.feature_names
                .iter()
                .map(String::as_str)
                .ne(features::NAMES)
            || b.label_encoding != expected_labels
            || b.status != "experimental_research_only"
            || b.training_partition != "train"
            || !safe_id(&b.model_id)
            || !hash(&b.corpus_source_sha256)
            || !hash(&b.protocol_sha256)
            || !(1..=MAX_REFERENCES).contains(&b.references.len())
            || !(1..=b.references.len()).contains(&b.k)
            || !matches!(b.weights.as_str(), "uniform" | "inverse_distance")
            || !finite(&b.mean)
            || !finite(&b.scale)
            || !finite(&b.raw_min)
            || !finite(&b.raw_max)
            || b.scale.iter().any(|v| *v <= 0.0)
            || (0..8).any(|i| b.raw_min[i] > b.raw_max[i])
            || !policy.margin.is_finite()
            || !(0.0..=1.0).contains(&policy.margin)
            || !policy.distance_limit.is_finite()
            || policy.distance_limit < 0.0
            || !matches!(
                policy.selection_status.as_str(),
                "validation_selected" | "coverage_or_error_target_unmet" | "baseline_fixed"
            )
        {
            return Err(ModelError::InvalidBundle);
        }
        let mut ids = BTreeSet::new();
        for r in &b.references {
            if !safe_id(&r.id) || !ids.insert(&r.id) || r.label > 1 || !finite(&r.vector) {
                return Err(ModelError::InvalidBundle);
            }
        }
        Ok(Self(b))
    }

    pub fn model_id(&self) -> &str {
        &self.0.model_id
    }
    pub fn neighbour_count(&self) -> usize {
        self.0.k
    }
    pub fn reference_count(&self) -> usize {
        self.0.references.len()
    }

    pub fn predict(&self, query: &[f64; 8]) -> Result<Prediction<'_>, ModelError> {
        if !finite(query) {
            return Err(ModelError::InvalidQuery);
        }
        let b = &self.0;
        let z: [f64; 8] = std::array::from_fn(|i| (query[i] - b.mean[i]) / b.scale[i]);
        if !finite(&z) {
            return Err(ModelError::NumericOverflow);
        }
        let mut ordered = Vec::with_capacity(b.references.len());
        let mut zero_count = 0;
        let mut zero_positive = 0;
        for r in &b.references {
            let contributions: [f64; 8] = std::array::from_fn(|i| {
                let delta = r.vector[i] - z[i];
                delta * delta
            });
            // Preserve the Python reference's coordinate accumulation order.
            let squared = contributions.iter().fold(0.0, |sum, v| sum + v);
            if !squared.is_finite() {
                return Err(ModelError::NumericOverflow);
            }
            if squared == 0.0 {
                zero_count += 1;
                zero_positive += usize::from(r.label);
            }
            ordered.push(Neighbour {
                id: &r.id,
                label: r.label,
                distance: squared.sqrt(),
                contributions,
            });
        }
        ordered.sort_by(|a, b| {
            a.distance
                .total_cmp(&b.distance)
                .then_with(|| a.id.cmp(b.id))
        });
        ordered.truncate(b.k);
        let nearest = ordered[0].distance;
        let score = if zero_count > 0 {
            zero_positive as f64 / zero_count as f64
        } else {
            let mut numerator = 0.0;
            let mut denominator = 0.0;
            for n in &ordered {
                let weight = if b.weights == "uniform" {
                    1.0
                } else {
                    1.0 / n.distance
                };
                denominator += weight;
                if n.label == 1 {
                    numerator += weight;
                }
            }
            if !denominator.is_finite() || denominator <= 0.0 {
                return Err(ModelError::NumericOverflow);
            }
            numerator / denominator
        };
        if !score.is_finite() || !(0.0..=1.0).contains(&score) {
            return Err(ModelError::NumericOverflow);
        }
        let conflict = zero_positive > 0 && zero_positive < zero_count;
        let outside = (0..8).any(|i| query[i] < b.raw_min[i] || query[i] > b.raw_max[i]);
        let p = &b.policy;
        let review_reason = if p.review_all {
            Some("validation_policy_unmet")
        } else if conflict {
            Some("exact_match_conflict")
        } else if outside {
            Some("outside_training_support")
        } else if nearest > p.distance_limit {
            Some("nearest_distance_exceeded")
        } else if (2.0 * score - 1.0).abs() < p.margin {
            Some("low_vote_margin")
        } else {
            None
        };
        Ok(Prediction {
            score,
            nearest,
            conflict,
            outside,
            zero_count,
            prediction: review_reason.is_none().then_some(u8::from(score >= 0.5)),
            review_reason,
            neighbours: ordered,
        })
    }
}
