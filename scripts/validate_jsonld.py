#!/usr/bin/env python3
"""Validate JSON-LD schema templates for syntactic and structural correctness.

This validator targets the JSON-LD templates shipped in ``geo-output/schema/``
(and any other path passed on the command line). It is intentionally a
*structural* validator, not a full schema.org semantic validator. It checks:

  1. The file is valid JSON.
  2. The document is a JSON object (or a list of objects, or a ``@graph``).
  3. Each JSON-LD node declares ``@context`` (top-level) and ``@type``.
  4. ``@context`` references schema.org.
  5. A jsonschema meta-validation of the minimal JSON-LD envelope, so malformed
     structures fail loudly via the ``jsonschema`` library.

``[FILL: ...]`` placeholders are allowed: templates are meant to be filled in
by users, so empty/placeholder string *values* do not fail validation.

Exit code is non-zero when any file fails, so this can gate CI.

Usage:
    python scripts/validate_jsonld.py geo-output/schema/*.json
    python scripts/validate_jsonld.py --dir geo-output/schema
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover - dependency guard
    print("ERROR: jsonschema is required. Install with: pip install jsonschema", file=sys.stderr)
    sys.exit(2)

# Minimal JSON-LD envelope schema: a node must be an object that carries an
# @type, and may carry @context / @id / @graph. This catches gross structural
# mistakes without trying to model all of schema.org.
NODE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "@context": {"type": ["string", "object", "array"]},
        "@type": {"type": ["string", "array"]},
        "@id": {"type": "string"},
        "@graph": {"type": "array"},
    },
    "anyOf": [
        {"required": ["@type"]},
        {"required": ["@graph"]},
    ],
}

_VALIDATOR = Draft7Validator(NODE_SCHEMA)


def _context_mentions_schema_org(context: Any) -> bool:
    if isinstance(context, str):
        return "schema.org" in context
    if isinstance(context, list):
        return any(_context_mentions_schema_org(c) for c in context)
    if isinstance(context, dict):
        return any(_context_mentions_schema_org(v) for v in context.values())
    return False


def _iter_nodes(doc: Any) -> List[dict]:
    """Return the list of JSON-LD nodes to type-check (handles @graph / arrays)."""
    if isinstance(doc, list):
        return [n for n in doc if isinstance(n, dict)]
    if isinstance(doc, dict):
        if isinstance(doc.get("@graph"), list):
            return [n for n in doc["@graph"] if isinstance(n, dict)]
        return [doc]
    return []


def validate_file(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read file: {exc}"]

    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(doc, (dict, list)):
        return ["top-level JSON-LD must be an object or an array of objects"]

    # Top-level @context check (skip for bare arrays where each node carries it).
    if isinstance(doc, dict):
        if "@context" not in doc:
            errors.append("missing top-level '@context'")
        elif not _context_mentions_schema_org(doc["@context"]):
            errors.append("'@context' does not reference schema.org")

    nodes = _iter_nodes(doc)
    if not nodes:
        errors.append("no JSON-LD nodes found")

    for i, node in enumerate(nodes):
        for verr in sorted(_VALIDATOR.iter_errors(node), key=lambda e: e.path):
            loc = "/".join(str(p) for p in verr.path) or f"node[{i}]"
            errors.append(f"node[{i}] {loc}: {verr.message}")
        if "@type" not in node and "@graph" not in node:
            errors.append(f"node[{i}]: missing '@type'")

    return errors


def collect_paths(args: argparse.Namespace) -> List[Path]:
    paths: List[Path] = []
    if args.dir:
        paths.extend(sorted(Path(args.dir).glob("*.json")))
    for pattern in args.files:
        matched = [Path(p) for p in glob.glob(pattern)]
        paths.extend(matched if matched else [Path(pattern)])
    # De-duplicate while preserving order.
    seen = set()
    unique: List[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="JSON-LD files or globs to validate.")
    parser.add_argument("--dir", help="Validate every *.json file in this directory.")
    args = parser.parse_args()

    paths = collect_paths(args)
    if not paths:
        print("ERROR: no JSON-LD files specified. Pass files or --dir.", file=sys.stderr)
        return 1

    total_errors = 0
    for path in paths:
        if not path.exists():
            print(f"FAIL  {path}\n      - file not found")
            total_errors += 1
            continue
        errors = validate_file(path)
        if errors:
            total_errors += len(errors)
            print(f"FAIL  {path}")
            for e in errors:
                print(f"      - {e}")
        else:
            print(f"OK    {path}")

    print()
    print(f"Validated {len(paths)} file(s); {total_errors} error(s).")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
