use git2::{IndexEntry, Repository, Signature};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use tempfile::TempDir;
use veilguard::{ScanLimits, scan};

struct Fixture {
    dir: TempDir,
    repo: Repository,
}

impl Fixture {
    fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let repo = Repository::init(dir.path()).unwrap();
        Self { dir, repo }
    }

    fn path(&self) -> &Path {
        self.dir.path()
    }

    fn stage(&self, path: impl AsRef<Path>, content: impl AsRef<[u8]>) {
        let path = path.as_ref();
        let file = self.path().join(path);
        fs::create_dir_all(file.parent().unwrap()).unwrap();
        fs::write(file, content).unwrap();
        let mut index = self.repo.index().unwrap();
        index.add_path(path).unwrap();
        index.write().unwrap();
    }

    fn commit(&self) {
        let mut index = self.repo.index().unwrap();
        let tree = self.repo.find_tree(index.write_tree().unwrap()).unwrap();
        let signature = Signature::now("Veil Guard fixture", "fixture@example.invalid").unwrap();
        let parent = self
            .repo
            .head()
            .ok()
            .map(|head| head.peel_to_commit().unwrap());
        let parents: Vec<_> = parent.iter().collect();
        self.repo
            .commit(
                Some("HEAD"),
                &signature,
                &signature,
                "safe fixture",
                &tree,
                &parents,
            )
            .unwrap();
    }

    fn run(&self, extra: &[&str]) -> Output {
        Command::new(env!("CARGO_BIN_EXE_veilguard"))
            .args(["scan", "--staged", "--repo"])
            .arg(self.path())
            .args(extra)
            .output()
            .unwrap()
    }

    fn report(&self) -> veilguard::Report {
        scan(self.path(), &ScanLimits::default()).unwrap()
    }
}

// Authored, unprovisioned format fixtures. Never sent to a provider.
fn fake_pat() -> String {
    format!("ghp_{}", "A".repeat(36))
}

#[test]
fn unborn_index_finds_pattern_and_redacts_both_formats() {
    let fixture = Fixture::new();
    let token = fake_pat();
    fixture.stage("config.txt", format!("access = \"{token}\"\n"));
    for format in ["text", "json"] {
        let output = fixture.run(&["--format", format]);
        assert_eq!(output.status.code(), Some(1));
        let stdout = String::from_utf8(output.stdout).unwrap();
        assert!(stdout.contains("github-pat-shape"));
        assert!(!stdout.contains(&token));
        assert!(output.stderr.is_empty());
    }
}

#[test]
fn staged_secret_is_found_when_worktree_was_cleaned() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    fs::write(fixture.path().join("config.txt"), "clean working copy\n").unwrap();
    let index_before = fs::read(fixture.repo.path().join("index")).unwrap();
    assert_eq!(fixture.report().exit_code(), 1);
    assert_eq!(
        index_before,
        fs::read(fixture.repo.path().join("index")).unwrap()
    );
    assert_eq!(
        fs::read_to_string(fixture.path().join("config.txt")).unwrap(),
        "clean working copy\n"
    );
}

#[test]
fn worktree_only_secret_is_never_scanned() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "plain = 'safe'\n");
    fs::write(fixture.path().join("config.txt"), fake_pat()).unwrap();
    assert!(fixture.report().findings.is_empty());
    assert_eq!(fixture.report().exit_code(), 0);
}

#[test]
fn staged_object_does_not_need_a_worktree_file() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    fs::remove_file(fixture.path().join("config.txt")).unwrap();
    assert_eq!(fixture.report().exit_code(), 1);
}

#[test]
fn unchanged_secret_line_is_not_repeated_in_a_modified_file() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", format!("{}\nunchanged\n", fake_pat()));
    fixture.commit();
    fixture.stage("config.txt", format!("{}\nnew benign line\n", fake_pat()));
    let report = fixture.report();
    assert_eq!(report.scanned_files, 1);
    assert!(report.findings.is_empty());
}

#[test]
fn clean_index_and_staged_deletion_are_complete() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    fixture.commit();
    assert!(fixture.report().findings.is_empty());
    let mut index = fixture.repo.index().unwrap();
    index.remove_path(Path::new("config.txt")).unwrap();
    index.write().unwrap();
    assert_eq!(fixture.report().exit_code(), 0);
    assert!(fixture.report().coverage_complete);
}

#[test]
fn rename_is_conservatively_treated_as_a_new_path() {
    let fixture = Fixture::new();
    fixture.stage("old.txt", fake_pat());
    fixture.commit();
    let mut index = fixture.repo.index().unwrap();
    index.remove_path(Path::new("old.txt")).unwrap();
    index.write().unwrap();
    fixture.stage("new name.txt", fake_pat());
    let report = fixture.report();
    assert_eq!(report.findings[0].path, "new name.txt");
    assert_eq!(report.exit_code(), 1);
}

#[test]
fn generic_sensitive_assignment_is_visible_but_does_not_block() {
    let fixture = Fixture::new();
    fixture.stage(
        "config.txt",
        "api_key = 'authored-fixture-only'\ntokenizer = 'short'\n",
    );
    let report = fixture.report();
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].rule_id, "sensitive-assignment");
    assert_eq!(report.exit_code(), 0);
    assert!(!report.text().contains("authored-fixture-only"));
    assert_eq!(report.model_status, "not_implemented");
}

#[test]
fn changed_private_key_body_is_flagged_even_with_old_header() {
    let fixture = Fixture::new();
    fixture.stage(
        "key.txt",
        "-----BEGIN PRIVATE KEY-----\nFAKE-LAB-BODY\n-----END PRIVATE KEY-----\n",
    );
    fixture.commit();
    fixture.stage(
        "key.txt",
        "-----BEGIN PRIVATE KEY-----\nUPDATED-FAKE-LAB-BODY\n-----END PRIVATE KEY-----\n",
    );
    let report = fixture.report();
    assert_eq!(report.exit_code(), 1);
    assert_eq!(report.findings[0].staged_line, 2);
    assert!(!report.text().contains("UPDATED-FAKE-LAB-BODY"));
}

#[test]
fn unterminated_private_key_marker_is_conservatively_blocked() {
    let fixture = Fixture::new();
    fixture.stage(
        "key.txt",
        "-----BEGIN OPENSSH PRIVATE KEY-----\nNOT-A-KEY\n",
    );
    assert_eq!(fixture.report().findings[0].rule_id, "private-key-marker");
    assert_eq!(fixture.report().exit_code(), 1);
}

#[test]
fn unsupported_blob_retains_findings_and_exit_two_takes_priority() {
    let fixture = Fixture::new();
    fixture.stage("a.txt", fake_pat());
    fixture.stage("z.bin", b"\x00fake-binary");
    let report = fixture.report();
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.exit_code(), 2);
    assert!(!report.coverage_complete);
    assert_eq!(report.issues[0].code, "binary_blob_unsupported");
}

#[test]
fn non_utf8_text_is_reported_as_incomplete() {
    let fixture = Fixture::new();
    fixture.stage("raw.txt", b"\xff\xfecontent");
    assert_eq!(fixture.report().issues[0].code, "non_utf8_blob_unsupported");
}

#[test]
fn limits_are_disclosed_and_do_not_clear_findings() {
    let fixture = Fixture::new();
    fixture.stage("a.txt", fake_pat());
    fixture.stage("z.txt", "x".repeat(200));
    let mut limits = ScanLimits {
        max_blob_bytes: 100,
        ..ScanLimits::default()
    };
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.code == "blob_limit_exceeded")
    );
    limits.max_blob_bytes = 1000;
    limits.max_total_bytes = 100;
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.code == "total_bytes_limit_exceeded")
    );
}

#[test]
fn finding_and_index_entry_limits_report_incompleteness() {
    let fixture = Fixture::new();
    fixture.stage("a.txt", "password = 'one'\nsecret = 'two'\n");
    fixture.stage("b.txt", "clean\n");
    let limits = ScanLimits {
        max_findings: 1,
        ..ScanLimits::default()
    };
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.exit_code(), 2);
    assert_eq!(report.issues[0].code, "finding_limit_exceeded");
    let limits = ScanLimits {
        max_index_entries: 1,
        ..ScanLimits::default()
    };
    assert_eq!(scan(fixture.path(), &limits).unwrap().exit_code(), 2);
}

#[test]
fn conflicted_index_is_refused_without_source_diagnostics() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    let mut index = fixture.repo.index().unwrap();
    let mut entry: IndexEntry = index.get_path(Path::new("config.txt"), 0).unwrap();
    index.clear().unwrap();
    entry.flags = (entry.flags & !0x3000) | 0x1000;
    index.add(&entry).unwrap();
    index.write().unwrap();
    assert!(index.has_conflicts());
    assert_eq!(
        scan(fixture.path(), &ScanLimits::default()).unwrap_err(),
        "index_conflicts"
    );
}

#[test]
fn missing_object_is_reported_without_leaking_object_or_source() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "safe\n");
    let index = fixture.repo.index().unwrap();
    let entry = index.get_path(Path::new("config.txt"), 0).unwrap();
    let object_id = entry.id.to_string();
    let object_file = fixture
        .repo
        .path()
        .join("objects")
        .join(&object_id[..2])
        .join(&object_id[2..]);
    fs::remove_file(object_file).unwrap();
    let report = fixture.report();
    assert_eq!(report.issues[0].code, "object_unavailable");
    assert!(!report.text().contains(&object_id));
}

#[test]
fn malicious_argument_values_are_not_echoed() {
    let fixture = Fixture::new();
    let token = fake_pat();
    let output = fixture.run(&["--unexpected", &token]);
    assert_eq!(output.status.code(), Some(2));
    assert!(!String::from_utf8(output.stderr).unwrap().contains(&token));
    assert!(output.stdout.is_empty());
}

#[test]
fn report_file_is_new_and_existing_paths_are_not_overwritten() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    let file = fixture.path().join("report.json");
    let output = fixture.run(&["--format", "json", "--output", file.to_str().unwrap()]);
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stdout.is_empty());
    let original = fs::read(&file).unwrap();
    let json: serde_json::Value = serde_json::from_slice(&original).unwrap();
    assert_eq!(json["scope"], "staged_index");
    assert!(
        !String::from_utf8(original.clone())
            .unwrap()
            .contains(&fake_pat())
    );
    let output = fixture.run(&["--format", "json", "--output", file.to_str().unwrap()]);
    assert_eq!(output.status.code(), Some(2));
    assert_eq!(fs::read(&file).unwrap(), original);
    assert!(!output.stdout.is_empty()); // Redacted report survives a failed file write.
}

#[test]
fn runtime_ignores_external_diff_filters_and_hooks() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", fake_pat());
    let script = fixture.path().join("must-not-run.sh");
    let marker = fixture.path().join("EXECUTED");
    fs::write(
        &script,
        format!("#!/bin/sh\ntouch '{}'\n", marker.display()),
    )
    .unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&script, fs::Permissions::from_mode(0o700)).unwrap();
        fs::copy(&script, fixture.repo.path().join("hooks/pre-commit")).unwrap();
    }
    let mut config = fixture.repo.config().unwrap();
    config
        .set_str("diff.external", script.to_str().unwrap())
        .unwrap();
    config
        .set_str("diff.evil.command", script.to_str().unwrap())
        .unwrap();
    config
        .set_str("filter.evil.clean", script.to_str().unwrap())
        .unwrap();
    fs::write(
        fixture.path().join(".gitattributes"),
        "*.txt diff=evil filter=evil\n",
    )
    .unwrap();
    assert_eq!(fixture.run(&[]).status.code(), Some(1));
    assert!(!marker.exists());
}

#[cfg(unix)]
#[test]
fn symlink_targets_are_not_followed_and_output_symlinks_are_refused() {
    use std::os::unix::fs::symlink;
    let fixture = Fixture::new();
    let external = tempfile::tempdir().unwrap();
    let target = external.path().join("outside.txt");
    fs::write(&target, fake_pat()).unwrap();
    symlink(&target, fixture.path().join("link")).unwrap();
    let mut index = fixture.repo.index().unwrap();
    index.add_path(Path::new("link")).unwrap();
    index.write().unwrap();
    let report = fixture.report();
    assert_eq!(report.issues[0].code, "symlink_not_followed");
    assert!(report.findings.is_empty());
    let output_link = fixture.path().join("output.json");
    symlink(&target, &output_link).unwrap();
    assert_eq!(
        fixture
            .run(&["--output", output_link.to_str().unwrap()])
            .status
            .code(),
        Some(2)
    );
    assert_eq!(fs::read_to_string(&target).unwrap(), fake_pat());
}

#[cfg(unix)]
#[test]
fn unusual_filenames_are_escaped_and_reports_are_private() {
    use std::os::unix::{ffi::OsStrExt, fs::PermissionsExt};
    let fixture = Fixture::new();
    let path = PathBuf::from(std::ffi::OsStr::from_bytes(b"line\n\x1b[31m-\xff.txt"));
    fixture.stage("seed.txt", fake_pat());
    let mut index = fixture.repo.index().unwrap();
    let mut entry = index.get_path(Path::new("seed.txt"), 0).unwrap();
    index.remove_path(Path::new("seed.txt")).unwrap();
    entry.path = path.as_os_str().as_bytes().to_vec();
    index.add(&entry).unwrap();
    index.write().unwrap();
    let report = fixture.report();
    assert!(!report.findings[0].path.contains('\n'));
    assert!(!report.findings[0].path.contains('\x1b'));
    assert!(report.findings[0].path.contains("\\x1b"));
    assert!(report.findings[0].path.contains("\\xff"));
    let file = fixture.path().join("report.json");
    fixture.run(&["--output", file.to_str().unwrap()]);
    assert_eq!(
        fs::metadata(file).unwrap().permissions().mode() & 0o777,
        0o600
    );
}

#[test]
fn changed_submodule_entry_is_explicitly_out_of_scope() {
    let fixture = Fixture::new();
    fixture.stage("module", "safe seed\n");
    fixture.commit();
    let commit_id = fixture.repo.head().unwrap().target().unwrap();
    let mut index = fixture.repo.index().unwrap();
    let mut entry = index.get_path(Path::new("module"), 0).unwrap();
    entry.mode = 0o160000;
    entry.id = commit_id;
    index.add(&entry).unwrap();
    index.write().unwrap();
    let report = fixture.report();
    assert_eq!(report.exit_code(), 2);
    assert_eq!(report.issues[0].code, "submodule_out_of_scope");
    assert!(report.findings.is_empty());
}

#[test]
fn byte_budget_counts_both_baseline_and_staged_blob() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "original\n");
    fixture.commit();
    fixture.stage("config.txt", "modified\n");
    assert_eq!(fixture.report().inspected_bytes, 18);
    let limits = ScanLimits {
        max_total_bytes: 12,
        ..ScanLimits::default()
    };
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.exit_code(), 2);
    assert_eq!(report.issues[0].code, "total_bytes_limit_exceeded");
}

#[test]
fn separate_quoted_values_on_one_line_keep_distinct_byte_spans() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "call(\"abcdefgh\", \"ijklmnop\")\n");
    let report = fixture.report();
    assert_eq!(report.candidates, 2);
    assert_eq!(report.feature_eligible_candidates, 2);
    assert_eq!(report.findings.len(), 2);
    assert_eq!(
        (
            report.findings[0].staged_column,
            report.findings[0].end_column
        ),
        (7, 15)
    );
    assert_eq!(
        (
            report.findings[1].staged_column,
            report.findings[1].end_column
        ),
        (19, 27)
    );
    assert_ne!(report.findings[0].id, report.findings[1].id);
    assert!(!report.text().contains("abcdefgh"));
}

#[test]
fn repeated_values_are_deduplicated_by_location_only() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "call(\"abcdefgh\", \"abcdefgh\")");
    let report = fixture.report();
    assert_eq!(report.candidates, 2);
    assert_eq!(report.findings.len(), 2);
    assert_ne!(report.findings[0].id, report.findings[1].id);
}

#[test]
fn quoted_assignment_keys_and_values_are_not_double_counted() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "\"privateKey\": \"abcdefgh\", # fixture\n");
    let report = fixture.report();
    assert_eq!(report.candidates, 1);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].rule_id, "sensitive-assignment");
    assert_eq!(
        report.findings[0].review_reason,
        Some("model_not_available")
    );
}

#[test]
fn crlf_and_spaces_inside_values_are_preserved_in_span_metadata() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "token = \" abcd ef \"\r\n");
    let report = fixture.report();
    assert_eq!(report.feature_eligible_candidates, 1);
    assert_eq!(report.findings[0].staged_column, 10);
    assert_eq!(report.findings[0].end_column, 19);
    assert_eq!(report.findings[0].end_line, 1);
}

#[test]
fn supported_unquoted_literals_keep_url_slashes_and_trailing_comments_out() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "endpoint=https://lab.invalid/x # fixture\n");
    let report = fixture.report();
    assert_eq!(report.candidates, 1);
    assert_eq!(report.feature_eligible_candidates, 1);
    assert_eq!(
        report.findings[0].end_column - report.findings[0].staged_column,
        21
    );
}

#[test]
fn comment_only_quoted_strings_are_not_generic_candidates() {
    let fixture = Fixture::new();
    fixture.stage("config.txt",
        "// ignored \"abcdefgh\"\n# ignored \"ijklmnop\"\ncall(\"qrstuvwx\") # \"comment-only-value\"\n");
    assert_eq!(fixture.report().candidates, 1);
    fixture.stage("config.txt", format!("# {}\n", fake_pat()));
    assert_eq!(fixture.report().exit_code(), 1); // Pattern rules do not ignore comments.
}

#[test]
fn unsupported_values_stay_visible_without_feature_eligibility() {
    let cases = [
        ("token = \"authored\\nfixture\"\n", "escaped_literal"),
        (
            "token = \"lab-é-fixture\"\n",
            "non_ascii_or_control_literal",
        ),
        (
            "token = \"abcdefgh\" + \"ijklmnop\"\n",
            "unsupported_expression",
        ),
        ("token = build(\"abcdefgh\")\n", "unsupported_expression"),
        ("token = \"abcdefgh\n", "unterminated_literal"),
        (
            "token = \"\"\"abcdefgh\"\"\"\n",
            "multiline_delimiter_unsupported",
        ),
        ("token = abc+defgh==\n", "unsupported_expression"),
    ];
    for (source, expected) in cases {
        let fixture = Fixture::new();
        fixture.stage("config.txt", source);
        let report = fixture.report();
        assert_eq!(report.candidates, 1);
        assert_eq!(report.feature_eligible_candidates, 0);
        assert_eq!(report.findings[0].review_reason, Some(expected));
        assert_eq!(report.findings[0].policy, "review");
        assert_eq!(report.exit_code(), 0);
    }
}

#[test]
fn generic_concatenation_is_review_only() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "use(\"abcdefgh\" + \"ijklmnop\")\n");
    let report = fixture.report();
    assert_eq!(report.candidates, 2);
    assert_eq!(report.feature_eligible_candidates, 0);
    assert!(
        report
            .findings
            .iter()
            .all(|f| f.review_reason == Some("unsupported_expression"))
    );
}

#[test]
fn sensitive_length_boundaries_are_explicit_and_not_imputed() {
    let fixture = Fixture::new();
    fixture.stage(
        "config.txt",
        format!(
            "password = '{}'\nsecret = '{}'\ntoken = '{}'\napi_key = '{}'\nprivate_key = ''\n",
            "a".repeat(7),
            "b".repeat(8),
            "c".repeat(256),
            "d".repeat(257)
        ),
    );
    let report = fixture.report();
    assert_eq!(report.candidates, 5);
    assert_eq!(report.feature_eligible_candidates, 2);
    assert_eq!(report.findings[0].review_reason, Some("short_literal"));
    assert_eq!(report.findings[3].review_reason, Some("long_literal"));
    assert_eq!(report.findings[4].review_reason, Some("short_literal"));
}

#[test]
fn candidate_budget_is_independent_and_does_not_hide_later_blocking_rules() {
    let fixture = Fixture::new();
    fixture.stage("a.txt", "call(\"abcdefgh\", \"ijklmnop\")");
    fixture.stage("z.txt", fake_pat());
    let limits = ScanLimits {
        max_candidates: 1,
        ..ScanLimits::default()
    };
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.candidates, 1);
    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.code == "candidate_limit_exceeded")
    );
    assert!(report.findings.iter().any(|f| f.policy == "block"));
}

#[test]
fn reviews_cannot_consume_the_slot_for_a_later_blocking_rule() {
    let fixture = Fixture::new();
    fixture.stage("a.txt", "token = 'abcdefgh'\n");
    fixture.stage("z.txt", fake_pat());
    let limits = ScanLimits {
        max_findings: 1,
        ..ScanLimits::default()
    };
    let report = scan(fixture.path(), &limits).unwrap();
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].policy, "block");
    assert_eq!(report.exit_code(), 2);
}

#[test]
fn two_pattern_matches_on_one_line_are_separate_occurrences() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", format!("{} {}", fake_pat(), fake_pat()));
    let report = fixture.report();
    assert_eq!(report.findings.len(), 2);
    assert_eq!(report.findings[0].staged_column, 1);
    assert_eq!(report.findings[1].staged_column, 42);
    assert_ne!(report.findings[0].id, report.findings[1].id);
}

#[test]
fn blocking_span_is_not_duplicated_as_an_unranked_generic_finding() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", format!("token = \"{}\"\n", fake_pat()));
    let report = fixture.report();
    assert_eq!(report.candidates, 1);
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].policy, "block");
}

#[test]
fn source_values_are_redacted_from_same_and_cross_file_report_paths() {
    let fixture = Fixture::new();
    fixture.stage("a-abcdefgh.txt", "token = 'ijklmnop'\n");
    fixture.stage("z-source.txt", "token = 'abcdefgh'\n");
    for format in ["text", "json"] {
        let output = fixture.run(&["--format", format]);
        assert_eq!(output.status.code(), Some(0));
        let rendered = String::from_utf8(output.stdout).unwrap();
        assert!(!rendered.contains("abcdefgh"));
        assert!(!rendered.contains("ijklmnop"));
    }
    assert_eq!(fixture.report().path_status, "redacted");
}

#[test]
fn recognised_pattern_is_redacted_from_a_filename_even_without_matching_source_value() {
    let fixture = Fixture::new();
    fixture.stage(format!("{}.txt", fake_pat()), "token = 'abcdefgh'\n");
    assert!(!fixture.report().text().contains(&fake_pat()));
}

#[test]
fn inner_literals_in_unsupported_expressions_are_redacted_from_paths() {
    let fixture = Fixture::new();
    fixture.stage("a-abcdefgh.txt", "token = build(\"abcdefgh\")\n");
    assert!(!fixture.report().text().contains("abcdefgh"));
}

#[test]
fn incomplete_scan_withholds_all_paths_but_retains_findings_and_issue_codes() {
    let fixture = Fixture::new();
    fixture.stage("a-unknown-sensitive-value.txt", fake_pat());
    fixture.stage("z.bin", b"\x00binary");
    let report = fixture.report();
    assert_eq!(report.path_status, "withheld");
    assert_eq!(report.findings.len(), 1);
    assert_eq!(report.findings[0].path, "[path withheld]");
    assert_eq!(report.issues[0].code, "binary_blob_unsupported");
    assert!(!report.text().contains("unknown-sensitive-value"));
}

#[test]
fn v2_report_and_example_have_the_same_contract_and_no_value_fields() {
    let fixture = Fixture::new();
    fixture.stage("config.txt", "token = 'abcdefgh'\n");
    let report = fixture.report();
    let json = serde_json::to_value(report).unwrap();
    let example: serde_json::Value =
        serde_json::from_str(include_str!("../examples/finding.example.json")).unwrap();
    assert_eq!(json["report_schema"], "veilguard.report.v2");
    assert_eq!(json["candidate_grammar"], "veilguard.candidates.v1");
    assert_eq!(
        json.as_object().unwrap().keys().collect::<Vec<_>>(),
        example.as_object().unwrap().keys().collect::<Vec<_>>()
    );
    assert_eq!(
        json["findings"][0]
            .as_object()
            .unwrap()
            .keys()
            .collect::<Vec<_>>(),
        example["findings"][0]
            .as_object()
            .unwrap()
            .keys()
            .collect::<Vec<_>>()
    );
    assert!(json["findings"][0].get("value").is_none());
    assert!(json["findings"][0].get("features").is_none());
}
