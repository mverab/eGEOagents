"""``egeo loop`` — the loop-mode surface: ``run``, ``collect``, ``doctor``, ``decide``.

Loop mode turns one-shot GEO into a continuous one: deterministic collectors
record ground truth into a per-user workspace (``$EGEO_HOME``), and an agent run
turns that data into knowledge, one bounded unit of work per wake-up.

This module is the **trigger seam**, not the loop itself. It is LLM-free by
design:

- ``egeo loop collect <serp|page>`` runs a collector pass in-process.
- ``egeo loop run <domain>`` resolves and prints the *run plan* — the charter's
  current focus, collector deltas since the last Timeline entry, and candidate
  signals — and makes sure the workspace and domain are in a valid state. The
  interpretive work is then performed by an agent runtime executing
  ``.claude/skills/geo-loop/SKILL.md`` (in Claude Code: ``/geo:loop <domain>``,
  headless: ``claude -p "/geo:loop <domain>"``).
- ``egeo loop doctor`` self-checks the workspace.
- ``egeo loop decide`` ranks exactly one next action from collector JSONL and
  the outcome ledger. It never publishes or merges.

Any scheduler drives these commands identically; Hermes cron is the reference.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import repo_root, substrate_lint, workspace

#: Collector name → module file under ``collectors/``.
COLLECTORS = {"serp": "serp.py", "page": "page.py"}

_TIMELINE_DATE_RE = re.compile(r"^### (\d{4}-\d{2}-\d{2}) run\s*$")


# --------------------------------------------------------------------------- #
# collect
# --------------------------------------------------------------------------- #
def load_collector(name: str):
    """Import a collector module from ``collectors/`` for in-process invocation."""
    if name not in COLLECTORS:
        raise KeyError(name)
    directory = repo_root() / "collectors"
    path = directory / COLLECTORS[name]
    if not path.is_file():
        raise FileNotFoundError(path)
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))  # so the module finds `_common`
    spec = importlib.util.spec_from_file_location(f"egeo_collector_{name}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load collector {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# run plan
# --------------------------------------------------------------------------- #
def parse_charter(text: str) -> Dict[str, Any]:
    """Extract the level-2 sections and Timeline entries of a domain charter."""
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    timeline_dates: List[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current == "Timeline":
            match = _TIMELINE_DATE_RE.match(line)
            if match:
                timeline_dates.append(match.group(1))
        if current:
            sections[current].append(line)

    def body(name: str) -> List[str]:
        return [line.strip() for line in sections.get(name, []) if line.strip()]

    backlog = [
        re.sub(r"^(?:\d+\.|[-*])\s*", "", line)
        for line in body("Backlog")
        if re.match(r"^(?:\d+\.|[-*])\s", line)
    ]
    return {
        "charter": " ".join(body("Charter")),
        "cadence": " ".join(body("Cadence")),
        "current_focus": " ".join(body("Current focus")),
        "backlog": backlog,
        "timeline_dates": timeline_dates,
        "last_run": timeline_dates[-1] if timeline_dates else None,
    }


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def collector_deltas(home: Path, since: Optional[str]) -> List[Dict[str, Any]]:
    """Summarize each collector stream: totals, new records since ``since``, drift.

    ``since`` is a ``YYYY-MM-DD`` date (the last Timeline entry); records with a
    ``ts`` on or after it are "fresh". Read-only.
    """
    out: List[Dict[str, Any]] = []
    data_root = home / "data"
    if not data_root.is_dir():
        return out
    for stream in sorted(data_root.glob("*/*.jsonl")):
        records = _read_jsonl(stream)
        if not records:
            continue
        fresh = [r for r in records if since is None or str(r.get("ts", "")) >= since]
        item: Dict[str, Any] = {
            "collector": stream.parent.name,
            "stream": stream.name[: -len(".jsonl")],
            "records": len(records),
            "fresh": len(fresh),
            "latest_ts": records[-1].get("ts"),
        }
        if stream.parent.name == "serp":
            positions = [r.get("target_position") for r in records]
            item["target_position"] = positions[-1]
            previous = next((p for p in reversed(positions[:-1]) if p is not None), None)
            if positions[-1] is not None and previous is not None:
                item["position_delta"] = previous - positions[-1]
        if stream.parent.name == "page":
            hashes = [r.get("content_hash") for r in records]
            item["content_changed"] = len(hashes) > 1 and hashes[-1] != hashes[-2]
            item["word_count"] = records[-1].get("word_count")
            item["jsonld_types"] = records[-1].get("jsonld_types")
        out.append(item)
    return out


def candidate_signals(deltas: List[Dict[str, Any]]) -> List[str]:
    """Observations worth interpreting, phrased for the agent — not written here.

    Deliberately conservative and mechanical: thresholds mirror loopstack
    ARCHITECTURE.md 5.3 (position move ≥3 is signal-worthy). Turning these into
    artifacts is the agent's job; this list only tells it where to look.
    """
    candidates: List[str] = []
    for item in deltas:
        if item["collector"] == "serp":
            delta = item.get("position_delta")
            if isinstance(delta, int) and abs(delta) >= 3:
                direction = "improved" if delta > 0 else "dropped"
                candidates.append(
                    f"serp/{item['stream']}: target position {direction} by {abs(delta)} "
                    f"(now {item.get('target_position')})"
                )
            elif item.get("target_position") is None and item["records"] >= 3:
                candidates.append(
                    f"serp/{item['stream']}: target absent from the top 10 across {item['records']} observations"
                )
        if item["collector"] == "page":
            if item.get("content_changed"):
                candidates.append(f"page/{item['stream']}: content hash changed since the previous pass")
            if not item.get("jsonld_types"):
                candidates.append(f"page/{item['stream']}: no JSON-LD detected on the page")
    return candidates


def build_plan(domain: str, home: Path) -> Dict[str, Any]:
    """Assemble the run plan for ``domain``. Pure read; never writes."""
    project = workspace.load_project_config(home)
    readme = workspace.domain_readme(domain, home)
    plan: Dict[str, Any] = {
        "domain": domain,
        "workspace": str(home),
        "charter_path": str(readme),
        "charter_exists": readme.is_file(),
        "project": workspace.project_summary(project, home),
    }
    if readme.is_file():
        plan.update(parse_charter(readme.read_text(encoding="utf-8")))
    plan["deltas"] = collector_deltas(home, plan.get("last_run"))
    plan["candidate_signals"] = candidate_signals(plan["deltas"])
    plan["skill"] = ".claude/skills/geo-loop/SKILL.md"
    plan["agent_command"] = f"/geo:loop {domain}"
    return plan


def _print_plan(plan: Dict[str, Any], dry_run: bool) -> None:
    mode = "DRY RUN — nothing will be written" if dry_run else "run plan"
    print(f"egeo loop run: {plan['domain']} ({mode})")
    print(f"  workspace:     {plan['workspace']}")
    project = plan.get("project", {})
    print(f"  project:       {project.get('id') or 'legacy'} ({project.get('config_source')})")
    print(f"  project stats: {project.get('active_queries', 0)} active querie(s), {project.get('active_pages', 0)} active page(s)")
    print(f"  charter:       {plan['charter_path']}")
    if not plan["charter_exists"]:
        print("  charter:       MISSING — create it (see egeo-core backlog) before running the agent")
    else:
        print(f"  cadence:       {plan.get('cadence') or '—'}")
        print(f"  current focus: {plan.get('current_focus') or '—'}")
        print(f"  last run:      {plan.get('last_run') or 'never'}")
        backlog = plan.get("backlog") or []
        print(f"  backlog:       {len(backlog)} item(s)")
        for item in backlog[:5]:
            print(f"    - {item}")

    deltas = plan["deltas"]
    print(f"  fresh data:    {sum(item['fresh'] for item in deltas)} new record(s) across {len(deltas)} stream(s)")
    for item in deltas:
        extra = ""
        if item["collector"] == "serp":
            extra = f", position {item.get('target_position')}"
            if "position_delta" in item:
                extra += f" (delta {item['position_delta']:+d})"
        elif item["collector"] == "page":
            extra = f", {item.get('word_count')} words, changed={item.get('content_changed')}"
        print(f"    - {item['collector']}/{item['stream']}: {item['fresh']}/{item['records']} fresh{extra}")

    candidates = plan["candidate_signals"]
    print(f"  candidate signals: {len(candidates)}")
    for line in candidates:
        print(f"    - {line}")

    print("  next: one unit of work, executed by the agent, not by this command:")
    print(f"    Claude Code:  {plan['agent_command']}")
    print(f'    headless:     claude -p "{plan["agent_command"]}"   # pin provider+model per job')
    print(f"    procedure:    {plan['skill']}")


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #
def diagnose(home: Path) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Check the workspace. Returns ``(problems, warnings, facts)``.

    Never prints secret values: only whether a variable is set.
    """
    problems: List[str] = []
    warnings: List[str] = []
    facts: Dict[str, Any] = {"home": str(home)}

    for name in workspace.LAYOUT_DIRS:
        if not (home / name).is_dir():
            problems.append(f"missing directory: {name}/")
    for name in (workspace.LOG_NAME, workspace.CONFIG_NAME, workspace.SUBSTRATE_NAME):
        if not (home / name).is_file():
            problems.append(f"missing file: {name}")

    config: Dict[str, Any] = {}
    try:
        config = workspace.load_config(home)
    except FileNotFoundError:
        problems.append(f"{workspace.CONFIG_NAME} not found")
    except (OSError, ValueError) as exc:
        problems.append(f"{workspace.CONFIG_NAME} does not parse: {exc}")

    if config:
        auto_apply = workspace.config_get(config, "reflect.auto_apply", None)
        facts["reflect.auto_apply"] = auto_apply
        if auto_apply not in ("never", "low_risk", "all"):
            problems.append(f"reflect.auto_apply must be never|low_risk|all, got {auto_apply!r}")
        for key in ("budgets.queries_per_day", "budgets.pages_per_day"):
            value = workspace.config_get(config, key, None)
            facts[key] = value
            if value is None:
                warnings.append(f"{key} is unset: collectors will run without a cap")
            elif not isinstance(value, int) or isinstance(value, bool) or value < 1:
                problems.append(f"{key} must be a positive integer, got {value!r}")
        facts["models"] = workspace.config_get(config, "models", {})

    project: Optional[Dict[str, Any]] = None
    try:
        project = workspace.load_project_config(home)
    except workspace.ProjectConfigError as exc:
        problems.append(str(exc))
    else:
        project_facts = workspace.project_summary(project, home)
        facts.update({f"project.{key}": value for key, value in project_facts.items()})
        if project is None:
            warnings.append("project.yaml is absent: legacy config.yaml fallback is active")

    violations, artifacts, domains = substrate_lint.lint(home)
    facts["artifacts"] = artifacts
    facts["domains"] = domains
    for path, line, message in violations:
        problems.append(f"substrate {path}:{line}: {message}")

    facts["brave_api_key_set"] = bool(os.environ.get("BRAVE_API_KEY", "").strip())
    if not facts["brave_api_key_set"]:
        warnings.append("BRAVE_API_KEY is not set: the serp collector can only run in --fixture mode")

    overrides = sorted(p.name for p in workspace.prompts_dir(home).glob("*.txt")) if workspace.prompts_dir(home).is_dir() else []
    facts["prompt_overrides"] = overrides

    repo_substrate = repo_root() / workspace.SUBSTRATE_NAME
    workspace_substrate = home / workspace.SUBSTRATE_NAME
    if repo_substrate.is_file() and workspace_substrate.is_file():
        drift = repo_substrate.read_text(encoding="utf-8") != workspace_substrate.read_text(encoding="utf-8")
        facts["substrate_drift"] = drift
        if drift:
            warnings.append(
                "workspace SUBSTRATE.md differs from the repo copy: review the contract, "
                "then replace the workspace copy to adopt it"
            )

    streams = sorted((home / "data").glob("*/*.jsonl")) if (home / "data").is_dir() else []
    facts["streams"] = len(streams)
    return problems, warnings, facts


# --------------------------------------------------------------------------- #
# command handlers
# --------------------------------------------------------------------------- #
def cmd_run(args: argparse.Namespace) -> int:
    home = workspace.resolve_home()
    if args.dry_run:
        if not workspace.exists(home):
            print(
                f"egeo loop run: {home} is not bootstrapped yet (dry run writes nothing).\n"
                "Run `egeo loop doctor` to create the workspace.",
                file=sys.stderr,
            )
            return 1
    else:
        workspace.bootstrap(home)

    try:
        plan = build_plan(args.domain, home)
    except workspace.ProjectConfigError as exc:
        print(f"egeo loop run: invalid project contract: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        _print_plan(plan, args.dry_run)
    if not plan["charter_exists"]:
        return 1
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    workspace.bootstrap(workspace.resolve_home())
    module = load_collector(args.collector)
    argv = list(args.collector_args)
    if argv and argv[0] == "--":  # argparse.REMAINDER keeps the separator
        argv = argv[1:]
    return int(module.main(argv))


def cmd_doctor(args: argparse.Namespace) -> int:
    home = workspace.resolve_home()
    summary = workspace.bootstrap(home)
    problems, warnings, facts = diagnose(home)

    if args.json:
        print(
            json.dumps(
                {
                    "bootstrapped_now": summary["bootstrapped"],
                    "created": summary["created"],
                    "facts": facts,
                    "warnings": warnings,
                    "problems": problems,
                    "ok": not problems,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if problems else 0

    print(f"egeo loop doctor — {facts['home']}")
    if summary["bootstrapped"]:
        print(f"  bootstrapped now: {', '.join(summary['created'])}")
    else:
        print("  workspace: already present (bootstrap left it untouched)")
    print(f"  substrate: {facts.get('artifacts', 0)} artifact(s), {facts.get('domains', 0)} domain(s), "
          f"{facts.get('streams', 0)} data stream(s)")
    print(f"  budgets:   queries/day={facts.get('budgets.queries_per_day')} "
          f"pages/day={facts.get('budgets.pages_per_day')}")
    print(f"  project:   {facts.get('project.id') or 'legacy'} ({facts.get('project.config_source', 'unknown')})")
    print(f"  targets:   queries={facts.get('project.active_queries', 0)} pages={facts.get('project.active_pages', 0)}")
    print(f"  reflect:   auto_apply={facts.get('reflect.auto_apply')}")
    print(f"  BRAVE_API_KEY: {'set' if facts.get('brave_api_key_set') else 'not set'}")
    overrides = facts.get("prompt_overrides") or []
    print(f"  prompt overrides: {', '.join(overrides) if overrides else 'none (repo defaults in use)'}")
    for warning in warnings:
        print(f"  WARN: {warning}")
    for problem in problems:
        print(f"  FAIL: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s) found.", file=sys.stderr)
        return 1
    print("OK: workspace is healthy.")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    from . import decide

    home = workspace.resolve_home()
    if args.dry_run:
        if not workspace.exists(home):
            print(
                f"egeo loop decide: {home} is not bootstrapped yet (dry run writes nothing).\n"
                "Run `egeo loop doctor` to create the workspace.",
                file=sys.stderr,
            )
            return 1
    else:
        workspace.bootstrap(home)
    try:
        project = workspace.load_project_config(home)
    except workspace.ProjectConfigError as exc:
        print(f"egeo loop decide: invalid project contract: {exc}", file=sys.stderr)
        return 1
    if project is None:
        print(
            "egeo loop decide: project.yaml is required. Copy examples/project.yaml "
            "into $EGEO_HOME and fill the active project's identity and targets.",
            file=sys.stderr,
        )
        return 1
    action = decide.rank_action(home, project)
    payload: Dict[str, Any] = {"action": action, "dry_run": bool(args.dry_run), "workspace": str(home)}
    if not args.dry_run:
        payload.update(decide.apply_decision(home, project, action))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(f"egeo loop decide: {action['kind']} ({'DRY RUN' if args.dry_run else 'recorded'})")
        print(f"  reason:    {action['reason']}")
        print(f"  next_gate: {action['next_gate']}")
        print(f"  auto_apply: {action['auto_apply']}")
        if action.get("query_ids"):
            print(f"  queries:   {', '.join(action['query_ids'])}")
        if action.get("page_ids"):
            print(f"  pages:     {', '.join(action['page_ids'])}")
        if action.get("evidence"):
            print(f"  evidence:  {', '.join(action['evidence'])}")
        if payload.get("written"):
            print(f"  wrote:     {', '.join(payload['written'])}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def add_parser(sub: argparse._SubParsersAction) -> None:
    """Register the ``loop`` subcommand group on the ``egeo`` parser."""
    parser = sub.add_parser(
        "loop",
        help="Loop mode: collectors, run plans, workspace health, and decisions ($EGEO_HOME).",
        description=(
            "Loop mode keeps state in a per-user workspace ($EGEO_HOME, default ~/.egeo). "
            "These commands are the scheduler seam and make zero LLM calls: `collect` gathers "
            "ground truth, `run` resolves the plan for one unit of work, `doctor` checks the "
            "workspace, `decide` ranks one next action from collector data and the outcome ledger. "
            "The interpretive loop run itself is executed by an agent runtime via "
            ".claude/skills/geo-loop/SKILL.md (`/geo:loop <domain>`)."
        ),
    )
    loop_sub = parser.add_subparsers(dest="loop_cmd", required=True)

    run = loop_sub.add_parser(
        "run",
        help="Resolve and print the run plan for one domain (the agent does the work).",
        description=(
            "Prints the domain's current focus, collector deltas since its last Timeline entry, "
            "and candidate signals, then names the agent command that performs the unit of work. "
            "With --dry-run nothing is written at all."
        ),
    )
    run.add_argument("domain", help="Domain directory name under $EGEO_HOME/domains/.")
    run.add_argument("--dry-run", action="store_true", help="Print the plan and write nothing (not even bootstrap).")
    run.add_argument("--json", action="store_true", help="Print the plan as JSON.")
    run.set_defaults(loop_handler=cmd_run)

    collect = loop_sub.add_parser(
        "collect",
        help="Run one deterministic collector pass (no LLM calls).",
        description=(
            "Runs a collector in-process against $EGEO_HOME. Every argument after the collector "
            "name is forwarded to it verbatim, so `--fixture`, `--json`, `--query` and `--url` "
            "behave exactly as when running collectors/<name>.py directly; "
            "`egeo loop collect serp --help` shows them."
        ),
    )
    collect.add_argument("collector", choices=sorted(COLLECTORS), help="Collector to run.")
    collect.add_argument(
        "collector_args",
        nargs=argparse.REMAINDER,
        metavar="...",
        help="Arguments forwarded to the collector (e.g. --fixture PATH, --query Q, --url URL, --json).",
    )
    collect.set_defaults(loop_handler=cmd_collect)

    doctor = loop_sub.add_parser(
        "doctor",
        help="Bootstrap if needed, then self-check the workspace (layout, config, substrate, budgets).",
    )
    doctor.add_argument("--json", action="store_true", help="Print the diagnosis as JSON.")
    doctor.set_defaults(loop_handler=cmd_doctor)

    decide_p = loop_sub.add_parser(
        "decide",
        help="Rank exactly one next action from collector data and the outcome ledger (no LLM, never publishes).",
        description=(
            "Reads project.yaml, collector JSONL, and data/outcomes/ledger.jsonl, then ranks one "
            "action. Without --dry-run it may append one ledger row, one proposal doc, and one LOG "
            "line. It never sets status=applied, never edits the site, and never opens a PR."
        ),
    )
    decide_p.add_argument("--dry-run", action="store_true", help="Print the ranked action and write nothing.")
    decide_p.add_argument("--json", action="store_true", help="Print the decision as JSON.")
    decide_p.set_defaults(loop_handler=cmd_decide)


def main(args: argparse.Namespace) -> int:
    """Dispatch a parsed ``egeo loop ...`` namespace."""
    return int(args.loop_handler(args))


__all__ = ["add_parser", "main", "build_plan", "diagnose", "load_collector", "parse_charter", "cmd_decide"]
