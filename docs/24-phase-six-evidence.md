# Phase Six — dependency review, runtime evidence and development packages

Recorded 5 November 2026. These are scoped local engineering results, not public release approval. The CLI remains `0.1.0-dev.6`; the frozen model and failed synthetic benefit gate are unchanged.

## Dependency and licence review

[RustSec, R31](13-sources.md#r31) and [pip-audit, R34](13-sources.md#r34) check known advisories. The [dated review](../research/results/phase-six/dependency-review-2026-11-05/review.json) records cargo-audit 0.22.2, RustSec database commit `26fd2d43f7280a1fb925a3743ec463017afe7119`, 54 lockfile dependencies, zero reported Rust vulnerabilities/warnings, and zero reported advisories across 17 installed research distributions using pip-audit 2.10.1. The research environment is separate from the shipped CLI. The Phase Three environment declares no external Python dependencies. Audit services received names/versions, not repository source or findings.

The host-resolved [Cargo metadata, R32](13-sources.md#r32) inventory has 47 third-party crates plus this unlicensed project. It records features, declared licence expressions and hashes of 106 upstream notice/licence files. Crate-level declarations are not a legal compatibility decision. `unicode-ident` has an additional Unicode term; `rustix` lists alternatives including an LLVM exception. No automatic OR-licence choice or project licence grant is made.

Native review matters: the `libgit2-sys` wrapper's declaration does not replace [libgit2 COPYING and its linking exception, R35](13-sources.md#r35). Its build script includes bundled llhttp, xdiff and PCRE2. The notice collection conservatively includes native component notices and unused/build-only components; it is not a precise binary-level licence attribution map. Rust standard-library copyright/licence notices are also included in the development package. Research-distribution metadata and installed licence-file hashes are recorded but those distributions are not packaged.

The [native review record](../research/results/phase-six/native-review.json) captures component/OS observations and the unresolved release decision.

[libgit2 security information, R37](13-sources.md#r37) was reviewed separately. [zlib, R36](13-sources.md#r36) published 1.4 on 4 November 2026 with security fixes. The measured macOS binary dynamically links `/usr/lib/libz.1.dylib` (reported upstream string 1.2.12), as well as OS libiconv, Security, CoreFoundation and libSystem. The crate source also contains bundled zlib 1.3.2; its presence does not mean that copy was linked on this host. Apple/distribution backport status and affected-call reachability have not been established. No system library was changed. Native/OS patch applicability remains a release gate; zero Rust/Python advisories is not a clean bill of health for C or OS libraries.

Reproduce the metadata/advisory review (cargo-audit must already be installed; the Python audit tool is explicitly pinned):

```sh
python3 scripts/review_dependencies.py --output /new/private/review-directory --python-audit
```

The default refreshes RustSec. `--no-fetch` uses a cached database and records its commit/date; it does not claim freshness. Review results are time-bound, not a permanent clearance. Project source licence, corpus/model redistribution, naming clearance and release approval remain owner decisions. Models/corpus are excluded from packages.

## Benchmarks

[Raw measurements](../research/results/phase-six/benchmark-macos-arm64/benchmark.json) record the host, CPU, release-binary/model hashes, source identities and every run. Three authored ASCII workloads contain 100, 1,000 or 10,000 generic candidates, split into files of at most 500 lines; each is scanned with and without the frozen model. No user source is benchmarked. Setup/build time is excluded; each timed process includes startup, Git reading, parsing, optional model loading and inference. Index/config/source immutability is checked.

Each workload has one first-observed run followed by 20 fresh-process repetitions. The OS file cache is not evicted. Therefore the first run is not a guaranteed filesystem-cold measurement; repetitions are warm-cache opportunities in fresh processes, not an in-process inference microbenchmark. Wall time includes the OS timing utility wrapper; peak RSS is taken from that utility, normalised from macOS bytes or Linux KiB. P95 is the nearest-rank 19th ordered value of 20 repetitions. Small local samples and uncontrolled machine load limit generalisation.

Measured summary and target decisions are in the table below. Both the 2-second p95 and 150 MiB targets are project choices, not guarantees for other workloads or machines.

| Candidates | Model | Original p95 (s) | Exact-selection p95 (s) | New peak RSS (MiB) | New targets |
| ---: | --- | ---: | ---: | ---: | --- |
| 100 | Off | 0.015 | 0.016 | 9.6 | Pass locally |
| 100 | On | 0.048 | 0.021 | 10.4 | Pass locally |
| 1,000 | Off | 0.019 | 0.018 | 10.8 | Pass locally |
| 1,000 | On | 0.307 | 0.064 | 11.9 | Pass locally |
| 10,000 | Off | 0.067 | 0.067 | 27.9 | Pass locally |
| 10,000 | On | 3.052 | 0.506 | 30.5 | Pass locally |

Host: Apple M4, 10 logical CPUs, arm64, Darwin 25.6.0. All measured scans completed. The original 10,000-candidate model workload missed latency (3.052 seconds); that baseline is retained. An exact partial selection now partitions by the same `(distance, opaque ID)` total order and sorts only selected k neighbours, after computing every distance and all zero-match votes. It changes no features, references, model parameters, policy or arithmetic. Native/Python parity still passes all 12,132 predictions with maximum score/distance error 2.22e-16; a separate full-sort oracle covers small and full-reference k. The [new measurements](../research/results/phase-six/benchmark-exact-selection-macos-arm64/benchmark.json) reach 0.506 seconds and 30.5 MiB at 10,000 model-scored candidates. These are observed local results, not a production guarantee.

```sh
python3 scripts/benchmark_scan.py --output /new/private/benchmark-directory --runs 20
```

True cold-cache performance, fresh-OS performance and wider workloads remain unmeasured. A failed workload target remains visible and does not cause the script to discard measurements.

## Offline and repository-command instrumentation

[Runtime evidence](../research/results/phase-six/runtime-macos-arm64/runtime.json) combines selected-API interposition and a macOS sandbox replay. The test-only C guard observes/denies socket, connect, sendto, getaddrinfo, fork, vfork, execve, posix_spawn and posix_spawnp. A compiled positive-control probe must produce each event exactly once before any scanner result is accepted. The probe refuses to proceed unless an exported guard-active symbol is present; numeric loopback input avoids external DNS even in a failed control. Constructor/destructor records on an inherited pipe verify that the guard actually loaded and completed; it logs fixed operation names only.

Both rule-only and model-enabled scans of authored staged fixtures complete with the expected blocking exit 1 and no selected-API events. Repository clean/smudge filters, external diff/textconv, fsmonitor and executable pre-commit tripwires remain untouched; the fixture source/index/config and attribute/hook files remain unchanged. No shell command from repository text was observed executing.

The separate macOS sandbox denies network operations, fork and foreign executable replacement. A loopback connect/fork positive control is denied, and both scanner modes reproduce the unsandboxed JSON exactly. `/var` fixture paths are canonicalised for sandbox literal matching. The scanner continues to work when covered network/process operations are denied. Dynamic interposition is not complete syscall tracing: direct syscalls, other APIs and OS services are outside its observation. This is scoped evidence, not proof of every possible runtime path or a shipped filesystem sandbox.

```sh
python3 scripts/check_runtime.py --output /new/private/runtime-directory
```

Linux uses the same guarded libc positive controls and tripwires in CI. Linux syscall/network-namespace enforcement is not claimed here. The guard and compiler are development tooling only and are never included in the shipped binary/package.

## Development packaging and remaining gates

See the [install and verification guide](25-install-and-verification.md). The bundle is private development output with `source_license: NOASSERTION`, not an approved redistribution. Only native macOS arm64 and Linux x86_64 GNU targets are accepted by the packager. The existing CI matrix uses the [documented runner labels, R33](13-sources.md#r33), and now runs instrumentation plus package/fresh-prefix checks after acceptance. That workflow has been authored, not remotely executed in this task; a Linux artifact/result is therefore pending.

The [local packaging record](../research/results/phase-six/packaging-macos-arm64.json) records the archive hash and target. The local macOS package passes byte-identical assembly from identical payloads, manifest/checksum validation, safe archive checks and scan/explain/hook install/uninstall from a fresh prefix with a minimal PATH. This is not an independent compiler-reproducibility test or a fresh machine. Archive verification is data-only and never executes an arbitrary downloaded binary. Tests reject traversal, links, unlisted/tampered data, unsafe permissions, excessive member sizes and false release/model claims.

Before public release: decide project/corpus licences and naming, complete native/OS patch and notice-obligation review, verify Linux CI and compatibility, independently reproduce builds, obtain suitable signatures/notarization and establish trusted checksum distribution, and complete independent label/release review. No archive is uploaded or published by these scripts or workflow steps. Phase Six remains constrained by these gates.
