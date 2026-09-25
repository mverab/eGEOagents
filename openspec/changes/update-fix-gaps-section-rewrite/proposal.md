# Change: Section-level fix-gaps with Jev diagnosis, fidelity gates and real-competitor verification

## Why

The first real `fix-gaps` run (2026-09-25, `openai/gpt-4o` via OpenRouter, E-GEO's own 5 Perplexity gaps) showed two defects in the underlying `optimize` pipeline:

1. **It summarizes instead of optimizing.** A 1,515-word comparison page came back as 379 words; the 18-project directory, its tables and its sources were replaced by one vague sentence, and marketing filler was added. Publishing it would remove what made the page citable.
2. **Its verification measures nothing on real pages.** Rank before/after compares the page against three synthetic competitor stubs. A real, detailed page is already #1 before rewriting, so every run reports `#1 → #1`.

Trackers already hand us the missing ingredient: the sources the answer engine cited *instead of* the site. And TypeSafe's Jev returns typed, cheap decisions — "which of these candidates best answers the query?" is exactly the choice an answer engine makes when it picks what to cite.

## What Changes

- `fix-gaps` gains a **section mode** (new default, `--mode sections`); the current whole-page behavior stays as `--mode page`.
- **Diagnose (Jev Choice):** for the gap query, Jev chooses among the page's own sections and the fetched text of the sources the tracker says were cited. If an own section wins, the page is reported `already_best` and nothing is rewritten. If a source wins, the own section with the highest probability is the rewrite target.
- **Rewrite only that section (LLM)** with a structure-preserving prompt; heading, links, numbers, table rows and code blocks must survive.
- **Fidelity gates:** deterministic rules in code (links, numbers, table rows, code blocks, heading, length ratio) and a Jev Choice judge (`faithful` / `drops_facts` / `adds_claims`, confidence gate 0.6). Failing either keeps the original section.
- **Verify (Jev Choice again)** with the rewritten section in place, against the same real sources. Outcomes `won` / `improved` / `no_change` / `worse`; `worse` is rejected.
- **Outputs:** the full rewritten file, a unified diff and `diagnosis.json` per page; `fix-gaps.json` carries sources, diagnosis, fidelity, verification and Jev usage.
- **Fail closed:** section mode refuses to run without `TYPESAFE_API_KEY` unless `GEO_EVAL_MOCK=1` (offline deterministic mock). No heuristic fallback ranks.
- **Validation before rollout:** `eval/jev_selection/` measures whether Jev's source choice agrees with what Perplexity actually cites (AUC over cited vs. uncited SERP results). The report cites that number; the proxy is never presented as a live engine result.

## Impact

- Capability: `citation-gap-fixing` (2 requirements modified, 7 added).
- New modules: `egeo/sections.py`, `egeo/fidelity.py`, `egeo/sources.py`, `egeo/jev.py`, `egeo/judge.py`, `egeo/section_rewriter.py`; changes in `egeo/gaps.py`, `egeo/cli.py`.
- New prompts `prompts/section_rewriter_{system,user}.txt` (+ packaged copies).
- New eval `eval/jev_selection/`.
- Network: section mode fetches up to `--max-sources` (default 6) public URLs per page and calls TypeSafe; nothing in tests touches the network.
- No change to `optimize`, `evaluate`, loop mode or the `project.yaml` schema.
