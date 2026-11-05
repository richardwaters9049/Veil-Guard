# Phase Six — hardening and packaging

Status: hook management implemented; broader release gates remain open. Entry is the integrated [Phase Five scanner](22-phase-five-native-inference.md) at commit 558b086, followed by the branch-policy correction 18b922c. Work uses `phase-six/hardening-and-packaging` as defined in the [delivery plan](09-delivery-plan.md).

Git index semantics are described by [R17](13-sources.md#r17); the local metadata implementation uses [R18](13-sources.md#r18). Hook ownership, refusal and failure rules below are project choices tested with authored nonfunctional fixtures. They do not establish organisation-wide enforcement.

## Explicit hook management

From a trusted binary at a stable absolute location:

```sh
/absolute/path/to/veilguard hooks install --repo /absolute/path/to/owned-repository
/absolute/path/to/veilguard hooks uninstall --repo /absolute/path/to/owned-repository
/absolute/path/to/veilguard hooks manual
```

These are deliberate commands. Scanning, model inspection and explanations do not install or run Git hooks. No hook is installed in this project as part of implementation or acceptance checks; all installation tests use temporary repositories.

Install writes only `.git/hooks/pre-commit` and its `.veilguard-pre-commit.json` ownership record. A temporary `.veilguard-hooks.lock` serialises management commands. No Git config, index, worktree source or other hook is changed. A missing hooks directory is created; existing files, symlinks or ownership records are never overwritten. Unix hook/record permissions are 0700/0600. Files are written through private temporary files and published without clobbering an existing destination.

The wrapper calls the absolute executable used for installation, safely quoted for the shell, with `scan --staged --repo .`. It does not search PATH, source repository scripts or discover a model. Keep that executable available: installing from a debug build or moving/deleting the binary can stop commits until you uninstall/reinstall with a stable binary. Upgrading the binary in place changes what future commits run; signed distribution and release verification remain pending.

The hook propagates scanner codes 0–3. Unexpected execution failures become 2 and stop the commit. Scanner stdout is redacted; stderr from the executable launch is suppressed to avoid leaking executable paths, and failures receive a fixed message. Run the scan manually to see its safe error code. No source value, binary path or Git environment value is interpolated into failure messages.

Git can commit through a temporary alternate index (for example, selected-file/partial commit modes). The current scanner intentionally reads the repository's normal index. The wrapper therefore refuses `GIT_INDEX_FILE` unless it is empty, `.git/index` or the absolute `$PWD/.git/index`; it does not pretend to protect a different commit index. Ordinary staged commits are tested. This constraint is visible and intentional; broader alternate-index support requires its own scoped implementation and tests.

## Existing hook managers and safe removal

Automatic management refuses local or default/global/system `core.hooksPath` settings and default configuration includes (including conditional includes), so it cannot silently miss a hook-manager setting from a different inclusion context. Use `hooks manual` to integrate with an existing manager while retaining its other checks and propagating Veil Guard failure. Hook management reads Git's default personal/system configuration for this check; the scanner continues to use its isolated local configuration. Management also refuses a `GIT_*` environment override rather than guessing which repository or hook path the eventual Git invocation uses. Clear those overrides before management, or integrate manually. `hooks manual` itself does not open a repository or inspect configuration.

Uninstall requires a valid private ownership record and an exact byte match to the generated wrapper. An unowned hook, edited hook, invalid/missing record, symlink or missing managed hook is preserved/refused rather than deleted. When neither hook nor record exists, uninstall succeeds without changing anything. A record remembers the original executable location, so uninstall works from a replacement binary after moving the old one.

Operations are not a filesystem sandbox against concurrent malicious edits. Existing repository preflight restrictions still apply; linked worktrees/gitfiles, bare or redirected layouts remain unsupported. The lock coordinates Veil Guard management commands only. Crashes can leave a lock or ownership record; inspect those manually rather than using automatic lock stealing. If a removal fails midway, the fixed error reports the failed step; inspect the remaining hook/record before retrying. The tool never executes an existing hook to inspect it. Git's own hook bypass options mean this is a local convenience, not tamper-proof policy enforcement.

## Verification and automation

`tests/hooks.rs` covers install/uninstall permissions and unchanged config/index/source; existing/unowned/edited hooks; local/global custom hook paths; Git environment overrides; management locks; symlinked directories/files/records; actual clean and blocked commits; staged/worktree disagreement; alternate-index refusal; shell-sensitive executable paths; missing-binary failure; and uninstall from a replacement binary. Tests run only authored nonfunctional values and perform no push/provider validation.

```sh
cargo test --locked --offline --test hooks
python3 scripts/check_all.py --offline
```

The existing acceptance workflow now watches the established `phase-five/**`, `phase-six/**` and `phase-seven/**` names as well as earlier phases, with no alternate branch prefix. Local passing tests do not imply the remote macOS/Linux matrix has run.

## Remaining release gates

Phase Six is **in progress**, not complete. The [dependency review, local benchmarks, runtime instrumentation and development-package evidence](24-phase-six-evidence.md) are now recorded, with an [install/verification guide](25-install-and-verification.md). Native/OS patch applicability, licence approval, model distribution integrity, remote Linux results, independent build reproduction and fresh-OS/platform validation remain release gates. Corpus licensing, independent label review, naming clearance and release approval remain tracked programme items. The failed synthetic AI benefit gate is unchanged.
