# Capability: Skills Visibility

## ADDED Requirements

### Requirement: skills.sh Parse Compatibility
The repository SHALL keep every published skill compatible with the `skills` CLI parser so skills remain discoverable in skills.sh.

#### Scenario: Skill files are parseable
- **WHEN** a maintainer runs `npx skills add https://github.com/mverab/eGEOagents --list`
- **THEN** the command returns all intended skills without parser errors
- **AND** each skill includes required frontmatter fields (`name`, `description`)

#### Scenario: Duplicate names are prevented
- **WHEN** new skills are introduced across multiple agent directories
- **THEN** no two published skills share the same `name`
- **AND** the visible listing remains unambiguous on skills.sh

### Requirement: Automatic Listing Activation
The repository SHALL include explicit install instructions that trigger skills.sh telemetry-based listing.

#### Scenario: Listing activation path is documented
- **WHEN** a user opens the README
- **THEN** the user can find a copy-paste command for `npx skills add <owner/repo>`
- **AND** the command format for single-skill install is documented

#### Scenario: Post-publish verification exists
- **WHEN** a maintainer publishes a change to skills
- **THEN** the maintainer follows a verification checklist
- **AND** confirms skills appear under `skills.sh/mverab/egeoagents`

### Requirement: Install-Driven Ranking Execution
The project SHALL operate an install-growth loop because skills.sh ranking is based on aggregated install counts.

#### Scenario: Distribution is tied to install commands
- **WHEN** a skill is promoted externally
- **THEN** the promotion includes direct `npx skills add` commands
- **AND** references one concrete use case to improve conversion

#### Scenario: Weekly trend is monitored
- **WHEN** weekly metrics are reviewed
- **THEN** install deltas per skill are recorded
- **AND** the next distribution action is chosen from observed conversion

### Requirement: GitHub Visibility Completeness
The repository SHALL maintain complete GitHub metadata to improve public discoverability and trust.

#### Scenario: About panel completeness
- **WHEN** a user visits `github.com/mverab/eGEOagents`
- **THEN** the About panel includes description, website, and relevant topics

#### Scenario: Release and tag hygiene
- **WHEN** meaningful updates are shipped
- **THEN** at least one release and semantic tag are published
- **AND** release notes mention new or improved skills

### Requirement: Link Integrity for Canonical Repo
The project SHALL keep all external links aligned with the canonical repository slug.

#### Scenario: README links are canonical
- **WHEN** README links are validated
- **THEN** links point to `mverab/eGEOagents` unless intentionally external
- **AND** outdated links to `mverab/egeo-claude-agents` are removed or redirected
