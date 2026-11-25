## Context

`$EGEO_HOME/config.yaml` currently mixes loop machinery with project-specific collector inputs. `egeo loop run <domain>` also depends on a manually maintained domain charter. The reusable boundary should be explicit and inspectable before any agent interprets data.

## Goals / Non-Goals

- Goals:
  - Make one project portable by changing data, not Python code.
  - Give every tracked query and URL an owner, purpose, and stable ID.
  - Reject ambiguous query/page ownership before collection.
  - Preserve existing workspaces and one-shot CLI behavior.
  - Keep project state outside the public repository.
- Non-goals:
  - Automatically publish content or merge PRs.
  - Replace the substrate, domain charters, or append-only collector data.
  - Add a database, external service, or new paid API.
  - Infer project configuration from the web at runtime.

## Decisions

### File boundary

`$EGEO_HOME/project.yaml` is the active project's declarative contract. A separate `$EGEO_HOME` is the portability unit for each project. `config.yaml` remains the loop runtime contract.

### Contract shape

```yaml
schema_version: 1
project:
  id: egeoagents
  name: E-GEO
  repository: https://github.com/mverab/eGEOagents
  canonical_domain: egeoagents.com
  canonical_url: https://egeoagents.com/
  language: en

queries:
  - id: generic-geo-evaluation
    text: GEO evaluation harness open source
    class: generic
    intent: evaluation
    target_pages: [docs-evaluation]
    active: true

pages:
  - id: docs-evaluation
    url: https://egeoagents.com/docs/evaluation/
    purpose: product-capability
    canonical: true
    active: true

measurement:
  engines: [google-search-console, perplexity]
  cadence: weekly

guardrails:
  no_duplicate_query_owners: true
  no_auto_publish_visible_copy: true
  no_fabricated_proof: true
  require_fresh_crawl_before_verdict: true
```

The implementation may add fields, but these fields and invariants are the stable v1 contract.

### Precedence and migration

- If `project.yaml` exists and validates, collectors read its `project.canonical_domain`, `queries`, and `pages`.
- Explicit CLI flags remain highest precedence.
- If no `project.yaml` exists, current `config.yaml` fields continue to work unchanged.
- Doctor reports the compatibility fallback so a user knows the workspace is not yet portable.
- Invalid `project.yaml` fails closed; it must not silently fall back to stale project data.

### Validation

Validation is deterministic and LLM-free. It checks schema version, required identity fields, URL/domain consistency, unique IDs, non-empty active query text, valid query classes, page references, and the anti-spam/canibalization guardrails. It never calls a search engine and never writes project artifacts.

## Risks / Trade-offs

- Two config files can confuse users during migration → doctor prints the active source and fallback status; docs show the boundary.
- A project contract can become stale → every measurement record retains its query/page IDs and the loop reports stale active targets rather than inventing replacements.
- A strict schema can block old workspaces → compatibility fallback remains until project.yaml is added; no automatic destructive migration.

## Migration Plan

1. Add loader, schema validator, and example fixture.
2. Add project precedence to collectors and run-plan construction.
3. Add doctor output and tests for legacy and portable workspaces.
4. Migrate the E-GEO workspace by creating project.yaml outside the public repo.
5. Run fixture collectors and a dry-run plan for E-GEO and a second fixture project.
6. Only after verification, document `project.yaml` as the portability boundary.

## Open Questions

- None for v1. The second-project fixture can be synthetic and offline; it must not use credentials or claim live outcomes.
