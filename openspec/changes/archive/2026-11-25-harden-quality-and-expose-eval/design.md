# Design: Harden Quality Gates and Expose the Evaluation Harness

## Context

E-GEO is distributed as Claude Code skills plus a small Python evaluation
harness. Two gaps motivate this change:

1. **Quality is unenforced.** Skill frontmatter, JSON-LD validity, and link
   integrity are checked manually, if at all. Regressions reach `main`.
2. **The harness is opaque and risky.** It needs a paid API key (so it never
   runs in CI), it destructively overwrites a tracked prompt file, and its
   metrics are undocumented.

**Stakeholders:** maintainers (CI signal), contributors (clear gates), and
users evaluating E-GEO's credibility (reproducible, honestly-scoped results).

**Constraints:** keep dependencies tiny (`pyyaml`, `jsonschema` only), no new
services, single-file scripts, and the harness must still work unchanged with a
real API key.

## Goals / Non-Goals

### Goals
- Run the full evaluate path in CI with zero secrets.
- Make `optimize` safe by default (no silent overwrite).
- Enforce SKILL.md frontmatter, JSON-LD validity, and link integrity on every PR.
- Document evaluation honestly (proxy metric, not real engine ranking).

### Non-Goals
- A real schema.org semantic validator (we do structural validation only).
- Measuring real ChatGPT/Perplexity rankings (out of scope; explicitly a proxy).
- Replacing the OpenAI-compatible client or changing prompt contents.

## Decisions

### 1. Env-gated deterministic MOCK client

**Decision:** Add `MockClient` in `llm_client.py`, selected by `get_client()`
when `GEO_EVAL_MOCK` is truthy (`1/true/yes/on`).

The mock infers its role from the **system prompt** and returns schema-correct
JSON:

| Role | Detection (system prompt) | Output |
|------|---------------------------|--------|
| Meta-optimizer | `meta-optimizer` / `new_prompt` | `{"new_prompt", "rationale"}` |
| Ranker | `re-ranking` / `ordered_ids` | `{"ordered_ids", "notes"}` |
| Rewriter | `rewrit` | `{"rewritten_description"}` |

Role order matters: the meta-optimizer system prompt also contains "rewriting",
so it is matched first.

The ranker scores candidates by `(has "Best for" marker, description length,
id)`. The rewriter prepends a `Best for ...` line and appends a scannable
closing line. Therefore a rewritten target reliably gains the marker bonus and
moves up, producing a **deterministic positive** `avg_rank_improvement`. This
exercises the entire evaluate/optimize code path without network access.

**Alternatives considered:**
- *Record/replay fixtures*: rejected — brittle and heavy for a smoke test.
- *Skip CI evaluation entirely*: rejected — leaves the harness untested.

### 2. Non-destructive `optimize`

**Decision:** Write the optimized prompt to
`prompts/rewriter_user.candidate.txt` by default; only overwrite
`prompts/rewriter_user.txt` when `--apply` is passed. The return payload
includes `applied`, `saved_to`, and a `hint`.

**Rationale:** prevents accidental loss of the working prompt and keeps `git
diff` clean during experimentation.

### 3. Validators as single-file scripts

**Decision:** `scripts/validate_skills.py` (PyYAML) and
`scripts/validate_jsonld.py` (jsonschema). Both exit non-zero on failure so they
gate CI directly.

- `validate_skills.py`: requires a YAML frontmatter block, `name` +
  `description`, kebab-case `name`, and globally unique names.
- `validate_jsonld.py`: validates JSON parse, a minimal JSON-LD envelope schema
  (`@type` or `@graph` required), `@context` referencing schema.org, and
  iterates `@graph`/array nodes. `[FILL: ...]` placeholders are allowed because
  templates are meant to be completed by users.

**Alternatives considered:**
- *Node-based linters*: rejected — Python is already a project dependency.
- *Full schema.org validation*: rejected — too heavy; structural checks catch
  the real-world breakages (malformed JSON, missing type/context).

### 4. CI structure

**Decision:** One `quality-gates` job in `ci.yml` running on push/PR to
`main`/`release/**`. Steps: frontmatter validation, JSON-LD validation,
deprecated-slug grep (hard fail), skills.sh parser smoke test
(`continue-on-error`), and `evaluate --limit 5` with `GEO_EVAL_MOCK=1`.

The skills.sh smoke test is **non-blocking** because it depends on an external
network/tool; everything else is deterministic and offline.

`qa-monthly.yml` runs on a cron schedule and adds a dead-link scan and
release/tag freshness advisory.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Mock output diverges from real LLM behavior | Mock is for *path* coverage only; documented as such in `docs/evaluation.md`. |
| Structural JSON-LD validation misses semantic errors | Documented scope; users still run Google Rich Results Test. |
| `npx skills` unavailable in CI | Step is `continue-on-error`; local frontmatter validation still runs. |
| Deprecated-slug grep false positives | Scoped to `*.md`; the canonical name `eGEOagents` does not contain the slug. |

## Migration Plan

1. Land harness + validators + templates + workflows + docs on `release/v1.1`.
2. Verify CI green on the PR (mock evaluate, validators, link check).
3. After merge, tag `v1.1.0` so the monthly freshness check has a baseline.

Rollback: the change is additive except for the `optimize` behavior change;
reverting the `optimize` diff restores the old in-place write.

## Open Questions

- Should `evaluate` gain a `--json-out` option to persist CI metrics as an
  artifact? (Deferred to a future change.)
