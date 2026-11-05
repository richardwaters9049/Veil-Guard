use crate::candidates;
use crate::privacy::PathGuard;
use crate::report::{Finding, Report, escape_path};
use crate::rules;
use git2::{DiffOptions, ErrorCode, ObjectType, Patch, Repository};
use std::collections::BTreeSet;
use std::path::Path;
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
pub struct ScanLimits {
    pub max_blob_bytes: usize,
    pub max_total_bytes: usize,
    pub max_findings: usize,
    pub max_candidates: usize,
    pub max_index_entries: usize,
    pub deadline: Duration,
}

impl Default for ScanLimits {
    fn default() -> Self {
        Self {
            max_blob_bytes: 1024 * 1024,
            max_total_bytes: 20 * 1024 * 1024,
            max_findings: 10_000,
            max_candidates: 10_000,
            max_index_entries: 100_000,
            deadline: Duration::from_secs(10),
        }
    }
}

#[cfg(unix)]
fn object_path(bytes: &[u8]) -> std::path::PathBuf {
    use std::os::unix::ffi::OsStrExt;
    Path::new(std::ffi::OsStr::from_bytes(bytes)).to_path_buf()
}

#[cfg(not(unix))]
fn object_path(bytes: &[u8]) -> std::path::PathBuf {
    Path::new(&String::from_utf8_lossy(bytes).to_string()).to_path_buf()
}

fn blob_bytes(
    repo: &Repository,
    id: git2::Oid,
    report: &mut Report,
    limits: &ScanLimits,
) -> Result<Vec<u8>, &'static str> {
    let odb = repo.odb().map_err(|_| "object_database_unavailable")?;
    let (size, kind) = odb.read_header(id).map_err(|_| "object_unavailable")?;
    if kind != ObjectType::Blob {
        return Err("unexpected_object_type");
    }
    if size > limits.max_blob_bytes {
        return Err("blob_limit_exceeded");
    }
    if size
        > limits
            .max_total_bytes
            .saturating_sub(report.inspected_bytes)
    {
        return Err("total_bytes_limit_exceeded");
    }
    let blob = repo.find_blob(id).map_err(|_| "object_unavailable")?;
    report.inspected_bytes += size;
    Ok(blob.content().to_vec())
}

fn changed_lines(old: &[u8], new: &[u8]) -> Result<BTreeSet<u32>, &'static str> {
    let mut options = DiffOptions::new();
    options.force_text(true).context_lines(0);
    let patch = Patch::from_buffers(old, None, new, None, Some(&mut options))
        .map_err(|_| "in_memory_diff_failed")?;
    let mut changed = BTreeSet::new();
    for hunk in 0..patch.num_hunks() {
        let (_, count) = patch.hunk(hunk).map_err(|_| "diff_hunk_unavailable")?;
        for line in 0..count {
            let line = patch
                .line_in_hunk(hunk, line)
                .map_err(|_| "diff_line_unavailable")?;
            if line.origin() == '+'
                && let Some(number) = line.new_lineno()
            {
                changed.insert(number);
            }
        }
    }
    Ok(changed)
}

/// Reads object bytes only. The deadline is cooperative, not a per-library-call cap.
pub fn scan(path: &Path, limits: &ScanLimits) -> Result<Report, &'static str> {
    if !cfg!(unix) {
        return Err("platform_unsupported");
    }
    if limits.max_blob_bytes == 0
        || limits.max_total_bytes == 0
        || limits.max_findings == 0
        || limits.max_candidates == 0
        || limits.max_index_entries == 0
        || limits.deadline.is_zero()
    {
        return Err("invalid_scan_limits");
    }
    let start = Instant::now();
    let repo = Repository::discover(path).map_err(|_| "repository_unavailable")?;
    if repo.is_bare() {
        return Err("bare_repository_unsupported");
    }
    let index = repo.index().map_err(|_| "index_unavailable")?;
    if index.has_conflicts() {
        return Err("index_conflicts");
    }
    let head_tree = match repo.head() {
        Ok(head) => Some(head.peel_to_tree().map_err(|_| "head_tree_unavailable")?),
        Err(err) if matches!(err.code(), ErrorCode::UnbornBranch | ErrorCode::NotFound) => None,
        Err(_) => return Err("head_unavailable"),
    };
    let mut report = Report::default();
    let mut privacy = PathGuard::default();
    for (number, entry) in index.iter().enumerate() {
        if start.elapsed() >= limits.deadline {
            report.issue(None, "cooperative_deadline_exceeded");
            break;
        }
        if number >= limits.max_index_entries {
            report.issue(None, "index_entry_limit_exceeded");
            break;
        }
        let path = object_path(&entry.path);
        let previous = match head_tree.as_ref().map(|t| t.get_path(&path)) {
            Some(Ok(value)) => Some(value),
            Some(Err(err)) if err.code() == ErrorCode::NotFound => None,
            Some(Err(_)) => {
                report.issue(Some(escape_path(&entry.path)), "baseline_path_unavailable");
                continue;
            }
            None => None,
        };
        if previous
            .as_ref()
            .is_some_and(|p| p.id() == entry.id && p.filemode() as u32 == entry.mode)
        {
            continue;
        }
        let display = escape_path(&entry.path);
        if entry.path.len() > 4096 {
            report.issue(Some(display), "path_limit_exceeded");
            continue;
        }
        match entry.mode & 0o170000 {
            0o120000 => {
                report.issue(Some(display), "symlink_not_followed");
                continue;
            }
            0o160000 => {
                report.issue(Some(display), "submodule_out_of_scope");
                continue;
            }
            0o100000 => {}
            _ => {
                report.issue(Some(display), "unsupported_index_mode");
                continue;
            }
        }
        let new_bytes = match blob_bytes(&repo, entry.id, &mut report, limits) {
            Ok(value) => value,
            Err(code) => {
                report.issue(Some(display), code);
                continue;
            }
        };
        if new_bytes.contains(&0) {
            report.issue(Some(display), "binary_blob_unsupported");
            continue;
        }
        let text = match std::str::from_utf8(&new_bytes) {
            Ok(value) => value,
            Err(_) => {
                report.issue(Some(display), "non_utf8_blob_unsupported");
                continue;
            }
        };
        let old_bytes = if let Some(previous) = previous {
            if previous.kind() == Some(ObjectType::Blob) {
                match blob_bytes(&repo, previous.id(), &mut report, limits) {
                    Ok(value) => value,
                    Err(code) => {
                        report.issue(Some(display), code);
                        continue;
                    }
                }
            } else {
                Vec::new()
            }
        } else {
            Vec::new()
        };
        let changed = match changed_lines(&old_bytes, &new_bytes) {
            Ok(value) => value,
            Err(code) => {
                report.issue(Some(display), code);
                continue;
            }
        };
        let (blocking, rule_limit) = rules::detect(text, &changed, limits.max_findings);
        for rule in &blocking {
            // Retained transiently for cross-file path redaction, never serialised.
            for value in text[rule.span.clone()].lines() {
                privacy.remember(value.trim());
            }
            report.add_finding(
                Finding {
                    id: String::new(),
                    path: display.clone(),
                    staged_line: rule.line,
                    staged_column: rule.column,
                    end_line: rule.end_line,
                    end_column: rule.end_column,
                    rule_id: rule.rule,
                    severity: "high",
                    policy: "block",
                    model_status: "not_implemented",
                    review_reason: None,
                },
                limits.max_findings,
            );
        }
        if rule_limit {
            report.global_issue("finding_limit_exceeded");
        }
        let extraction = candidates::extract(
            text,
            &changed,
            limits.max_candidates.saturating_sub(report.candidates),
        );
        report.candidates += extraction.candidates.len();
        for candidate in extraction.candidates {
            privacy.remember_source(&text[candidate.span.clone()]);
            if candidate.reason == "model_not_available" {
                report.feature_eligible_candidates += 1;
            }
            if blocking
                .iter()
                .any(|r| r.span.start < candidate.span.end && candidate.span.start < r.span.end)
            {
                continue;
            }
            report.add_finding(
                Finding {
                    id: String::new(),
                    path: display.clone(),
                    staged_line: candidate.line,
                    staged_column: candidate.column,
                    end_line: candidate.line,
                    end_column: candidate.end_column,
                    rule_id: if candidate.sensitive {
                        "sensitive-assignment"
                    } else {
                        "generic-candidate"
                    },
                    severity: "review",
                    policy: "review",
                    model_status: "not_implemented",
                    review_reason: Some(candidate.reason),
                },
                limits.max_findings,
            );
        }
        if extraction.limit_hit {
            report.global_issue("candidate_limit_exceeded");
        }
        report.scanned_files += 1;
        if start.elapsed() >= limits.deadline {
            report.global_issue("cooperative_deadline_exceeded");
            break;
        }
    }
    report.findings.sort_by(|a, b| {
        (&a.path, a.staged_line, a.staged_column, a.rule_id).cmp(&(
            &b.path,
            b.staged_line,
            b.staged_column,
            b.rule_id,
        ))
    });
    for (index, finding) in report.findings.iter_mut().enumerate() {
        finding.id = format!("finding-{:05}", index + 1);
    }
    privacy.finish(&mut report);
    Ok(report)
}
