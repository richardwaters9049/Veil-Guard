//! Bounded, transient path redaction. This is not anonymisation or secure erasure.
use crate::report::{Report, escape_path};
use crate::rules;
use aho_corasick::{AhoCorasickBuilder, MatchKind};
use std::collections::BTreeSet;

const PATTERN_BYTES: usize = 4 * 1024 * 1024;

#[derive(Default)]
pub(crate) struct PathGuard {
    values: BTreeSet<String>,
    bytes: usize,
    exhausted: bool,
}

impl PathGuard {
    pub fn remember(&mut self, value: &str) {
        if self.exhausted || value.is_empty() || value.len() > 4096 {
            return;
        }
        let escaped = escape_path(value.as_bytes());
        if self.values.contains(&escaped) {
            return;
        }
        if escaped.len() > PATTERN_BYTES.saturating_sub(self.bytes) {
            self.exhausted = true;
            self.values.clear();
            return;
        }
        self.bytes += escaped.len();
        self.values.insert(escaped);
    }

    pub fn remember_source(&mut self, value: &str) {
        self.remember(value);
        // Protect inner quoted components even when an expression is review-only.
        for segment in value.split(['\'', '"']) {
            self.remember(segment);
        }
    }

    pub fn finish(self, report: &mut Report) {
        if self.exhausted {
            report.issue(None, "path_redaction_budget_exceeded");
        }
        if !report.coverage_complete {
            withhold(report);
            return;
        }
        if self.values.is_empty() {
            for finding in &mut report.findings {
                let safe = rules::redact_path_patterns(&finding.path);
                if safe != finding.path {
                    report.path_status = "redacted";
                }
                finding.path = safe;
            }
            return;
        }
        let matcher = match AhoCorasickBuilder::new()
            .match_kind(MatchKind::LeftmostLongest)
            .build(&self.values)
        {
            Ok(matcher) => matcher,
            Err(_) => {
                report.issue(None, "path_redaction_unavailable");
                withhold(report);
                return;
            }
        };
        let replacements = vec!["[REDACTED]"; self.values.len()];
        for finding in &mut report.findings {
            let safe = matcher.replace_all(&finding.path, &replacements);
            let safe = rules::redact_path_patterns(&safe);
            if safe != finding.path {
                report.path_status = "redacted";
            }
            finding.path = safe;
        }
    }
}

fn withhold(report: &mut Report) {
    report.path_status = "withheld";
    for finding in &mut report.findings {
        finding.path = "[path withheld]".to_string();
    }
    for issue in &mut report.issues {
        if issue.path.is_some() {
            issue.path = Some("[path withheld]".to_string());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exhausted_redaction_budget_withholds_paths_and_marks_incomplete() {
        let mut guard = PathGuard::default();
        for index in 0..=1024 {
            guard.remember(&format!("{index:08}{}", "x".repeat(4088)));
        }
        let mut report = Report::default();
        guard.finish(&mut report);
        assert!(!report.coverage_complete);
        assert_eq!(report.path_status, "withheld");
        assert_eq!(report.issues[0].code, "path_redaction_budget_exceeded");
    }
}
