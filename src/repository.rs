//! Conservative repository layout policy, before opening an index/object database.
//! This is preflight validation, not a filesystem sandbox against concurrent attacks.
use git2::{Config, ErrorCode, ObjectType, Repository, RepositoryOpenFlags, Tree, TreeEntry};
use std::fs::{self, Metadata};
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};
use std::time::{Duration, Instant};

const MAX_ENTRIES: usize = 100_000;
const CONFIG_BYTES: u64 = 1024 * 1024;
const INDEX_BYTES: u64 = 16 * 1024 * 1024;
const REF_BYTES: u64 = 4 * 1024 * 1024;
const TREE_BYTES: usize = 16 * 1024 * 1024;

#[derive(PartialEq, Eq)]
struct Stamp {
    bytes: u64,
    modified: Option<std::time::SystemTime>,
    #[cfg(unix)]
    identity: (u64, u64),
}

fn metadata(path: &Path) -> Result<Option<Metadata>, &'static str> {
    match fs::symlink_metadata(path) {
        Ok(meta) if meta.file_type().is_symlink() => Err("repository_metadata_symlink"),
        Ok(meta) => Ok(Some(meta)),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(_) => Err("repository_metadata_unavailable"),
    }
}

fn stamp(path: &Path) -> Result<Option<Stamp>, &'static str> {
    metadata(path).map(|meta| {
        meta.map(|meta| Stamp {
            bytes: meta.len(),
            modified: meta.modified().ok(),
            #[cfg(unix)]
            identity: {
                use std::os::unix::fs::MetadataExt;
                (meta.dev(), meta.ino())
            },
        })
    })
}

fn regular(path: &Path, cap: u64, required: bool) -> Result<(), &'static str> {
    match metadata(path)? {
        Some(meta) if !meta.is_file() => Err("repository_metadata_type_unsupported"),
        Some(meta) if meta.len() > cap => Err("repository_metadata_limit_exceeded"),
        None if required => Err("repository_metadata_missing"),
        _ => Ok(()),
    }
}

fn read_small(path: &Path, cap: u64) -> Result<Vec<u8>, &'static str> {
    regular(path, cap, true)?;
    let mut file = fs::File::open(path).map_err(|_| "repository_metadata_unavailable")?;
    let mut bytes = Vec::new();
    file.by_ref()
        .take(cap + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "repository_metadata_unavailable")?;
    if bytes.len() as u64 > cap {
        return Err("repository_metadata_limit_exceeded");
    }
    Ok(bytes)
}

fn exists(path: &Path) -> Result<bool, &'static str> {
    Ok(metadata(path)?.is_some())
}

fn locate(path: &Path) -> Result<(PathBuf, PathBuf), &'static str> {
    let mut directory = fs::canonicalize(path).map_err(|_| "repository_unavailable")?;
    if !directory.is_dir() {
        return Err("repository_directory_required");
    }
    for _ in 0..256 {
        if directory.file_name().is_some_and(|name| name == ".git") {
            return Err("repository_metadata_path_unsupported");
        }
        let gitdir = directory.join(".git");
        if let Some(meta) = metadata(&gitdir)? {
            if !meta.is_dir() {
                return Err("gitfile_layout_unsupported");
            }
            return Ok((directory, gitdir));
        }
        if exists(&directory.join("HEAD"))?
            && directory.join("objects").is_dir()
            && directory.join("refs").is_dir()
        {
            return Err("bare_repository_unsupported");
        }
        if !directory.pop() {
            return Err("repository_unavailable");
        }
    }
    Err("repository_discovery_limit_exceeded")
}

fn config_policy(path: &Path) -> Result<Config, &'static str> {
    let text = String::from_utf8(read_small(path, CONFIG_BYTES)?)
        .map_err(|_| "repository_config_unsupported")?;
    // Reject file inclusion before asking libgit2 to parse the configuration.
    // Backslash continuations/escaped section forms are deliberately unsupported.
    let mut section = false;
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with(['#', ';']) {
            continue;
        }
        if line.contains('\\') {
            return Err("repository_config_unsupported");
        }
        if line.starts_with('[') {
            let close = line.find(']').ok_or("repository_config_invalid")?;
            let name = line[1..close]
                .split(|c: char| c.is_ascii_whitespace() || c == '.')
                .next()
                .unwrap_or("")
                .to_ascii_lowercase();
            if name == "include" || name == "includeif" {
                return Err("repository_config_include_unsupported");
            }
            let suffix = line[close + 1..].trim();
            if name.is_empty() || (!suffix.is_empty() && !suffix.starts_with(['#', ';'])) {
                return Err("repository_config_invalid");
            }
            section = true;
        } else if !section {
            return Err("repository_config_invalid");
        }
    }
    let config = Config::open(path).map_err(|_| "repository_config_invalid")?;
    let format = config
        .get_i32("core.repositoryformatversion")
        .map_err(|_| "repository_format_unsupported")?;
    if !(0..=1).contains(&format) {
        return Err("repository_format_unsupported");
    }
    if config
        .get_bool("core.bare")
        .map_err(|_| "repository_config_invalid")?
    {
        return Err("bare_repository_unsupported");
    }
    if config.get_entry("core.worktree").is_ok() {
        return Err("redirected_worktree_unsupported");
    }
    for key in ["core.sparsecheckout", "index.sparse"] {
        match config.get_bool(key) {
            Ok(true) => return Err("sparse_index_unsupported"),
            Ok(false) => {}
            Err(error) if error.code() == ErrorCode::NotFound => {}
            Err(_) => return Err("repository_config_invalid"),
        }
    }
    let mut entries = config
        .entries(None)
        .map_err(|_| "repository_config_invalid")?;
    while let Some(entry) = entries.next() {
        let entry = entry.map_err(|_| "repository_config_invalid")?;
        let name = entry.name().map_err(|_| "repository_config_invalid")?;
        if name.starts_with("extensions.")
            && (name != "extensions.objectformat" || entry.value().ok() != Some("sha1"))
        {
            return Err("repository_extension_unsupported");
        }
        if name.ends_with(".promisor") {
            return Err("partial_clone_unsupported");
        }
    }
    drop(entries);
    Ok(config)
}

fn walk(
    root: &Path,
    cap_files: bool,
    controls: &mut Vec<PathBuf>,
    count: &mut usize,
    start: Instant,
    deadline: Duration,
) -> Result<(), &'static str> {
    if !metadata(root)?.is_some_and(|m| m.is_dir()) {
        return Err("repository_metadata_missing");
    }
    let mut stack = vec![root.to_path_buf()];
    while let Some(directory) = stack.pop() {
        for entry in fs::read_dir(directory).map_err(|_| "repository_metadata_unavailable")? {
            if start.elapsed() >= deadline {
                return Err("repository_preflight_deadline_exceeded");
            }
            *count += 1;
            if *count > MAX_ENTRIES {
                return Err("repository_metadata_entry_limit_exceeded");
            }
            let entry = entry.map_err(|_| "repository_metadata_unavailable")?;
            let path = entry.path();
            let meta = metadata(&path)?.ok_or("repository_metadata_changed")?;
            if meta.is_dir() {
                if cap_files {
                    controls.push(path.clone());
                }
                stack.push(path);
            } else if meta.is_file() {
                if cap_files {
                    if meta.len() > REF_BYTES {
                        return Err("repository_metadata_limit_exceeded");
                    }
                    controls.push(path);
                }
            } else {
                return Err("repository_metadata_type_unsupported");
            }
        }
    }
    Ok(())
}

pub(crate) struct ScopedRepository {
    pub repo: Repository,
    controls: Vec<(PathBuf, Option<Stamp>)>,
}

impl ScopedRepository {
    pub fn unchanged(&self) -> bool {
        self.controls
            .iter()
            .all(|(path, initial)| stamp(path).is_ok_and(|now| &now == initial))
    }
}

pub(crate) fn open(
    path: &Path,
    start: Instant,
    deadline: Duration,
) -> Result<ScopedRepository, &'static str> {
    let (root, gitdir) = locate(path)?;
    // Validate parent directories before looking up any child control files.
    for relative in ["objects", "refs", "info", "objects/info", "objects/pack"] {
        if let Some(meta) = metadata(&gitdir.join(relative))?
            && !meta.is_dir()
        {
            return Err("repository_metadata_type_unsupported");
        }
    }
    for relative in [
        "commondir",
        "gitdir",
        "config.worktree",
        "shallow",
        "info/grafts",
        "objects/info/alternates",
        "objects/info/http-alternates",
    ] {
        if exists(&gitdir.join(relative))? {
            return Err("repository_layout_unsupported");
        }
    }
    for lock in ["index.lock", "HEAD.lock", "config.lock", "packed-refs.lock"] {
        if exists(&gitdir.join(lock))? {
            return Err("repository_update_in_progress");
        }
    }
    // Shared-index storage is deliberately not part of the supported Phase One scope.
    let mut count = 0;
    for entry in fs::read_dir(&gitdir).map_err(|_| "repository_metadata_unavailable")? {
        if start.elapsed() >= deadline {
            return Err("repository_preflight_deadline_exceeded");
        }
        count += 1;
        if count > MAX_ENTRIES {
            return Err("repository_metadata_entry_limit_exceeded");
        }
        let entry = entry.map_err(|_| "repository_metadata_unavailable")?;
        if entry
            .file_name()
            .as_encoded_bytes()
            .starts_with(b"sharedindex.")
        {
            return Err("split_index_unsupported");
        }
    }
    regular(&gitdir.join("HEAD"), 4096, true)?;
    regular(&gitdir.join("index"), INDEX_BYTES, false)?;
    regular(&gitdir.join("packed-refs"), INDEX_BYTES, false)?;
    if let Some(meta) = metadata(&gitdir.join("info"))?
        && !meta.is_dir()
    {
        return Err("repository_metadata_type_unsupported");
    }
    let config = config_policy(&gitdir.join("config"))?;
    let head = read_small(&gitdir.join("HEAD"), 4096)?;
    let head = std::str::from_utf8(&head)
        .map_err(|_| "head_invalid")?
        .trim();
    let mut paths = vec![
        gitdir.join("HEAD"),
        gitdir.join("index"),
        gitdir.join("config"),
        gitdir.join("packed-refs"),
        gitdir.join("refs"),
    ];
    if let Some(target) = head.strip_prefix("ref: ") {
        let target_path = Path::new(target);
        if !target.starts_with("refs/")
            || target_path
                .components()
                .any(|c| !matches!(c, Component::Normal(_)))
        {
            return Err("head_invalid");
        }
        paths.push(gitdir.join(target_path)); // Also watch the missing ref of an unborn branch.
    } else if head.len() != 40 || !head.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("head_invalid");
    }
    walk(
        &gitdir.join("objects"),
        false,
        &mut paths,
        &mut count,
        start,
        deadline,
    )?;
    walk(
        &gitdir.join("refs"),
        true,
        &mut paths,
        &mut count,
        start,
        deadline,
    )?;
    if metadata(&gitdir.join("info"))?.is_some() {
        walk(
            &gitdir.join("info"),
            false,
            &mut paths,
            &mut count,
            start,
            deadline,
        )?;
    }
    if metadata(&gitdir.join("index"))?.is_some() {
        let header = read_small(&gitdir.join("index"), INDEX_BYTES)?;
        if header.len() < 12 || &header[..4] != b"DIRC" {
            return Err("index_header_invalid");
        }
        let version = u32::from_be_bytes(header[4..8].try_into().expect("four bytes"));
        if !(2..=4).contains(&version) {
            return Err("index_version_unsupported");
        }
    }
    paths.sort();
    paths.dedup();
    let controls = paths
        .into_iter()
        .map(|path| {
            let initial = stamp(&path)?;
            Ok((path, initial))
        })
        .collect::<Result<Vec<_>, &'static str>>()?;
    let repo = Repository::open_ext(
        &gitdir,
        RepositoryOpenFlags::NO_SEARCH | RepositoryOpenFlags::NO_DOTGIT,
        &[] as &[&std::ffi::OsStr],
    )
    .map_err(|_| "repository_open_failed")?;
    if repo.is_bare()
        || repo.is_worktree()
        || repo
            .workdir()
            .and_then(|p| fs::canonicalize(p).ok())
            .as_ref()
            != Some(&root)
    {
        return Err("repository_layout_unsupported");
    }
    repo.set_config(&config)
        .map_err(|_| "repository_config_invalid")?;
    let scoped = ScopedRepository { repo, controls };
    if !scoped.unchanged() {
        return Err("repository_metadata_changed");
    }
    Ok(scoped)
}

fn tree(repo: &Repository, id: git2::Oid) -> Result<Tree<'_>, &'static str> {
    let odb = repo.odb().map_err(|_| "object_database_unavailable")?;
    let (size, kind) = odb
        .read_header(id)
        .map_err(|_| "baseline_tree_unavailable")?;
    if kind != ObjectType::Tree || size > TREE_BYTES {
        return Err("baseline_tree_unsupported");
    }
    repo.find_tree(id).map_err(|_| "baseline_tree_unavailable")
}

pub(crate) fn head_tree(repo: &Repository) -> Result<Option<Tree<'_>>, &'static str> {
    let head = match repo.head() {
        Ok(head) => head,
        Err(error) if error.code() == ErrorCode::UnbornBranch => return Ok(None),
        Err(_) => return Err("head_unavailable"),
    };
    let id = head.target().ok_or("head_unavailable")?;
    let odb = repo.odb().map_err(|_| "object_database_unavailable")?;
    let (size, kind) = odb.read_header(id).map_err(|_| "head_object_unavailable")?;
    if kind != ObjectType::Commit || size > TREE_BYTES {
        return Err("head_object_unsupported");
    }
    let commit = repo
        .find_commit(id)
        .map_err(|_| "head_commit_unavailable")?;
    tree(repo, commit.tree_id()).map(Some)
}

pub(crate) fn baseline(
    repo: &Repository,
    root: &Tree<'_>,
    path: &[u8],
) -> Result<Option<TreeEntry<'static>>, &'static str> {
    let mut current = root.clone();
    let parts: Vec<_> = path.split(|b| *b == b'/').collect();
    for (index, part) in parts.iter().enumerate() {
        let Some(entry) = current.get_name_bytes(part).map(|e| e.to_owned()) else {
            return Ok(None);
        };
        if index + 1 == parts.len() {
            return Ok(Some(entry));
        }
        if entry.kind() != Some(ObjectType::Tree) {
            return Ok(None); // A staged directory replaced a baseline file.
        }
        current = tree(repo, entry.id())?;
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn control_snapshot_detects_a_new_index_and_config_edits() {
        for relative in ["index", "config", "HEAD"] {
            let directory = tempfile::tempdir().unwrap();
            Repository::init(directory.path()).unwrap();
            let scoped = open(directory.path(), Instant::now(), Duration::from_secs(10)).unwrap();
            fs::write(
                directory.path().join(".git").join(relative),
                b"changed fixture metadata\n",
            )
            .unwrap();
            assert!(!scoped.unchanged());
        }
    }

    #[test]
    fn worktree_only_edits_do_not_invalidate_the_metadata_snapshot() {
        let directory = tempfile::tempdir().unwrap();
        Repository::init(directory.path()).unwrap();
        let scoped = open(directory.path(), Instant::now(), Duration::from_secs(10)).unwrap();
        fs::write(
            directory.path().join("fixture.txt"),
            "working-tree-only fixture\n",
        )
        .unwrap();
        assert!(scoped.unchanged());
    }
}
