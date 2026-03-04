# Change: Improve skills.sh Discoverability and GitHub Visibility

## Why

As of March 3, 2026, the public footprint is good but still under-optimized for discovery and conversion:

- `skills.sh/mverab/egeoagents` shows 4 indexed skills and 52 total installs.
- The owner page `skills.sh/mverab` shows 2 sources, 5 skills, 53 total installs.
- `competitive-analysis` shows 14 weekly installs, 8 GitHub stars, first seen Feb 8, 2026.
- Security audits are already healthy (PASS in Gen Agent Trust Hub, Socket, and Snyk).
- GitHub About panel is missing key metadata (no description, no website, no topics), plus 0 tags and no releases.
- README still contains multiple links to the old repo slug (`egeo-claude-agents`) instead of `eGEOagents`.

From skills.sh docs and the official CLI/parser behavior:

- Listing/ranking is driven by installs from the `skills` CLI telemetry.
- Skills appear automatically once users run `npx skills add <owner/repo>`.
- Discovery requires valid `SKILL.md` parsing (frontmatter and structure), so publication quality directly affects indexability.

## What Changes

- Define a formal `skills-visibility` capability in OpenSpec.
- Add an execution playbook to guarantee indexability in skills.sh.
- Add a distribution playbook focused on install growth (the ranking signal).
- Add a GitHub metadata playbook for repository-level visibility.
- Add verification gates so each release cycle checks:
  - parser compatibility,
  - index presence,
  - install growth,
  - metadata completeness,
  - broken-link regressions.

## Impact

### Affected specs

- New capability: `skills-visibility`.

### Affected files (planned implementation)

- `README.md` (installation CTA and repository-link cleanup)
- Optional docs page: `docs/skills-distribution.md`
- Release/tag workflow files under `.github/` (if automated)

### External systems

- `skills.sh` listing pages
- `npx skills` install flow and telemetry
- GitHub repository metadata (About/Topics/Releases/Tags)

### Success criteria

- 100% of published skills remain parseable by `npx skills add <repo> --list`.
- Repo About section is complete (description + website + topics).
- At least one release and one tag published.
- README has no broken links to previous repo slug.
- Install trend increases over baseline (52 total installs on March 3, 2026).
