# Change: Regroup four over-long `citation-gap-fixing` requirements

## Why

`openspec validate --all --strict` fails on `citation-gap-fixing`: four requirements exceed 500 characters (1,693, 1,014, 929 and 560). Each mixes several behaviors, which makes them hard to review and to cite.

## What Changes

- Spec only. Every normative sentence is kept word for word: a script cut the existing text at sentence boundaries and asserted that nothing was lost. No sentence is reworded, added or dropped.
- "Report And Re-Measure List" is removed and regrouped into six requirements, each with the existing scenarios that belong to it.
- "Diagnosis Against Real Cited Sources", "Section Mode Fails Closed Without Jev" and "Jev Selection Is Validated Against A Live Engine" keep their name, their first sentences and all their scenarios; the rest of each moves to new requirements.
- New requirements need at least one scenario. Eleven scenarios are added; each restates a sentence of its own requirement and adds no new behavior.

## Impact

- Affected spec: `citation-gap-fixing` (3 modified, 1 removed, 11 added requirements). No code, test, prompt, threshold or documentation change.
- The pre-registered Jev validation (`eval/jev_selection/PREREG-v4.md`) is not touched, and the text describing the gate, the pre-registration rule and the no-re-tuning rule is unchanged.
- After archiving, `openspec validate --all --strict` passes for every spec.
