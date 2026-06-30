# Change: Harden Quality Gates and Expose the Evaluation Harness

## Why

E-GEO ships an evaluation harness (`geo_eval.py`, `llm_client.py`) and a set of
publishable skills, but neither has automated protection against regressions:

- The harness requires a live `OPENAI_API_KEY`, so it cannot run in CI and is
  never exercised on pull requests.
- `optimize` overwrites `prompts/rewriter_user.txt` in place, which is
  destructive and easy to trigger accidentally.
- There is no enforcement that every `SKILL.md` keeps valid, unique frontmatter,
  even though skills.sh discoverability depends on it.
- The repository advertises JSON-LD schema output, but `geo-output/schema/`
  contains only documentation — there are no validated, copy-paste templates.
- Broken links to the deprecated `egeo-claude-agents` slug can silently
  reappear, and the documented monthly QA gate is manual.
- Evaluation metrics are reported with no public documentation of what they
  mean or how to reproduce them.

## What Changes

- Add a `quality-gates` capability that defines the automated checks the project
  guarantees on every change and monthly.
- Add a deterministic, env-gated **MOCK** LLM client (`GEO_EVAL_MOCK=1`) so the
  harness runs offline in CI without API keys.
- Make `optimize` **non-destructive** by default: write to
  `rewriter_user.candidate.txt` and only overwrite the working prompt with
  `--apply`.
- Add a smoke dataset `eval/datasets/geo_smoke.jsonl` (7 examples).
- Add Python validators under `scripts/`:
  - `validate_skills.py` — SKILL.md frontmatter and unique-name validation.
  - `validate_jsonld.py` — JSON-LD structural validation via `jsonschema`.
- Add CI (`.github/workflows/ci.yml`) running frontmatter validation, JSON-LD
  validation, a deprecated-slug link check, a non-blocking skills.sh parser
  smoke test, and `evaluate --limit 5` with the MOCK client.
- Add a monthly QA workflow (`.github/workflows/qa-monthly.yml`): parser
  validation, dead-link scan, metadata completeness, and release/tag freshness.
- Add validated JSON-LD templates in `geo-output/schema/`: `Organization.json`,
  `Product.json`, `Service.json`, `Article.json`, `FAQPage.json`.
- Add `docs/evaluation.md` documenting the dataset format, commands, metrics,
  and the honest proxy-vs-real-measurement limitation; link it from `README.md`.
- Add `CHANGELOG.md` with a `v1.1.0` entry.

## Impact

### Affected specs

- New capability: `quality-gates`.

### Affected files (planned implementation)

- `llm_client.py` (MockClient + env-gated `get_client`)
- `geo_eval.py` (non-destructive `optimize`, `--apply` flag)
- `eval/datasets/geo_smoke.jsonl` (new)
- `scripts/validate_skills.py`, `scripts/validate_jsonld.py` (new)
- `.github/workflows/ci.yml`, `.github/workflows/qa-monthly.yml` (new)
- `geo-output/schema/*.json` (new templates)
- `docs/evaluation.md` (new), `README.md` (link + CI badge)
- `CHANGELOG.md` (new)

### External systems

- GitHub Actions (CI + scheduled QA)
- `skills.sh` parser (non-blocking smoke test)

### Success criteria

- `evaluate --limit 5` runs to completion in CI with `GEO_EVAL_MOCK=1` and no
  API key.
- `optimize` never modifies `prompts/rewriter_user.txt` unless `--apply` is set.
- All `SKILL.md` files pass `validate_skills.py` with unique names.
- All `geo-output/schema/*.json` templates pass `validate_jsonld.py`.
- CI fails if `egeo-claude-agents` appears in any markdown file.
- `docs/evaluation.md` documents metrics and the proxy limitation and is linked
  from the README with a CI badge and a "Reproducible results" section.
