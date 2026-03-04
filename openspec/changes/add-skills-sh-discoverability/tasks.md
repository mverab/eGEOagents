# Tasks: Improve skills.sh Discoverability and GitHub Visibility

## 1. Baseline and Validation

- [x] 1.1 Record current baseline from skills.sh (`skills`, `installs`, weekly installs per skill).
- [x] 1.2 Verify parser discovery with `npx skills add https://github.com/mverab/eGEOagents --list`.
- [x] 1.3 Confirm each skill has valid frontmatter (`name`, `description`; optional `allowed-tools`).
- [x] 1.4 Confirm unique skill names across all directories to avoid collisions.

## 2. skills.sh Discoverability Hardening

- [x] 2.1 Ensure all publishable skills live in supported skill paths and use `SKILL.md` filenames.
- [x] 2.2 Standardize first 1-2 description lines for clear intent and trigger phrases.
- [x] 2.3 Add a root-level install section with copy-paste commands:
  - `npx skills add https://github.com/mverab/eGEOagents`
  - `npx skills add https://github.com/mverab/eGEOagents --skill <name>`
- [x] 2.4 Add a verification section describing how to confirm the skill appears on skills.sh.

## 3. GitHub Visibility Improvements

- [ ] 3.1 Set GitHub About description with GEO + agent skills keywords.
- [ ] 3.2 Set GitHub About website URL to a canonical destination (docs/site/landing).
- [ ] 3.3 Add 8-12 relevant topics (GEO, AI search, agent skills, Claude Code, Codex, etc.).
- [ ] 3.4 Create first release and publish a semantic tag.
- [x] 3.5 Fix README links that still point to `egeo-claude-agents`.

## 4. Ranking Growth Loop (Install-Driven)

- [ ] 4.1 Publish one focused distribution post per top skill with direct install command.
- [ ] 4.2 Promote in communities where agent users already run `npx` workflows.
- [ ] 4.3 Add examples showing expected output so users install with clear intent.
- [ ] 4.4 Track weekly install deltas and document which channels convert.

## 5. Ongoing QA Gate

- [ ] 5.1 Add monthly check: parser validation + skills.sh presence + security audit status.
- [ ] 5.2 Add monthly check: GitHub metadata completeness and stale-link scan.
- [ ] 5.3 Add monthly check: releases/tags freshness and install trend report.
