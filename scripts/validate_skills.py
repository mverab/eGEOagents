#!/usr/bin/env python3
"""Validate the YAML frontmatter of every SKILL.md in the repository.

Checks performed for each ``SKILL.md`` discovered under the repo:
  1. The file starts with a YAML frontmatter block delimited by ``---``.
  2. The frontmatter is valid YAML and parses to a mapping.
  3. Required fields ``name`` and ``description`` are present and non-empty.
  4. ``name`` is kebab-case (the format the skills.sh CLI parser expects).
  5. Skill ``name`` values are unique across the whole repository, so the
     skills.sh listing is unambiguous.

Exit code is non-zero when any check fails, so this can gate CI.

Usage:
    python scripts/validate_skills.py [--root .]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REQUIRED_FIELDS = ("name", "description")
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


def find_skill_files(root: Path) -> List[Path]:
    """Return all SKILL.md files under root, skipping the .git directory."""
    return sorted(
        p for p in root.rglob("SKILL.md") if ".git" not in p.parts
    )


def parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Extract and parse the YAML frontmatter. Returns (data, error)."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, "missing YAML frontmatter block (must start with '---')"
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return {}, f"invalid YAML frontmatter: {exc}"
    if not isinstance(data, dict):
        return {}, "frontmatter must parse to a mapping of key/value pairs"
    return data, ""


def validate_file(path: Path) -> Tuple[List[str], str]:
    """Validate a single SKILL.md. Returns (errors, skill_name)."""
    errors: List[str] = []
    text = path.read_text(encoding="utf-8")
    data, err = parse_frontmatter(text)
    if err:
        return [err], ""

    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"missing or empty required field: '{field}'")

    name = data.get("name", "")
    if isinstance(name, str) and name and not NAME_PATTERN.match(name):
        errors.append(
            f"name '{name}' is not kebab-case (lowercase letters, digits, hyphens)"
        )

    return errors, name if isinstance(name, str) else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan for SKILL.md files (default: current dir).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    skill_files = find_skill_files(root)

    if not skill_files:
        print(f"ERROR: no SKILL.md files found under {root}", file=sys.stderr)
        return 1

    total_errors = 0
    names_seen: Dict[str, Path] = {}

    for path in skill_files:
        rel = path.relative_to(root)
        errors, name = validate_file(path)

        if name:
            if name in names_seen:
                errors.append(
                    f"duplicate skill name '{name}' (also defined in "
                    f"{names_seen[name].relative_to(root)})"
                )
            else:
                names_seen[name] = path

        if errors:
            total_errors += len(errors)
            print(f"FAIL  {rel}")
            for e in errors:
                print(f"      - {e}")
        else:
            print(f"OK    {rel}  (name: {name})")

    print()
    print(
        f"Validated {len(skill_files)} skill file(s); "
        f"{len(names_seen)} unique name(s); {total_errors} error(s)."
    )
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
