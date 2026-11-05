use crate::candidates;
use serde::Serialize;
use std::fmt::Write as _;

#[derive(Debug, Serialize)]
pub struct Finding {
    pub id: String,
    pub path: String,
    pub staged_line: u32,
    pub staged_column: u32,
    pub end_line: u32,
    pub end_column: u32,
    pub rule_id: &'static str,
    pub severity: &'static str,
    pub policy: &'static str,
    pub model_status: &'static str,
    pub review_reason: Option<&'static str>,
}

#[derive(Debug, Serialize)]
pub struct Issue {
    pub path: Option<String>,
    pub code: &'static str,
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub report_schema: &'static str,
    pub scope: &'static str,
    pub scanner_version: &'static str,
    pub candidate_grammar: &'static str,
    pub model_status: &'static str,
    pub path_status: &'static str,
    pub coverage_complete: bool,
    pub scanned_files: usize,
    pub inspected_bytes: usize,
    pub candidates: usize,
    pub feature_eligible_candidates: usize,
    pub findings: Vec<Finding>,
    pub issues: Vec<Issue>,
}

impl Default for Report {
    fn default() -> Self {
        Self {
            report_schema: "veilguard.report.v2",
            scope: "staged_index",
            scanner_version: env!("CARGO_PKG_VERSION"),
            candidate_grammar: candidates::GRAMMAR,
            model_status: "not_implemented",
            path_status: "escaped",
            coverage_complete: true,
            scanned_files: 0,
            inspected_bytes: 0,
            candidates: 0,
            feature_eligible_candidates: 0,
            findings: Vec::new(),
            issues: Vec::new(),
        }
    }
}

impl Report {
    pub fn issue(&mut self, path: Option<String>, code: &'static str) {
        self.coverage_complete = false;
        self.issues.push(Issue { path, code });
    }

    pub(crate) fn global_issue(&mut self, code: &'static str) {
        if !self.issues.iter().any(|issue| issue.code == code) {
            self.issue(None, code);
        }
    }

    pub(crate) fn add_finding(&mut self, finding: Finding, cap: usize) {
        if self.findings.len() == cap {
            self.global_issue("finding_limit_exceeded");
            // A review must not consume the last slot needed by a later rule warning.
            if finding.policy == "block"
                && let Some(index) = self.findings.iter().rposition(|f| f.policy == "review")
            {
                self.findings.remove(index);
            } else {
                return;
            }
        }
        self.findings.push(finding);
    }

    pub fn exit_code(&self) -> u8 {
        if !self.coverage_complete {
            2
        } else if self.findings.iter().any(|f| f.policy == "block") {
            1
        } else {
            0
        }
    }

    pub fn text(&self) -> String {
        let mut out = String::from("Veil Guard — staged scan (rule-only; AI unavailable)\n");
        for f in &self.findings {
            let _ = writeln!(
                out,
                "{}:{}:{} [{}] {} ({}) [REDACTED]{}",
                f.path,
                f.staged_line,
                f.staged_column,
                f.policy,
                f.rule_id,
                f.id,
                f.review_reason
                    .map(|r| format!(" [{r}]"))
                    .unwrap_or_default()
            );
        }
        for issue in &self.issues {
            let _ = writeln!(
                out,
                "INCOMPLETE: {} [{}]",
                issue.path.as_deref().unwrap_or("scan"),
                issue.code
            );
        }
        let _ = writeln!(
            out,
            "Coverage: {}; files: {}; inspected bytes: {}; candidates: {}; feature-eligible: {}; findings: {}; paths: {}.",
            if self.coverage_complete {
                "complete within declared scope"
            } else {
                "incomplete"
            },
            self.scanned_files,
            self.inspected_bytes,
            self.candidates,
            self.feature_eligible_candidates,
            self.findings.len(),
            self.path_status
        );
        out.push_str("Exit 0 does not certify that a repository contains no secrets.\n");
        out
    }
}

pub fn escape_path(bytes: &[u8]) -> String {
    let mut out = String::new();
    for &byte in bytes.iter().take(4096) {
        match byte {
            b' '..=b'~' if byte != b'\\' => out.push(byte as char),
            b'\\' => out.push_str("\\\\"),
            _ => {
                let _ = write!(out, "\\x{byte:02x}");
            }
        }
    }
    if bytes.len() > 4096 {
        out.push_str("[path truncated]");
    }
    out
}
