## ADDED Requirements

### Requirement: Optimize Outputs Carry No Aggregate Score

`egeo optimize` SHALL NOT print or write a single aggregate GEO score. The CLI output, `report.md`, `analysis.json` and the `--json` summary SHALL present the ten analyzer signals individually, labeled as a keyword heuristic that is not a ranking score.

#### Scenario: CLI output

- **WHEN** `egeo optimize` finishes
- **THEN** the output states how many of the ten signals were detected and names the ones not found
- **AND** it contains no score out of 100

#### Scenario: Machine-readable outputs

- **WHEN** `analysis.json` and the `--json` summary are written
- **THEN** neither contains `total_score` or `geo_score`
- **AND** the ten per-signal values are present
