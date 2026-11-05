# Ethics, privacy and threat model

## Authorised purpose

**Evidence and responsibility.** OWASP informs secret lifecycle/logging considerations ([R20](13-sources.md#r20)); official persistence guidance informs the executable-deserialisation threat ([R19](13-sources.md#r19)). The threat table, authorisation boundary and privacy commitments are our proposed controls. They are neither audited guarantees nor a claim of legal/compliance certification.

Defensive analysis of local repositories the user owns or has explicit permission to inspect. The tool helps prevent accidental disclosure and supports human review. No offensive module, external scanning, provider credential validation, credential use or exploitation is planned.

## Assets and adversaries

Assets: source bytes, possible credentials, repository paths, developer decisions, training integrity and release trust.
Adversaries: malicious repository authors, tampered model distributors, accidental logging, poisoned examples, unsafe hook installation and a locally compromised machine. Host compromise is outside what this tool can solve. The [repository/automation policy](17-repository-and-automation.md) records the implemented preflight restrictions and explains why metadata checks are not race-proof filesystem confinement.

## Threats and mitigations

| Threat | Mitigation / residual risk |
| --- | --- |
| Candidate leaks in logs/reports | Redact before output; no raw snippets/value fragments; capture-output privacy tests; local RAM/crash-dump exposure remains |
| Repository runs code during scan | Object/index reading only; disable filters/external diff/textconv; never invoke hooks or shell commands from repository text |
| Path traversal/symlinks | Read object bytes; no symlink target following; validate report destination and repository boundaries |
| Terminal injection | Escape control bytes in paths, rule text and errors; test malicious filenames |
| Malicious oversized input | Bounded regex/parser, blob/model/candidate/time caps; incomplete scan status |
| Malicious model file | Strict bounded JSON; reject non-finite/wrong-shaped data; no deserialised executable objects |
| Training poisoning | Approved synthetic recipes, reviewed provenance, no auto-learning, versioned signed release process later |
| False clearance | Keep all rule findings; abstain for uncertain generic inputs; MVP model cannot suppress/block |
| False positive overload | Explain/rank findings, benchmark hard negatives, use narrow reviewed suppressions later |
| Unsafe remediation | Advice only; no source rewrite, automatic rotation or deletion |
| Supply-chain compromise | Lock dependencies, audit licences/security, versioned release manifests; signatures before trusted automatic model updates |
| Report exposes sensitive paths | Relative escaped paths; explicit output, restrictive permissions and documented retention |

## Privacy commitments

No runtime telemetry, analytics, remote model calls, provider validation, content upload or hidden training ingestion. No secret hashes as identifiers. Current filename displays scrub observed candidate values and withhold all paths when a scan is incomplete; see the [candidate/report privacy contract](16-candidate-and-report-contract.md). This is not anonymisation. Numerical features are not guaranteed anonymisation; default reports show distance contributions rather than raw vectors. Safe exemplar IDs refer only to the approved lab corpus.

No plaintext source copied into diagnostic archives. Error reporting must not include input buffers. Avoid logging environment variables. Do not scan the user's whole home directory or unrelated repositories.

## Human control and policy

Hook install/uninstall is a deliberate command, never a side effect of scan. It must preserve existing hooks and track only what Veil Guard installed. Local execution cannot enforce organisation-wide policy against a determined developer; hooking is convenience, not tamper-proof enforcement.

Keep uncertainty visible. A model's benign vote cannot certify safety. Any later blocking policy requires independent evidence, configurable documented criteria and an explicit user/team decision.

## Safe development and demonstration

Use disposable fixture repositories containing authored nonfunctional values only. Never demonstrate by publishing a real credential and hoping to revoke it later. Do not enable broad ignore rules to make fixture tests pass; scope fixtures and document them.

If an actual secret is encountered accidentally: do not reproduce it in issues, screenshots or training data. Notify its owner through an authorised private channel and follow the provider's rotation guidance. The software will not send those notifications automatically.

## Responsible claims

Say “ranked a possible credential for review” rather than “proved this key is live”. Say “tested on safe fixture repositories” rather than “protects every organisation”. Publish limitations and negative results. Ethical use guidance is a project boundary; it does not itself prevent misuse.
