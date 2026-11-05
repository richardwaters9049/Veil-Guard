//! Explain saved numeric evidence without reading source or echoing report strings.
use crate::report::ModelEvidence;
use serde::Serialize;
use serde_json::Value;
use std::fmt::Write;

pub const MAX_REPORT_BYTES: usize = 16 * 1024 * 1024;

#[derive(Serialize)]
pub struct Explanation {
    pub schema: &'static str,
    pub finding: usize,
    pub rule: &'static str,
    pub policy: &'static str,
    pub model_status: &'static str,
    pub review_reason: Option<&'static str>,
    pub model: Option<ModelEvidence>,
    pub note: &'static str,
}

fn allowed(value: &Value, choices: &[&'static str]) -> Result<&'static str, &'static str> {
    choices
        .iter()
        .copied()
        .find(|s| Some(*s) == value.as_str())
        .ok_or("invalid_report")
}
fn finding_number(id: &str) -> Result<usize, &'static str> {
    let digits = id.strip_prefix("finding-").ok_or("invalid_finding_id")?;
    if !(5..=8).contains(&digits.len()) || !digits.bytes().all(|c| c.is_ascii_digit()) {
        return Err("invalid_finding_id");
    }
    let number = digits.parse::<usize>().map_err(|_| "invalid_finding_id")?;
    if number == 0 || format!("finding-{number:05}") != id {
        return Err("invalid_finding_id");
    }
    Ok(number)
}

pub fn from_report(bytes: &[u8], id: &str) -> Result<Explanation, &'static str> {
    if bytes.len() > MAX_REPORT_BYTES {
        return Err("report_size_limit");
    }
    let finding = finding_number(id)?;
    let report: Value = serde_json::from_slice(bytes).map_err(|_| "invalid_report")?;
    if report["report_schema"] != "veilguard.report.v3" || report["scope"] != "staged_index" {
        return Err("unsupported_report");
    }
    let findings = report["findings"].as_array().ok_or("invalid_report")?;
    if findings.len() > 10_000 {
        return Err("report_finding_limit");
    }
    let matches: Vec<_> = findings
        .iter()
        .filter(|f| f["id"].as_str() == Some(id))
        .collect();
    if matches.len() != 1 {
        return Err("finding_not_unique_or_missing");
    }
    let f = matches[0];
    let rule = allowed(
        &f["rule_id"],
        &[
            "github-pat-shape",
            "private-key-marker",
            "sensitive-assignment",
            "generic-candidate",
        ],
    )?;
    let policy = allowed(&f["policy"], &["block", "review"])?;
    let model_status = allowed(
        &f["model_status"],
        &[
            "not_requested",
            "unavailable",
            "invalid",
            "not_applicable",
            "unsupported",
            "inference_failed",
            "ranked_experimental",
        ],
    )?;
    let review_reason = if f["review_reason"].is_null() {
        None
    } else {
        Some(allowed(
            &f["review_reason"],
            &[
                "model_not_available",
                "non_ascii_or_control_literal",
                "short_literal",
                "long_literal",
                "multiline_delimiter_unsupported",
                "multiline_or_template_unsupported",
                "unterminated_literal",
                "unsupported_expression",
                "escaped_literal",
                "validation_policy_unmet",
                "exact_match_conflict",
                "outside_training_support",
                "nearest_distance_exceeded",
                "low_vote_margin",
                "experimental_review_only",
                "inference_failed",
                "inference_budget_exceeded",
            ],
        )?)
    };
    let model = if f["model"].is_null() {
        None
    } else {
        if policy != "review" || model_status != "ranked_experimental" {
            return Err("invalid_report");
        }
        let evidence: ModelEvidence =
            serde_json::from_value(f["model"].clone()).map_err(|_| "invalid_evidence")?;
        validate(&evidence)?;
        Some(evidence)
    };
    if (model_status == "ranked_experimental") != model.is_some() {
        return Err("invalid_evidence");
    }
    if (policy == "block") != matches!(rule, "github-pat-shape" | "private-key-marker") {
        return Err("invalid_report");
    }
    Ok(Explanation {
        schema: "veilguard.explanation.v1",
        finding,
        rule,
        policy,
        model_status,
        review_reason,
        model,
        note: "Saved report evidence, not authenticated or recomputed. Values, paths and vectors withheld. At most five neighbours are retained; all exact matches vote, including unlisted ones. Uncalibrated research votes never certify safety or change rule policy.",
    })
}

fn validate(m: &ModelEvidence) -> Result<(), &'static str> {
    if !m.score.is_finite()
        || !(0.0..=1.0).contains(&m.score)
        || !m.nearest.is_finite()
        || m.nearest < 0.0
        || !(1..=10_000).contains(&m.rank)
        || m.zero_count > 10_000
        || (m.conflict && m.zero_count < 2)
    {
        return Err("invalid_evidence");
    }
    if let Some(neighbours) = &m.neighbours {
        if neighbours.is_empty() || neighbours.len() > 5 {
            return Err("invalid_evidence");
        }
        let mut references = std::collections::BTreeSet::new();
        let mut last = 0.0;
        for n in neighbours {
            if !(1..=10_000).contains(&n.reference)
                || !references.insert(n.reference)
                || n.label > 1
                || !n.distance.is_finite()
                || n.distance < last
                || n.contributions.iter().any(|v| !v.is_finite() || *v < 0.0)
            {
                return Err("invalid_evidence");
            }
            let sum: f64 = n.contributions.iter().sum();
            let square = n.distance * n.distance;
            if !sum.is_finite()
                || !square.is_finite()
                || (sum - square).abs() > 1e-9 * square.max(1.0)
            {
                return Err("invalid_evidence");
            }
            last = n.distance;
        }
        if neighbours[0].distance != m.nearest {
            return Err("invalid_evidence");
        }
    }
    Ok(())
}

impl Explanation {
    pub fn text(&self) -> String {
        let mut out = format!(
            "finding-{:05}: {} [{}]; AI: {} [REDACTED]\n",
            self.finding, self.rule, self.policy, self.model_status
        );
        if let Some(reason) = self.review_reason {
            let _ = writeln!(out, "Review reason: {reason}");
        }
        if let Some(m) = &self.model {
            let _ = writeln!(
                out,
                "Experimental vote: {:.6}; rank: {}; nearest distance: {:.6}; exact matches: {}; conflict: {}; outside training support: {}.",
                m.score, m.rank, m.nearest, m.zero_count, m.conflict, m.outside
            );
            if let Some(neighbours) = &m.neighbours {
                for n in neighbours {
                    let _ = writeln!(
                        out,
                        "reference-{:05}: label {}; distance {:.6}",
                        n.reference, n.label, n.distance
                    );
                    for (name, contribution) in crate::features::NAMES.iter().zip(n.contributions) {
                        let _ = writeln!(out, "  {name}: squared contribution {contribution:.6}");
                    }
                }
            } else {
                out.push_str("Neighbour details not retained; opt in with scan --explanations.\n");
            }
        }
        let _ = writeln!(out, "{}", self.note);
        out
    }
}
