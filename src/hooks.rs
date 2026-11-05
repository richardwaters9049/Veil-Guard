//! Explicit hook management only. Scanning never calls this module.
use crate::{local_input, repository};
use serde::{Deserialize, Serialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

const RECORD: &str = ".veilguard-pre-commit.json";
const LOCK: &str = ".veilguard-hooks.lock";
const LIMIT: usize = 16 * 1024;

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record {
    schema: String,
    executable: String,
}

pub const MANUAL: &str = r#"Manual integration: preserve your existing hook manager and its checks.
Add a call to your trusted absolute Veil Guard binary, and propagate failure:

case "${GIT_INDEX_FILE:-}" in
  ''|.git/index|"$PWD/.git/index") ;;
  *) printf '%s\n' 'Veil Guard: alternate commit index unsupported.' >&2; exit 2 ;;
esac
'/absolute/path/to/veilguard' scan --staged --repo . 2>/dev/null
status=$?
if [ "$status" -ne 0 ]; then
  printf '%s\n' 'Veil Guard: commit stopped; review redacted scan output.' >&2
  exit 2
fi
# Continue the rest of your existing checks here.

Replace the placeholder path with a trusted installed binary. Never source repository shell configuration.
No model is enabled automatically. Git --no-verify can bypass hooks; this is a convenience, not enforcement.
"#;

fn wrapper(executable: &str) -> Result<String, &'static str> {
    if !Path::new(executable).is_absolute()
        || executable.len() > 4096
        || executable.chars().any(char::is_control)
    {
        return Err("hook_executable_unsupported");
    }
    let quoted = format!("'{}'", executable.replace('\'', "'\\''"));
    let content = format!(
        r#"#!/bin/sh
# Veil Guard managed pre-commit v1; uninstall only with matching ownership record.
case "${{GIT_INDEX_FILE:-}}" in
  ''|.git/index|"$PWD/.git/index") ;;
  *) printf '%s\n' 'Veil Guard: alternate commit index unsupported; commit stopped.' >&2; exit 2 ;;
esac
{quoted} scan --staged --repo . 2>/dev/null
status=$?
case "$status" in 0|1|2|3) ;; *) status=2 ;; esac
if [ "$status" -ne 0 ]; then
  printf '%s\n' 'Veil Guard: commit stopped; review the redacted scan output.' >&2
fi
exit "$status"
"#
    );
    if content.len() > LIMIT {
        return Err("hook_wrapper_size_limit");
    }
    Ok(content)
}

fn exists(path: &Path) -> Result<bool, &'static str> {
    match fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err("hook_metadata_unavailable"),
    }
}

fn directory(repo: &Path) -> Result<PathBuf, &'static str> {
    if !cfg!(unix) {
        return Err("platform_unsupported");
    }
    // Hook management must not guess how Git invocation overrides route hooks.
    if std::env::vars_os().any(|(key, _)| key.as_encoded_bytes().starts_with(b"GIT_")) {
        return Err("hook_git_environment_unsupported");
    }
    let scoped = repository::open(repo, Instant::now(), Duration::from_secs(10))?;
    let local = scoped
        .repo
        .config()
        .map_err(|_| "hook_config_unavailable")?;
    let defaults = git2::Config::open_default().map_err(|_| "hook_config_unavailable")?;
    for config in [&local, &defaults] {
        let mut entries = config
            .entries(None)
            .map_err(|_| "hook_config_unavailable")?;
        while let Some(entry) = entries.next() {
            let entry = entry.map_err(|_| "hook_config_unavailable")?;
            let name = entry.name().map_err(|_| "hook_config_unavailable")?;
            if name.starts_with("include.") || name.starts_with("includeif.") {
                return Err("hook_config_include_manual_integration_required");
            }
        }
        match config.get_entry("core.hookspath") {
            Ok(_) => return Err("custom_hooks_path_manual_integration_required"),
            Err(e) if e.code() == git2::ErrorCode::NotFound => {}
            Err(_) => return Err("hook_config_unavailable"),
        }
    }
    if !scoped.unchanged() {
        return Err("repository_metadata_changed");
    }
    let directory = scoped.repo.path().join("hooks");
    if let Ok(meta) = fs::symlink_metadata(&directory)
        && (!meta.is_dir() || meta.file_type().is_symlink())
    {
        return Err("hook_directory_unsupported");
    }
    Ok(directory)
}

struct Lock(PathBuf);
impl Drop for Lock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn lock(directory: &Path) -> Result<Lock, &'static str> {
    let path = directory.join(LOCK);
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|_| "hook_management_locked")?;
    Ok(Lock(path))
}

fn save_new(path: &Path, bytes: &[u8], executable: bool) -> Result<(), &'static str> {
    let mut temporary = tempfile::NamedTempFile::new_in(path.parent().ok_or("hook_path_invalid")?)
        .map_err(|_| "hook_write_failed")?;
    temporary
        .write_all(bytes)
        .map_err(|_| "hook_write_failed")?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        temporary
            .as_file()
            .set_permissions(fs::Permissions::from_mode(if executable {
                0o700
            } else {
                0o600
            }))
            .map_err(|_| "hook_write_failed")?;
    }
    temporary
        .as_file()
        .sync_all()
        .map_err(|_| "hook_write_failed")?;
    temporary
        .persist_noclobber(path)
        .map_err(|_| "hook_destination_exists_or_unavailable")?;
    Ok(())
}

pub fn install(repo: &Path, executable: &Path) -> Result<&'static str, &'static str> {
    let executable = executable.to_str().ok_or("hook_executable_unsupported")?;
    let content = wrapper(executable)?;
    let directory = directory(repo)?;
    if !exists(&directory)? {
        fs::create_dir(&directory).map_err(|_| "hook_directory_unavailable")?;
    }
    let _lock = lock(&directory)?;
    let hook = directory.join("pre-commit");
    let record = directory.join(RECORD);
    if exists(&hook)? || exists(&record)? {
        return Err("existing_hook_or_record_preserved");
    }
    let bytes = serde_json::to_vec(&Record {
        schema: "veilguard.hook-record.v1".into(),
        executable: executable.into(),
    })
    .map_err(|_| "hook_record_invalid")?;
    save_new(&record, &bytes, false)?;
    if let Err(code) = save_new(&hook, content.as_bytes(), true) {
        // Only our freshly created record is rolled back; an existing hook is never removed.
        let _ = fs::remove_file(&record);
        return Err(code);
    }
    Ok(
        "Veil Guard: installed rule-only pre-commit hook bound to this executable location; retain the binary. Existing hooks are never overwritten.",
    )
}

pub fn uninstall(repo: &Path) -> Result<&'static str, &'static str> {
    let directory = directory(repo)?;
    if !exists(&directory)? {
        return Ok("Veil Guard: no managed hook installed.");
    }
    let _lock = lock(&directory)?;
    let hook = directory.join("pre-commit");
    let record = directory.join(RECORD);
    if !exists(&record)? {
        return if exists(&hook)? {
            Err("unowned_hook_preserved")
        } else {
            Ok("Veil Guard: no managed hook installed.")
        };
    }
    let bytes = local_input::read(&record, LIMIT).map_err(|_| "hook_record_unavailable")?;
    let record_data: Record = serde_json::from_slice(&bytes).map_err(|_| "hook_record_invalid")?;
    if record_data.schema != "veilguard.hook-record.v1" {
        return Err("hook_record_invalid");
    }
    let expected = wrapper(&record_data.executable)?;
    let actual =
        local_input::read(&hook, LIMIT).map_err(|_| "managed_hook_missing_or_unavailable")?;
    if actual != expected.as_bytes() {
        return Err("modified_hook_preserved");
    }
    fs::remove_file(&hook).map_err(|_| "hook_remove_failed")?;
    fs::remove_file(&record).map_err(|_| "hook_record_remove_failed")?;
    Ok("Veil Guard: removed matching managed pre-commit hook.")
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn wrapper_and_record_can_always_be_read_with_the_ownership_budget() {
        assert!(wrapper("/relative\nprivate").is_err());
        assert!(wrapper("relative").is_err());
        assert!(wrapper(&format!("/{}", "'".repeat(4095))).is_err());
        let executable = format!("/{}", "x".repeat(4095));
        assert!(wrapper(&executable).unwrap().len() <= LIMIT);
        let record = serde_json::to_vec(&Record {
            schema: "veilguard.hook-record.v1".into(),
            executable,
        })
        .unwrap();
        assert!(record.len() <= LIMIT);
    }
}
