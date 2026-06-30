# Tasks: Harden Quality Gates and Expose the Evaluation Harness

## 1. Evaluation Harness Hardening

- [ ] 1.1 Add a deterministic, env-gated `MockClient` in `llm_client.py` (enabled by `GEO_EVAL_MOCK=1`).
- [ ] 1.2 Route `get_client()` to `MockClient` when the flag is set; otherwise use the real client.
- [ ] 1.3 Ensure the mock returns schema-correct objects for ranker, rewriter, and meta-optimizer roles.
- [ ] 1.4 Make `optimize` non-destructive: write to `rewriter_user.candidate.txt` by default.
- [ ] 1.5 Add an `--apply` flag to `optimize` to overwrite the working prompt in place.
- [ ] 1.6 Create `eval/datasets/geo_smoke.jsonl` with 5-10 examples (query, candidates, target_id).
  - Depends on: 1.1-1.3 (so the dataset is exercised by the mock).

## 2. Python Validators

- [ ] 2.1 Create `scripts/validate_skills.py` validating SKILL.md frontmatter (name, description) and unique names.
- [ ] 2.2 Create `scripts/validate_jsonld.py` validating JSON-LD structure with `jsonschema`.
- [ ] 2.3 Confirm validators exit non-zero on failure (CI-gating).

## 3. JSON-LD Templates

- [ ] 3.1 Create `geo-output/schema/Organization.json`.
- [ ] 3.2 Create `geo-output/schema/Product.json`.
- [ ] 3.3 Create `geo-output/schema/Service.json`.
- [ ] 3.4 Create `geo-output/schema/Article.json`.
- [ ] 3.5 Create `geo-output/schema/FAQPage.json`.
- [ ] 3.6 Ensure all templates pass `scripts/validate_jsonld.py`.
  - Depends on: 2.2.

## 4. Continuous Integration

- [ ] 4.1 Create `.github/workflows/ci.yml`.
- [ ] 4.2 Add SKILL.md frontmatter validation step.
- [ ] 4.3 Add JSON-LD validation step (templates + example output).
- [ ] 4.4 Add deprecated-slug link-check step (fails on `egeo-claude-agents`).
- [ ] 4.5 Add non-blocking skills.sh parser smoke test (`npx skills add <repo> --list`).
- [ ] 4.6 Add `evaluate --limit 5` step with `GEO_EVAL_MOCK=1`.
  - Depends on: 1.1-1.6, 2.1-2.2, 3.1-3.6.

## 5. Monthly QA Gate

- [ ] 5.1 Create `.github/workflows/qa-monthly.yml` on a monthly schedule.
- [ ] 5.2 Add parser validation, dead-link scan, metadata completeness, and release/tag freshness steps.

## 6. Documentation

- [ ] 6.1 Create `docs/evaluation.md` (dataset format, commands, metrics, proxy limitation).
- [ ] 6.2 Link `docs/evaluation.md` from `README.md` documentation table.
- [ ] 6.3 Add a "Reproducible results" section and a CI badge to `README.md`.
  - Depends on: 4.1.

## 7. Release Notes

- [ ] 7.1 Create `CHANGELOG.md` with a `v1.1.0` entry summarizing all changes.

## 8. Validation

- [ ] 8.1 Run `evaluate` and `optimize` locally with `GEO_EVAL_MOCK=1`.
- [ ] 8.2 Run both validators against the repository.
- [ ] 8.3 Confirm `prompts/rewriter_user.txt` is unchanged after a default `optimize` run.
