# Change: Bring the `citation-gap-fixing` spec in line with page mode after #96

## Why

#96 added a fidelity gate to the `egeo optimize` pipeline, which page-mode `egeo fix-gaps` runs. The `citation-gap-fixing` spec still says page mode optimizes each page "as in version 2.1.0" and does not mention the per-page `fidelity` and `content_type` fields now written to `fix-gaps.json`. The code and tests already behave this way; only the spec is behind.

## What Changes

- Spec only. The first requirement is shortened to the command, its inputs and the mapping; its mode rules move, word for word, to a new requirement "Fix-Gaps Modes".
- The "Page mode is the default" scenario stays on the first requirement; it no longer pins version 2.1.0 and states the fidelity gate.
- New requirement: page-mode results report `content_type` and `fidelity`, and a rejected rewrite is not written under `optimized/`.

## Impact

- Affected spec: `citation-gap-fixing`. No code, test or behavior change.
- Side effect: one of the five "requirement text is very long" warnings on this spec goes away. The other four (report, diagnosis, fail-closed, Jev validation) are left as they are: splitting them means regrouping text tied to the pre-registered Jev validation, which deserves its own reviewed change.
