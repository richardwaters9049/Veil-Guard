#![cfg(unix)]

use git2::{Repository, Signature};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
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
    fn stage(&self, name: &str, value: &str) {
        let path = self.dir.path().join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(&path, value).unwrap();
        let mut index = self.repo.index().unwrap();
        index.add_path(Path::new(name)).unwrap();
        index.write().unwrap();
    }
    fn commit(&self) -> git2::Oid {
        let mut index = self.repo.index().unwrap();
        let tree = self.repo.find_tree(index.write_tree().unwrap()).unwrap();
        let signature = Signature::now("Fixture", "fixture@example.invalid").unwrap();
        self.repo
            .commit(Some("HEAD"), &signature, &signature, "fixture", &tree, &[])
            .unwrap()
    }
    fn append_config(&self, value: &str) {
        OpenOptions::new()
            .append(true)
            .open(self.repo.path().join("config"))
            .unwrap()
            .write_all(value.as_bytes())
            .unwrap();
    }
    fn cli(&self) -> Command {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_veilguard"));
        cmd.args(["scan", "--staged", "--repo"])
            .arg(self.dir.path());
        cmd
    }
}
fn token() -> String {
    format!("ghp_{}", "A".repeat(36))
}

fn git(path: &Path, args: &[&str]) -> Output {
    let mut command = Command::new("git");
    for (key, _) in
        std::env::vars_os().filter(|(key, _)| key.as_encoded_bytes().starts_with(b"GIT_"))
    {
        command.env_remove(key);
    }
    command
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_SYSTEM", "/dev/null");
    let output = command
        .args(["-c", "core.hooksPath=/dev/null", "-C"])
        .arg(path)
        .args(args)
        .output()
        .unwrap();
    assert!(output.status.success(), "Fixture Git command failed");
    output
}

#[test]
fn unsupported_layout_and_configuration_matrix_is_rejected() {
    let cases = [
        ("commondir", "repository_layout_unsupported"),
        ("gitdir", "repository_layout_unsupported"),
        ("shallow", "repository_layout_unsupported"),
        ("info/grafts", "repository_layout_unsupported"),
        ("config.worktree", "repository_layout_unsupported"),
        ("objects/info/alternates", "repository_layout_unsupported"),
        (
            "objects/info/http-alternates",
            "repository_layout_unsupported",
        ),
        ("split", "split_index_unsupported"),
        ("include", "repository_config_include_unsupported"),
        ("includeif", "repository_config_include_unsupported"),
        ("format", "repository_format_unsupported"),
        ("object-format", "repository_extension_unsupported"),
        ("extension", "repository_extension_unsupported"),
        ("redirect", "redirected_worktree_unsupported"),
        ("sparse", "sparse_index_unsupported"),
        ("promisor", "partial_clone_unsupported"),
        ("locked", "repository_update_in_progress"),
        ("bad-head", "head_invalid"),
        ("bad-index", "index_header_invalid"),
        ("future-index", "index_version_unsupported"),
        ("continued-config", "repository_config_unsupported"),
    ];
    for (case, expected) in cases {
        let f = Fixture::new();
        f.stage("config.txt", &token());
        let mut config = f.repo.config().unwrap();
        match case {
            "split" => fs::write(
                f.repo
                    .path()
                    .join(format!("sharedindex.{}", "a".repeat(40))),
                "",
            )
            .unwrap(),
            "include" => f.append_config("\n[InClude]\npath = /unread-fixture-path\n"),
            "includeif" => {
                f.append_config("\n[includeIf \"gitdir:*\"]\npath = /unread-fixture-path\n")
            }
            "format" => config.set_str("core.repositoryformatversion", "2").unwrap(),
            "object-format" => {
                config.set_str("core.repositoryformatversion", "1").unwrap();
                config.set_str("extensions.objectformat", "sha256").unwrap();
            }
            "extension" => config.set_str("extensions.unknown", "true").unwrap(),
            "redirect" => config
                .set_str("core.worktree", "/unread-fixture-path")
                .unwrap(),
            "sparse" => config.set_str("core.sparsecheckout", "true").unwrap(),
            "promisor" => config.set_str("remote.origin.promisor", "true").unwrap(),
            "locked" => fs::write(f.repo.path().join("index.lock"), "").unwrap(),
            "bad-head" => fs::write(f.repo.path().join("HEAD"), token()).unwrap(),
            "bad-index" => fs::write(f.repo.path().join("index"), b"invalid").unwrap(),
            "future-index" => {
                let path = f.repo.path().join("index");
                let mut bytes = fs::read(&path).unwrap();
                bytes[4..8].copy_from_slice(&5_u32.to_be_bytes());
                fs::write(path, bytes).unwrap();
            }
            "continued-config" => f.append_config("\n[user]\nname = continued\\\nvalue\n"),
            relative => {
                let path = f.repo.path().join(relative);
                fs::create_dir_all(path.parent().unwrap()).unwrap();
                fs::write(path, "").unwrap();
            }
        }
        let result = scan(f.dir.path(), &ScanLimits::default());
        assert_eq!(result.unwrap_err(), expected, "case {case}");
    }
}

#[test]
fn gitfiles_and_metadata_paths_are_not_followed() {
    let f = Fixture::new();
    let stored = f.dir.path().join("actual-metadata");
    fs::rename(f.repo.path(), &stored).unwrap();
    fs::write(
        f.dir.path().join(".git"),
        format!("gitdir: {}\n", stored.display()),
    )
    .unwrap();
    assert_eq!(
        scan(f.dir.path(), &ScanLimits::default()).unwrap_err(),
        "gitfile_layout_unsupported"
    );
    let f = Fixture::new();
    assert_eq!(
        scan(f.repo.path(), &ScanLimits::default()).unwrap_err(),
        "repository_metadata_path_unsupported"
    );
}

#[test]
fn metadata_symlinks_are_rejected_before_object_reads() {
    use std::os::unix::fs::symlink;
    for relative in [
        ".git",
        ".git/config",
        ".git/HEAD",
        ".git/index",
        ".git/objects",
        ".git/refs",
        ".git/objects/info",
        ".git/info",
    ] {
        let f = Fixture::new();
        f.stage("config.txt", &token());
        let path = f.dir.path().join(relative);
        let target = f.dir.path().join("fixture-saved-entry");
        if path.exists() {
            fs::rename(&path, &target).unwrap();
        } else {
            fs::create_dir_all(&target).unwrap();
        }
        symlink(&target, &path).unwrap();
        assert_eq!(
            scan(f.dir.path(), &ScanLimits::default()).unwrap_err(),
            "repository_metadata_symlink",
            "{relative}"
        );
    }
}

#[test]
fn symlinked_loose_objects_and_refs_are_rejected() {
    use std::os::unix::fs::symlink;
    for object in [true, false] {
        let f = Fixture::new();
        f.stage("config.txt", &token());
        let id = if object {
            f.repo
                .index()
                .unwrap()
                .get_path(Path::new("config.txt"), 0)
                .unwrap()
                .id
        } else {
            f.commit()
        };
        let hex = id.to_string();
        let path = if object {
            f.repo
                .path()
                .join("objects")
                .join(&hex[..2])
                .join(&hex[2..])
        } else {
            f.repo.path().join(f.repo.head().unwrap().name().unwrap())
        };
        let saved = f.dir.path().join("saved-entry");
        fs::rename(&path, &saved).unwrap();
        symlink(&saved, &path).unwrap();
        assert_eq!(
            scan(f.dir.path(), &ScanLimits::default()).unwrap_err(),
            "repository_metadata_symlink"
        );
    }
}

#[test]
fn bare_repositories_and_file_inputs_are_refused() {
    let dir = tempfile::tempdir().unwrap();
    Repository::init_bare(dir.path()).unwrap();
    assert_eq!(
        scan(dir.path(), &ScanLimits::default()).unwrap_err(),
        "bare_repository_unsupported"
    );
    let file = dir.path().join("input.txt");
    fs::write(&file, "fixture").unwrap();
    assert_eq!(
        scan(&file, &ScanLimits::default()).unwrap_err(),
        "repository_directory_required"
    );
}

#[test]
fn nested_discovery_and_git_environment_overrides_do_not_change_scope() {
    let f = Fixture::new();
    f.stage("config.txt", &token());
    let nested = f.dir.path().join("src/nested");
    fs::create_dir_all(&nested).unwrap();
    assert_eq!(
        scan(&nested, &ScanLimits::default()).unwrap().exit_code(),
        1
    );
    let mut cli = f.cli();
    for name in [
        "GIT_DIR",
        "GIT_COMMON_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
    ] {
        cli.env(name, "/unread-fixture-path");
    }
    cli.env("GIT_NAMESPACE", "unread-namespace");
    let output = cli.output().unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(!String::from_utf8(output.stdout).unwrap().contains(&token()));
}

#[test]
fn new_repository_without_an_index_is_not_modified() {
    let f = Fixture::new();
    assert!(!f.repo.path().join("index").exists());
    let report = scan(f.dir.path(), &ScanLimits::default()).unwrap();
    assert_eq!(report.exit_code(), 0);
    assert!(!f.repo.path().join("index").exists());
}

#[test]
fn packed_objects_packed_refs_detached_head_and_index_v4_are_supported() {
    let f = Fixture::new();
    f.stage("config.txt", "clean\n");
    let id = f.commit();
    git(f.dir.path(), &["repack", "-ad"]);
    git(f.dir.path(), &["pack-refs", "--all"]);
    f.repo.set_head_detached(id).unwrap();
    f.stage("config.txt", &token());
    let mut index = f.repo.index().unwrap();
    index.set_version(4).unwrap();
    index.write().unwrap();
    let header = fs::read(f.repo.path().join("index")).unwrap();
    assert_eq!(&header[4..8], &4_u32.to_be_bytes());
    assert_eq!(
        scan(f.dir.path(), &ScanLimits::default())
            .unwrap()
            .exit_code(),
        1
    );
}

#[test]
fn missing_detached_head_object_fails_instead_of_becoming_an_empty_baseline() {
    let f = Fixture::new();
    f.stage("config.txt", &token());
    fs::write(
        f.repo.path().join("HEAD"),
        format!("{}\n", "1234".repeat(10)),
    )
    .unwrap();
    let error = scan(f.dir.path(), &ScanLimits::default()).unwrap_err();
    assert!(["head_unavailable", "head_object_unavailable"].contains(&error));
    let output = f.cli().output().unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(
        !String::from_utf8(output.stderr)
            .unwrap()
            .contains(&"1234".repeat(10))
    );
}

#[test]
fn missing_nested_baseline_tree_retains_previous_findings_and_marks_incomplete() {
    let f = Fixture::new();
    f.stage("a.txt", "clean\n");
    f.stage("deep/file.txt", "old\n");
    f.commit();
    let commit = f.repo.head().unwrap().peel_to_commit().unwrap();
    let root = commit.tree().unwrap();
    let hex = root.get_name("deep").unwrap().id().to_string();
    f.stage("a.txt", &token());
    f.stage("deep/file.txt", "modified\n");
    fs::remove_file(
        f.repo
            .path()
            .join("objects")
            .join(&hex[..2])
            .join(&hex[2..]),
    )
    .unwrap();
    let report = scan(f.dir.path(), &ScanLimits::default()).unwrap();
    assert_eq!(report.exit_code(), 2);
    assert!(
        report
            .findings
            .iter()
            .any(|finding| finding.policy == "block")
    );
    assert!(
        report
            .issues
            .iter()
            .any(|issue| issue.code == "baseline_tree_unavailable")
    );
    assert_eq!(report.path_status, "withheld");
}

#[test]
fn oversized_index_metadata_is_refused_before_parsing() {
    let f = Fixture::new();
    OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(f.repo.path().join("index"))
        .unwrap()
        .set_len(17 * 1024 * 1024)
        .unwrap();
    assert_eq!(
        scan(f.dir.path(), &ScanLimits::default()).unwrap_err(),
        "repository_metadata_limit_exceeded"
    );
}

#[test]
fn special_object_entries_are_refused_without_blocking_on_a_fifo() {
    let f = Fixture::new();
    let output = Command::new("mkfifo")
        .arg(f.repo.path().join("objects/fifo-fixture"))
        .output()
        .unwrap();
    assert!(output.status.success());
    assert_eq!(
        scan(f.dir.path(), &ScanLimits::default()).unwrap_err(),
        "repository_metadata_type_unsupported"
    );
}

#[test]
fn missing_report_parent_falls_back_to_a_redacted_report() {
    let f = Fixture::new();
    f.stage("config.txt", &token());
    let output = f
        .cli()
        .args(["--format", "json", "--output"])
        .arg(f.dir.path().join("missing/report.json"))
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["findings"][0]["policy"], "block");
    assert!(!String::from_utf8(output.stdout).unwrap().contains(&token()));
}

#[test]
fn broken_stdout_returns_an_error_without_panic_or_source_details() {
    use std::os::fd::OwnedFd;
    use std::os::unix::net::UnixStream;
    use std::process::Stdio;
    let f = Fixture::new();
    f.stage("config.txt", &token());
    let (writer, reader) = UnixStream::pair().unwrap();
    drop(reader);
    let descriptor: OwnedFd = writer.into();
    let output = f.cli().stdout(Stdio::from(descriptor)).output().unwrap();
    assert_eq!(output.status.code(), Some(2));
    let error = String::from_utf8(output.stderr).unwrap();
    assert!(error.contains("report output failed"));
    assert!(!error.contains(&token()));
}

#[test]
fn extended_index_v3_entries_are_scanned_without_following_worktree_state() {
    let f = Fixture::new();
    f.stage("config.txt", &token());
    let mut index = f.repo.index().unwrap();
    let mut entry = index.get_path(Path::new("config.txt"), 0).unwrap();
    entry.flags |= 0x4000;
    entry.flags_extended = 0x4000;
    index.add(&entry).unwrap();
    index.set_version(3).unwrap();
    index.write().unwrap();
    let header = fs::read(f.repo.path().join("index")).unwrap();
    assert_eq!(&header[4..8], &3_u32.to_be_bytes());
    assert_eq!(
        scan(f.dir.path(), &ScanLimits::default())
            .unwrap()
            .exit_code(),
        1
    );
}

#[test]
fn configured_fsmonitor_command_is_not_executed() {
    use std::os::unix::fs::PermissionsExt;
    let f = Fixture::new();
    f.stage("config.txt", &token());
    let marker = f.dir.path().join("EXECUTED");
    let command = f.dir.path().join("fsmonitor-fixture");
    fs::write(
        &command,
        format!("#!/bin/sh\ntouch '{}'\n", marker.display()),
    )
    .unwrap();
    fs::set_permissions(&command, fs::Permissions::from_mode(0o700)).unwrap();
    f.repo
        .config()
        .unwrap()
        .set_str("core.fsmonitor", command.to_str().unwrap())
        .unwrap();
    let output = f.cli().output().unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(!marker.exists());
}
