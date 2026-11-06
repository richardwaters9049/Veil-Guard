use git2::Repository;
use std::fs;
use std::path::Path;
use std::process::{Command, Output};
use tempfile::TempDir;

struct Fixture {
    dir: TempDir,
    home: TempDir,
    repo: Repository,
}
impl Fixture {
    fn new() -> Self {
        let dir = tempfile::tempdir().unwrap();
        let home = tempfile::tempdir().unwrap();
        let repo = Repository::init(dir.path()).unwrap();
        Self { dir, home, repo }
    }
    fn command(&self, binary: &Path) -> Command {
        let mut command = Command::new(binary);
        for (key, _) in
            std::env::vars_os().filter(|(key, _)| key.as_encoded_bytes().starts_with(b"GIT_"))
        {
            command.env_remove(key);
        }
        // Child-only config isolation; never edit the user's Git configuration.
        command
            .env("HOME", self.home.path())
            .env("XDG_CONFIG_HOME", self.home.path().join("xdg"));
        command
    }
    fn hook(&self, operation: &str) -> Output {
        self.command(Path::new(env!("CARGO_BIN_EXE_veilguard")))
            .args(["hooks", operation, "--repo"])
            .arg(self.dir.path())
            .output()
            .unwrap()
    }
    fn stage(&self, text: &str) {
        fs::write(self.dir.path().join("fixture.txt"), text).unwrap();
        let mut index = self.repo.index().unwrap();
        index.add_path(Path::new("fixture.txt")).unwrap();
        index.write().unwrap();
    }
    fn git(&self, args: &[&str]) -> Output {
        self.command(Path::new("git"))
            .env("GIT_CONFIG_NOSYSTEM", "1")
            .args(["-C"])
            .arg(self.dir.path())
            .args([
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
            ])
            .args(args)
            .output()
            .unwrap()
    }
    fn path(&self, name: &str) -> std::path::PathBuf {
        self.repo.path().join("hooks").join(name)
    }
}

#[test]
fn explicit_install_is_executable_tracks_ownership_and_uninstalls_without_source_or_index_changes()
{
    let f = Fixture::new();
    f.stage("token = 'authored-generic-review'\n");
    let index = fs::read(f.repo.path().join("index")).unwrap();
    let config = fs::read(f.repo.path().join("config")).unwrap();
    let source = fs::read(f.dir.path().join("fixture.txt")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(0));
    assert!(
        fs::read_to_string(f.path("pre-commit"))
            .unwrap()
            .contains("scan --staged --repo .")
    );
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(
            fs::metadata(f.path("pre-commit"))
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(f.path(".veilguard-pre-commit.json"))
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert_eq!(f.hook("uninstall").status.code(), Some(0));
    assert!(!f.path("pre-commit").exists());
    assert!(!f.path(".veilguard-pre-commit.json").exists());
    assert_eq!(f.hook("uninstall").status.code(), Some(0));
    assert_eq!(fs::read(f.repo.path().join("index")).unwrap(), index);
    assert_eq!(fs::read(f.repo.path().join("config")).unwrap(), config);
    assert_eq!(fs::read(f.dir.path().join("fixture.txt")).unwrap(), source);
}

#[test]
fn existing_modified_or_unowned_hooks_and_records_are_preserved() {
    let f = Fixture::new();
    fs::write(f.path("pre-commit"), "#!/bin/sh\n# user's existing hook\n").unwrap();
    let before = fs::read(f.path("pre-commit")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert_eq!(f.hook("uninstall").status.code(), Some(2));
    assert_eq!(fs::read(f.path("pre-commit")).unwrap(), before);
    fs::remove_file(f.path("pre-commit")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(0));
    let mut modified = fs::read(f.path("pre-commit")).unwrap();
    modified.extend_from_slice(b"# user edit\n");
    fs::write(f.path("pre-commit"), &modified).unwrap();
    assert_eq!(f.hook("uninstall").status.code(), Some(2));
    assert_eq!(fs::read(f.path("pre-commit")).unwrap(), modified);
    assert!(f.path(".veilguard-pre-commit.json").exists());
}

#[test]
fn configured_hooks_paths_environment_overrides_and_management_locks_are_refused() {
    let f = Fixture::new();
    f.repo
        .config()
        .unwrap()
        .set_str("core.hooksPath", "custom-hook-manager")
        .unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert!(!f.path("pre-commit").exists());
    f.repo.config().unwrap().remove("core.hooksPath").unwrap();
    fs::write(
        f.home.path().join(".gitconfig"),
        "[core]\n hooksPath = ~/custom-hooks\n",
    )
    .unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    fs::write(
        f.home.path().join(".gitconfig"),
        "[includeIf \"gitdir:/nonmatching-safe-fixture/\"]\n path = /nonexistent-safe-fixture\n",
    )
    .unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    fs::remove_file(f.home.path().join(".gitconfig")).unwrap();
    let output = f
        .command(Path::new(env!("CARGO_BIN_EXE_veilguard")))
        .env("GIT_INDEX_FILE", "private-path-sentinel")
        .args(["hooks", "install", "--repo"])
        .arg(f.dir.path())
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(!String::from_utf8_lossy(&output.stderr).contains("private-path-sentinel"));
    fs::write(f.path(".veilguard-hooks.lock"), "existing lock").unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert_eq!(
        fs::read_to_string(f.path(".veilguard-hooks.lock")).unwrap(),
        "existing lock"
    );
}

#[test]
fn actual_git_commit_runs_rule_only_hook_and_stops_staged_pattern_even_if_worktree_is_clean() {
    let f = Fixture::new();
    assert_eq!(f.hook("install").status.code(), Some(0));
    f.stage("plain = short\n");
    let clean = f.git(&["commit", "-m", "safe fixture"]);
    assert!(clean.status.success(), "clean fixture commit must pass");
    let token = format!("ghp_{}", "A".repeat(36));
    f.stage(&format!("token = '{token}'\n"));
    fs::write(f.dir.path().join("fixture.txt"), "clean worktree\n").unwrap();
    let blocked = f.git(&["commit", "-m", "blocked fixture"]);
    assert!(!blocked.status.success());
    let output = String::from_utf8([blocked.stdout, blocked.stderr].concat()).unwrap();
    assert!(output.contains("github-pat-shape"));
    assert!(!output.contains(&token));
}

#[test]
fn alternate_indexes_are_refused_and_missing_binary_fails_closed_without_path_leak() {
    let f = Fixture::new();
    f.stage("plain = short\n");
    assert_eq!(f.hook("install").status.code(), Some(0));
    let output = f
        .command(&f.path("pre-commit"))
        .current_dir(f.dir.path())
        .env("GIT_INDEX_FILE", "private-index-sentinel")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(!String::from_utf8_lossy(&output.stderr).contains("private-index-sentinel"));
    // Installation records the executable used, including shell-sensitive path bytes.
    let bin = f.home.path().join("quoted ' binary");
    fs::copy(env!("CARGO_BIN_EXE_veilguard"), &bin).unwrap();
    assert_eq!(f.hook("uninstall").status.code(), Some(0));
    let output = f
        .command(&bin)
        .args(["hooks", "install", "--repo"])
        .arg(f.dir.path())
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(0));
    let commit = f.git(&["commit", "-m", "quoted binary fixture"]);
    assert!(commit.status.success());
    fs::remove_file(&bin).unwrap();
    let output = f
        .command(&f.path("pre-commit"))
        .current_dir(f.dir.path())
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(!String::from_utf8_lossy(&output.stderr).contains("quoted ' binary"));
    assert_eq!(f.hook("uninstall").status.code(), Some(0));
}

#[cfg(unix)]
#[test]
fn symlinked_hooks_directories_files_and_records_are_never_followed() {
    use std::os::unix::fs::symlink;
    let f = Fixture::new();
    let outside = tempfile::tempdir().unwrap();
    fs::remove_dir_all(f.repo.path().join("hooks")).unwrap();
    symlink(outside.path(), f.repo.path().join("hooks")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert_eq!(fs::read_dir(outside.path()).unwrap().count(), 0);
    fs::remove_file(f.repo.path().join("hooks")).unwrap();
    fs::create_dir(f.repo.path().join("hooks")).unwrap();
    let target = outside.path().join("private");
    fs::write(&target, "do not overwrite").unwrap();
    symlink(&target, f.path("pre-commit")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(2));
    assert_eq!(f.hook("uninstall").status.code(), Some(2));
    assert_eq!(fs::read_to_string(&target).unwrap(), "do not overwrite");
    fs::remove_file(f.path("pre-commit")).unwrap();
    assert_eq!(f.hook("install").status.code(), Some(0));
    fs::remove_file(f.path(".veilguard-pre-commit.json")).unwrap();
    symlink(&target, f.path(".veilguard-pre-commit.json")).unwrap();
    assert_eq!(f.hook("uninstall").status.code(), Some(2));
    assert!(f.path("pre-commit").exists());
}
