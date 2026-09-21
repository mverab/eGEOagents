## ADDED Requirements

### Requirement: Evidence-backed gap results
The system SHALL evaluate imported AI answers and source content against a target page, preserve provenance, and return typed relevance, support, coverage, and abstention results. It SHALL NOT equate model confidence with future citation probability.

#### Scenario: Insufficient evidence
- **WHEN** source extraction fails or evidence cannot support a comparison
- **THEN** the result marks the comparison insufficient and does not invent a gap or publish a correction.

### Requirement: Shared backend result contract
The system SHALL expose structured run results for CLI and visual consumption, including evidence identifiers, source URLs, capture timestamps, actual model version, assessment statuses, and available measured usage/timing. Proposed changes SHALL require approval and SHALL NOT be applied automatically.

#### Scenario: Visual inspection
- **WHEN** a viewer loads an exported backend result
- **THEN** its verdicts and evidence match that result without a separate UI scoring implementation.

### Requirement: Mandatory local-only visual demo
The delivery workflow SHALL include a local visual demo for recording, separate from the distributed product. Its source and dependencies SHALL live outside the repository and SHALL NOT be included in the product PR, package, or deployment. Only this requirement and its acceptance criteria belong in the product specification.

#### Scenario: Evidence comparison demo
- **WHEN** the user opens a completed run in the local viewer
- **THEN** the viewer shows query, target page, answer provenance, cited sources, grouped findings, and exact source/target fragments side by side
- **AND** an available proposed change can be inspected as a diff without applying or publishing it.

#### Scenario: Recorded replay
- **WHEN** a previously captured run is replayed for recording
- **THEN** the viewer prominently labels replay mode and capture time
- **AND** any playback animation is not presented as measured live execution time.

#### Scenario: Live evaluation
- **WHEN** the demo indicates that Jev evaluation is live
- **THEN** it uses actual backend execution, keeps credentials out of the browser, and displays failures honestly without substituting fixture results.

#### Scenario: Metrics and completion
- **WHEN** the demo displays duration, consumption, or cost
- **THEN** these derive from recorded run measurements and documented pricing assumptions, with unavailable values labeled unknown
- **AND** demo acceptance requires exercised real evidence and evaluator output, not a mockup alone.
