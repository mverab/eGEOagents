#!/usr/bin/env python3
"""Substrate lint: enforce the contract defined in the vendored ``SUBSTRATE.md``.

Checks artifacts under ``signals/`` and ``docs/``, domain charters under
``domains/``, and the ``LOG.md`` line grammar of a substrate root — for E-GEO,
the loop workspace (``$EGEO_HOME``). Prints one ``path:line: message`` per
violation and exits 1 if there is any. Python standard library only, by design:
the frontmatter subset in SUBSTRATE.md 2 is small enough to parse by hand, and
the lint must run anywhere with no install step.

Adapted from ``scripts/substrate_lint.py`` in mverab/loopstack (the upstream
system repo that owns the contract); kept in sync when SUBSTRATE.md is re-vendored.
The only local changes are this docstring, the default root (the workspace
instead of the repo), and :func:`lint` so ``egeo loop doctor`` can call it as a
library instead of shelling out.

Usage: python3 -m egeo.substrate_lint [substrate-root]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

KINDS = ("signal", "doc")
CONFIDENCES = ("high", "medium", "low")
REQUIRED_FIELDS = ("kind", "domains", "created", "updated", "confidence", "sources")
KIND_DIRS = {"signals": "signal", "docs": "doc"}
DOMAIN_SECTIONS = ("Charter", "Cadence", "Current focus", "Backlog", "Timeline")
OUTCOMES = ("success", "partial", "failure", "no-op")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOG_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z) "
    r"\[(?P<domain>[a-z0-9][a-z0-9-]*)\] "
    r"(?P<event>[a-z0-9][a-z0-9-]*): "
    r"(?P<summary>\S.*)$"
)
OUTCOME_RE = re.compile(r"outcome=([a-z-]+)$")


class Errors:
    def __init__(self):
        self.items = []

    def add(self, path, line, message):
        self.items.append((str(path), line, message))

    def report(self):
        for path, line, message in sorted(self.items, key=lambda item: (item[0], item[1])):
            print(f"{path}:{line}: {message}")
        return 1 if self.items else 0


def split_frontmatter(text):
    """Return (fields, body_start_line, error) for a leading --- block.

    fields maps name -> (raw_value, line_number). Values are either a scalar
    string or a list of strings (inline `[a, b]` form only).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0, "missing YAML frontmatter (file must start with '---')"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, 0, "unterminated YAML frontmatter (no closing '---')"

    fields = {}
    for i in range(1, end):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            return None, i + 1, f"frontmatter line is not 'key: value': {raw.strip()!r}"
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if not key or key != raw.partition(":")[0]:
            return None, i + 1, f"frontmatter key must be unindented: {raw.strip()!r}"
        if key in fields:
            return None, i + 1, f"duplicate frontmatter field '{key}'"
        if value.startswith("["):
            if not value.endswith("]"):
                return None, i + 1, (
                    f"field '{key}': only single-line inline lists are supported "
                    f"(got {value!r})"
                )
            inner = value[1:-1].strip()
            parsed = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        else:
            parsed = value
        fields[key] = (parsed, i + 1)
    return fields, end + 2, None


def check_artifact(path, root, domains, errors):
    text = path.read_text(encoding="utf-8")
    fields, _, err = split_frontmatter(text)
    rel = path.relative_to(root)
    if err:
        errors.add(rel, 1, err)
        return

    for name in REQUIRED_FIELDS:
        if name not in fields:
            errors.add(rel, 1, f"missing required frontmatter field '{name}'")

    def get(name):
        return fields[name][0] if name in fields else None

    def line_of(name):
        return fields[name][1] if name in fields else 1

    kind = get("kind")
    if kind is not None:
        if isinstance(kind, list) or kind not in KINDS:
            errors.add(
                rel,
                line_of("kind"),
                f"field 'kind': {kind!r} is not one of {list(KINDS)} "
                f"(new kinds must be earned, see SUBSTRATE.md 6)",
            )
        else:
            expected = KIND_DIRS.get(rel.parts[0])
            if expected and kind != expected:
                errors.add(
                    rel,
                    line_of("kind"),
                    f"field 'kind': {kind!r} does not match directory "
                    f"'{rel.parts[0]}/' (expected {expected!r})",
                )

    doms = get("domains")
    if doms is not None:
        if not isinstance(doms, list) or not doms:
            errors.add(rel, line_of("domains"), "field 'domains': must be a non-empty list")
        else:
            for d in doms:
                if d not in domains:
                    errors.add(
                        rel,
                        line_of("domains"),
                        f"field 'domains': '{d}' has no directory under domains/",
                    )

    for name in ("created", "updated"):
        value = get(name)
        if value is not None and (isinstance(value, list) or not DATE_RE.match(value)):
            errors.add(rel, line_of(name), f"field '{name}': expected YYYY-MM-DD, got {value!r}")
    created, updated = get("created"), get("updated")
    if (
        isinstance(created, str)
        and isinstance(updated, str)
        and DATE_RE.match(created)
        and DATE_RE.match(updated)
        and updated < created
    ):
        errors.add(rel, line_of("updated"), f"field 'updated' ({updated}) is earlier than 'created' ({created})")

    confidence = get("confidence")
    if confidence is not None and (isinstance(confidence, list) or confidence not in CONFIDENCES):
        errors.add(
            rel,
            line_of("confidence"),
            f"field 'confidence': {confidence!r} is not one of {list(CONFIDENCES)}",
        )

    sources = get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            errors.add(rel, line_of("sources"), "field 'sources': must be a list")
        elif not sources and confidence != "low":
            errors.add(
                rel,
                line_of("sources"),
                "field 'sources': may be empty only when confidence is 'low'",
            )

    if "frequency" in fields:
        freq = get("frequency")
        if kind != "signal":
            errors.add(rel, line_of("frequency"), "field 'frequency': valid on signals only")
        elif isinstance(freq, list) or not freq.isdigit() or int(freq) < 1:
            errors.add(rel, line_of("frequency"), f"field 'frequency': expected an integer >= 1, got {freq!r}")
    elif kind == "signal":
        errors.add(rel, 1, "missing frontmatter field 'frequency' (required on signals)")


def check_domain(readme, root, errors):
    rel = readme.relative_to(root)
    lines = readme.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        errors.add(rel, 1, "domain README is a charter, not an artifact: it must have no frontmatter")

    found = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            found.append((line[3:].strip(), i + 1))
    names = [n for n, _ in found]
    for section in DOMAIN_SECTIONS:
        if section not in names:
            errors.add(rel, 1, f"missing required section '## {section}'")
    present = [n for n in names if n in DOMAIN_SECTIONS]
    expected_order = [s for s in DOMAIN_SECTIONS if s in present]
    if present != expected_order:
        errors.add(rel, 1, f"sections out of order: expected {expected_order}, got {present}")
    if present and present[-1] != "Timeline" and "Timeline" in present:
        errors.add(rel, 1, "'## Timeline' must be the last section of the domain README")

    timeline_line = next((ln for n, ln in found if n == "Timeline"), None)
    if timeline_line is not None:
        for i in range(timeline_line, len(lines)):
            if lines[i].startswith("### "):
                header = lines[i][4:].strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2} run$", header):
                    errors.add(rel, i + 1, f"timeline entry header must be '### YYYY-MM-DD run', got {header!r}")
        entries = [i for i in range(timeline_line, len(lines)) if lines[i].startswith("### ")]
        for start_index, start in enumerate(entries):
            end = entries[start_index + 1] if start_index + 1 < len(entries) else len(lines)
            body = [ln.strip() for ln in lines[start + 1:end] if ln.strip()]
            outcome = next((ln for ln in body if ln.startswith("Outcome:")), None)
            if outcome is None:
                errors.add(rel, start + 1, "timeline entry has no 'Outcome:' line")
            else:
                value = outcome[len("Outcome:"):].strip()
                if value not in OUTCOMES:
                    errors.add(
                        rel,
                        start + 1,
                        f"timeline entry Outcome: {value!r} is not one of {list(OUTCOMES)}",
                    )
                elif body[-1] != outcome:
                    errors.add(rel, start + 1, "the 'Outcome:' line must be the last line of the timeline entry")


def check_log(path, root, domains, errors):
    rel = path.relative_to(root)
    in_comment = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        stripped = line.strip()
        if in_comment:
            if stripped.endswith("-->"):
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            if not stripped.endswith("-->"):
                in_comment = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        match = LOG_RE.match(line)
        if not match:
            errors.add(
                rel,
                i + 1,
                "line does not match '<YYYY-MM-DDTHH:MMZ> [<domain>] <event>: <summary>': "
                f"{stripped!r}",
            )
            continue
        domain = match.group("domain")
        if domains and domain not in domains:
            errors.add(rel, i + 1, f"unknown domain '{domain}' (no directory under domains/)")
        outcome = OUTCOME_RE.search(match.group("summary"))
        if outcome and outcome.group(1) not in OUTCOMES:
            errors.add(rel, i + 1, f"outcome={outcome.group(1)!r} is not one of {list(OUTCOMES)}")


def lint(root) -> Tuple[List[Tuple[str, int, str]], int, int]:
    """Lint a substrate root as a library call.

    Returns ``(violations, artifact_count, domain_count)`` where each violation is
    ``(path, line, message)``. Nothing is printed, so callers such as
    ``egeo loop doctor`` can format the result themselves.
    """
    root = Path(root).resolve()
    errors = _collect(root)
    return errors.items, errors.checked, errors.domains


def _collect(root):
    errors = Errors()
    errors.checked = 0
    errors.domains = 0

    domains_dir = root / "domains"
    domains = sorted(p.name for p in domains_dir.iterdir() if p.is_dir()) if domains_dir.is_dir() else []

    for name in domains:
        readme = domains_dir / name / "README.md"
        if not readme.is_file():
            errors.add(Path("domains") / name, 1, "domain directory has no README.md charter")
        else:
            check_domain(readme, root, errors)

    checked = 0
    for kind_dir in KIND_DIRS:
        directory = root / kind_dir
        if not directory.is_dir():
            errors.add(Path(kind_dir), 1, "required substrate directory is missing")
            continue
        for path in sorted(directory.rglob("*.md")):
            check_artifact(path, root, domains, errors)
            checked += 1

    log = root / "LOG.md"
    if not log.is_file():
        errors.add(Path("LOG.md"), 1, "required global activity feed is missing")
    else:
        check_log(log, root, domains, errors)

    errors.checked = checked
    errors.domains = len(domains)
    return errors


def main(argv):
    from . import workspace

    root = Path(argv[1]).resolve() if len(argv) > 1 else workspace.resolve_home()
    errors = _collect(root)

    status = errors.report()
    if status == 0:
        print(
            f"substrate ok: {errors.checked} artifact(s), {errors.domains} domain(s), LOG.md valid"
        )
    else:
        print(f"substrate lint failed: {len(errors.items)} error(s)", file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))