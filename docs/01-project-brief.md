# Project brief

Date: 5 November 2026. Owner: Richard Waters. Working name: Veil Guard.

## Overview

**Evidence and scope.** A 2019 peer-reviewed study documented credential leakage in public GitHub repositories ([R01](13-sources.md#r01)). A 2025 master's thesis explores heuristic and ML approaches to secret detection ([R02](13-sources.md#r02)). These motivate investigation; they establish neither current prevalence nor Veil Guard's effectiveness. Prioritising ambiguous reviews is our proposed intervention.

An offline native CLI for inspecting staged Git changes and triaging possible hard-coded credentials. It fits in a developer terminal, an explicitly installed pre-commit hook and later CI. It targets a workflow problem to be validated with consenting developers: deciding which ambiguous secret-scanning findings merit attention before code leaves the developer's machine.

## Intended users and scenario

A developer stages a configuration file containing an unfamiliar service credential beside a fake example token. In the proposed implementation, Veil Guard would check the exact staged content, emit a redacted high-confidence warning where a rule applies, and rank generic candidates. The developer opens their own editor at the location and decides how to remediate. A reviewer can inspect numerical similarity to safe training exemplars without seeing the candidate value in tool output.

Small engineering teams and maintainers are the initial audience. Enterprise fleet management, SOC workflows and central dashboards are outside the first release.

## Aim

Test whether eight explicit numeric features plus KNN can improve review ordering while preserving deterministic scanner findings and keeping proprietary source local.

## Objectives

1. Build a portable native CLI with no network requirement at scan time.
2. Correctly scan added/modified staged text, even where the working tree differs.
3. Keep all high-confidence rule findings visible regardless of model output.
4. Produce feature-level explanations and an explicit review/abstention state.
5. Measure ranking usefulness against a rule-only baseline and simple statistical baselines.
6. Publish a reproducible, safe demonstration and limitations.

## Deliverables

Rust source and release binaries; offline Python experiment code; a versioned eight-feature extractor; ethical synthetic corpus recipes; a non-executable model format; redacted text/JSON reports; tests; benchmark report; data/model cards; installation and remediation guidance; a 90–120 second terminal video.

## Definition of done

A fresh supported machine can run an offline scan using a packaged model. Integration tests show exact-index scanning, robust failure behaviour, no repository execution and no candidate-value output. Model export matches the Python reference. Evaluation states sample sizes, grouped splits, uncertainty and failed cases. A release is useful as a scanner even if KNN shows no benefit; in that case its AI remains experimental and the result is published candidly.

## Non-goals

Credential validation by calling providers; use of stolen, breached or live credentials; scanning third-party repositories without permission; password cracking; exploitation; automatic rotation or file edits; collecting developer code for training; web apps; replacing an organisation's security programme.

## Expected outcome

An installable developer security utility and a credible portfolio case study combining systems programming, defensive security and applied linear algebra. Expected benefits are hypotheses until measured. No claim of complete leak prevention, guaranteed detection or novel invention of secret scanning.
