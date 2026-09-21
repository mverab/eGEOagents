# Change: Add evidence-backed citation gap analysis

## Why
Egeo needs semantic comparison of cited sources against a target page, rather than more heuristic scores. A local visual demo is required to demonstrate evidence, abstention, and proposed improvements clearly.

## What Changes
- Propose an optional Jev evaluator for relevance, citation support, and coverage gaps, using imported AI answers with source provenance.
- Reuse the existing Python pipeline and approval gates; retain deterministic scheduling and auto_apply=false.
- Define a shared structured result consumed by CLI/report and a mandatory local-only visual demo.
- Keep the demo implementation outside the product PR and outside distributed packages. This proposal documents demo acceptance, not a supported frontend product.

## Scope Boundary
Product PR: backend evaluator, input/output contracts, tests, CLI integration, and specification. Implementation remains pending approval of the full technical contract.
Local demo: a separate local workspace outside the product repository. No frontend source, dependencies, recordings, captured datasets, or demo server enter the product PR or release. This initial PR publishes only the specification for owner review; it does not authorize implementation, merge, or deployment.

## Impact
- New capability: citation-gap (implemented on this branch; live Jev unverified).
- Expected integration: optional evaluator adjacent to existing pipeline and action ledger; do not replace deterministic decision rules.
- No SaaS, authentication, CMS integration, automatic publication, multi-engine monitoring, or production frontend.

## Status
Owner approved implementation. Backend evaluator + CLI are implemented on this branch. Local visual demo lives outside the product repository. Real TypeSafe/Jev smoke is unverified without `TYPESAFE_API_KEY`. No merge or deploy.
