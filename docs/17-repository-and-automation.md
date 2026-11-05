# Repository formats and automated acceptance

Updated: 5 November 2026. Development version: 0.1.0-dev.3. Branch: phase-one/staged-scanner.

This document records Phase One's supported repository boundary and acceptance automation. Git layout documentation describes the available storage arrangements ([R25](13-sources.md#r25)); libgit2 documents explicit open flags ([R26](13-sources.md#r26)). The restrictions below are our conservative policy, not universal Git requirements or a filesystem-sandbox guarantee.

## Supported formats

| Arrangement | Phase One policy / evidence |
| --- | --- |
| Ordinary non-bare SHA-1 worktree with a real .git directory | Supported |
| Root or nested working directory as the selected input | Supported; bounded parent discovery |
| Unborn symbolic HEAD with no branch commit yet | Empty baseline; supported |
| Existing branch HEAD or detached HEAD pointing to a commit | Supported; missing/corrupt objects fail |
| Loose or packed objects; loose or packed refs | Supported; packed-storage regression fixture |
| Index versions 2, 3 and 4 | Supported; v3 extended-entry and v4 fixtures, existing v2 staging suite |
| Mode-only changes, additions, modifications and deletions | Compared using object bytes and index entries |
| Renames | Conservatively treated as additions at the new path |
| Non-Unix systems | Explicitly refused; Windows support remains deferred |

The local config must explicitly contain parseable core.repositoryformatversion (0 or 1) and core.bare=false values, with no extension except explicit sha1 object format. Object IDs are not interpreted as proof of integrity against an attacker who controls the repository; they are Git addressing.

## Refused before source scanning

| Condition | Representative static error |
| --- | --- |
| .git file, linked worktree, separate Git directory or submodule-style Git link | gitfile_layout_unsupported |
| Direct selection of a .git metadata directory | repository_metadata_path_unsupported |
| Bare repository or core.bare true | bare_repository_unsupported |
| Configured core.worktree redirect | redirected_worktree_unsupported |
| commondir/gitdir/config.worktree markers, shallow history or grafts | repository_layout_unsupported |
| Object alternates or HTTP alternates, including empty marker files | repository_layout_unsupported |
| Split-index shared storage | split_index_unsupported |
| Sparse-checkout/index settings | sparse_index_unsupported |
| Promisor/partial-clone configuration | partial_clone_unsupported |
| SHA-256, reftable or another unapproved extension | repository_extension_unsupported |
| Repository config include/includeIf | repository_config_include_unsupported |
| Backslash continuations/escapes in local config | repository_config_unsupported |
| Metadata symlink or unsupported special file | repository_metadata_symlink / repository_metadata_type_unsupported |
| Existing index/HEAD/config/packed-refs lock | repository_update_in_progress |
| Invalid/missing/oversized metadata or unsupported index header | Specific static metadata/index error |

This can refuse legitimate advanced Git setups. The scanner does not delete markers, rewrite configuration, expand sparse checkouts or copy alternate objects to make them pass. Use an ordinary supported checkout when testing this prototype.

## Discovery and source-read boundary

The caller's directory is canonicalised, then at most 256 parents are considered. The first .git marker stops discovery; an unsupported child marker is not skipped in favour of a parent repository. Caller-selected directory symlinks resolve at this initial canonicalisation step. Critical repository metadata is then checked without following metadata symlinks.

The scanner checks object/ref/info directories and control files before opening the repository, rejects redirected layouts, and explicitly opens the selected .git directory with NO_SEARCH and NO_DOTGIT. It does not enable FROM_ENV. Tests show that GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR, GIT_INDEX_FILE, GIT_OBJECT_DIRECTORY, GIT_ALTERNATE_OBJECT_DIRECTORIES and GIT_NAMESPACE overrides do not redirect the selected scan.

The pinned libgit2 source was reviewed for open/config/index/object paths. Initial library open can read the user's standard global/system Git configuration as trusted metadata. After open, the scanner attaches the reviewed local configuration. This is not a claim that the process reads no files outside the checkout: system libraries, standard user/system Git config and explicitly requested output destinations are separate from source-blob scope.

Repository-directed includes are rejected before the local config is parsed by libgit2. There is no process-global environment mutation. The runtime does not execute Git, hooks, external diffs, filters or fsmonitor commands; regression fixtures cover these command settings. Development scripts intentionally run Git/Cargo on disposable fixtures or this project's source and are not runtime scanner code.

## Corruption and concurrent changes

A generic NotFound error is no longer treated as an unborn repository. Only the library's explicit UnbornBranch case permits an empty baseline. Existing HEAD objects must be commits; their trees must be available.

Baseline paths are walked through tree entries. A genuinely absent entry means added content; an entry whose child tree is missing is an incomplete scan. This distinction prevents corrupt nested trees from being silently treated as a new path. Already collected findings remain available, with paths withheld.

Control-file/ref metadata stamps are checked after opening and after scanning. A detected index, HEAD, config or ref change makes the result incomplete. Worktree-only edits do not invalidate the index snapshot.

These are best-effort checks, not race-proof confinement. A concurrently malicious process can race filesystem lookups or manipulate metadata timestamps. The current scanner is not an OS sandbox, does not hold immutable handles to every directory/object, and is not designed to defeat a compromised local machine.

## Metadata budgets

| Input | Limit |
| --- | --- |
| Local config | 1 MiB |
| HEAD control file | 4,096 bytes |
| Index and packed-refs | 16 MiB each |
| Individual loose ref metadata | 4 MiB |
| Each loaded commit/tree object | 16 MiB |
| Considered metadata entries across the inspected directories | 100,000 |
| Parent discovery | 256 levels |

The existing 1 MiB blob, 20 MiB combined source-blob, candidate/finding and path-redaction budgets still apply. inspected_bytes counts source blobs, not all metadata IO. The cooperative deadline is checked during metadata traversal and scan scheduling. It cannot interrupt an individual filesystem/library call; process-level memory/time isolation is not claimed.

## One local acceptance command

From /Users/richy/Documents/Github/veilguard:

~~~sh
python3 scripts/check_all.py
~~~

Phase Two also requires uv 0.13.7 and Python 3.12 or newer; follow the [environment setup](18-phase-two-feature-parity.md#reproduce).

With the pinned toolchain and dependencies already installed, cached-Cargo operation is available:

~~~sh
python3 scripts/check_all.py --offline
~~~

The script runs whitespace checks, rustfmt, Clippy with warnings denied, all Rust tests, the optimized build, source/link/arithmetic documentation checks an optimized scan smoke fixture, Python reference/gate tests, eight-dimensional parity and the [frozen corpus/materialisation checks](19-phase-three-corpus.md).

The smoke fixture stages an authored nonfunctional token shape, changes the worktree, and verifies that the binary still reads the staged bytes. It then reverses the arrangement. It checks output redaction and unchanged index/worktree bytes. No provider request or real credential is involved.

rust-toolchain.toml pins Rust 1.98.1 with rustfmt/Clippy. Cargo.lock pins dependencies, and vendored-libgit2 ensures the bundled library matching the reviewed crate source is used rather than an arbitrary installed system library. Initial setup/build may download these tools; --offline is a Cargo setting, not network isolation for the entire development process.

## GitHub Actions

The [workflow](../.github/workflows/phase-one.yml) runs the same acceptance script on macos-15 and ubuntu-24.04 for main/Phase One/Phase Two/Phase Three pushes and pull requests to main. Runner environments are recorded in the logs; labels are documented by GitHub ([R27](13-sources.md#r27)).

The workflow uses read-only contents permission, disables persisted checkout credentials, pins official checkout/setup-python actions to reviewed commit SHAs, and gives each job a 15-minute timeout. It builds/tests source; it does not grant release/deployment permissions.

[Workflow runs and logs](https://github.com/richardwaters9049/Veil-Guard/actions/workflows/phase-one.yml) are the authoritative per-commit CI result. A configuration file alone is not evidence of a passing run. Linux CI checks are engineering compatibility evidence, not a packaged Linux release claim.

## Acceptance record and scope

At the Phase One tip, local acceptance passed 62 Rust tests: 41 staged/candidate/report integration tests, 16 repository/output-scope integration tests, three library tests and two panic-guard tests. The repository/configuration matrix includes 21 refusal cases within one integration test. Tests also cover supported packed storage, index v3/v4, detached HEAD, corrupt baseline trees, metadata changes, special files, missing output parents, broken stdout and panic-payload/backtrace redaction.

The Rust panic child is a test-only subprocess; no panic-injection environment option exists in the shipped binary. Production error writes tolerate a broken stderr without formatting private panic payloads.

Milestones 1A/1B/1C now have implemented checks for the declared Phase One scope. The current branch must pass the local command and its CI run before acceptance. [Phase Two](18-phase-two-feature-parity.md) adds feature extraction/parity; training, KNN, inference, hooks and packaged releases remain later phases. There is no measured real-world accuracy, AI benefit, calibrated probability or sandbox-security claim.
