use serde::Serialize;
use std::fmt::Write as _;

#[derive(Debug, Serialize)]
pub struct Finding {
    pub id: String,
    pub path: String,
    pub staged_line: u32,
    pub rule_id: &'static str,
    pub severity: &'static str,
    pub policy: &'static str,
    pub model_status: &'static str,
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
    pub model_status: &'static str,
    pub coverage_complete: bool,
    pub scanned_files: usize,
    pub inspected_bytes: usize,
    pub findings: Vec<Finding>,
    pub issues: Vec<Issue>,
}

impl Default for Report {
    fn default() -> Self {
        Self {
            report_schema: "veilguard.report.v1",
            scope: "staged_index",
            scanner_version: env!("CARGO_PKG_VERSION"),
            model_status: "not_implemented",
            coverage_complete: true,
            scanned_files: 0,
            inspected_bytes: 0,
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
                "{}:{} [{}] {} ({}) [REDACTED]",
                f.path, f.staged_line, f.policy, f.rule_id, f.id
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
            "Coverage: {}; files: {}; inspected bytes: {}; findings: {}.",
            if self.coverage_complete {
                "complete within declared scope"
            } else {
                "incomplete"
            },
            self.scanned_files,
            self.inspected_bytes,
            self.findings.len()
        );
        out.push_str("Exit 0 does not certify that a repository contains no secrets.\n");
        out
    }
}

/// Preserve ASCII paths while escaping terminal controls, non-ASCII and invalid UTF-8.
/// A path is still potentially sensitive metadata; reports are not anonymised.
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
