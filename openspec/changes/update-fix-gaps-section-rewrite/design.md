# Design: section-mode fix-gaps

## Flow (one page, one gap query Q)

```
source file ─ split frontmatter / sections ─┐
tracker sources for Q ─ fetch (≤6, not own domain) ─┤
                                                     ▼
              Jev Choice over {own sections ≥30 words} ∪ {fetched sources}   (diagnose)
                 │ own wins → already_best (stop)
                 │ source wins → target = own section with max probability
                 ▼
              LLM rewrites target section only                                (rewrite)
                 ▼
              code rules: heading, links, numbers, table rows, code, length   (fidelity 1)
                 ▼
              Jev Choice faithful/drops_facts/adds_claims, conf ≥ 0.6          (fidelity 2)
                 ▼
              Jev Choice again with rewritten section in place                 (verify)
                 │ worse → reject
                 ▼
              write rewritten file + diff + diagnosis.json
```

## Decisions

1. **Jev judges, the LLM writes.** Jev is never asked to generate text; the LLM is never asked to judge.
2. **One primitive for diagnosis and verification.** The same Choice question with the same candidate ids is asked before and after; only the target section's text changes. Before/after probabilities of the target id are therefore comparable.
3. **Neutral option labels.** Choice criteria values are `"The candidate whose text is candidates.<id>"`; the id prefixes (`own_`, `src_`) are never explained to the model, so it cannot prefer "our" candidates by label.
4. **Competitor text never reaches the rewriter.** The rewriter sees only the query, the page title and the target section. This prevents copying competitor claims (guardrail `no_fabricated_proof`).
5. **Rules before judge.** Deterministic checks are free and exact; the Jev fidelity judge only runs on rewrites that already passed them.
6. **Thresholds are constants in code** (`FIDELITY_GATE = 0.6`, `IMPROVE_DELTA = 0.05`, `MIN_SECTION_WORDS = 30`, `MAX_CANDIDATE_CHARS = 1500`, `DEFAULT_MAX_SOURCES = 6`), reported in `fix-gaps.json`, never tuned per run.
7. **Mock mode is explicit.** `GEO_EVAL_MOCK=1` swaps in `MockJevTransport` (word-overlap probabilities) and an identity rewriter; no network. Reports say `"jev_model": "mock"`.
8. **Frontmatter round-trip** uses the existing `pipeline._extract_frontmatter` (raw + body == original text). Section split/join is byte-exact; this is tested.
9. **Validation gate.** `eval/jev_selection` must reach mean AUC ≥ 0.65 over ≥ 6 queries before section mode is documented as verification. If it fails, section mode still ships only if the owner decides, and the report note must say the proxy is unvalidated.

## Out of scope

- Rewriting more than one section per page per run.
- Using competitor text to guide rewrites.
- Calling answer engines from `fix-gaps`.
