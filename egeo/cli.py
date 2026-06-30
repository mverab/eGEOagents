"""The standalone ``egeo`` command-line interface.

Runtime-agnostic entry point for the GEO pipeline. Subcommands:

- ``optimize <file>``     analyze → rank → rewrite → index a local file.
- ``evaluate``            thin wrapper over ``geo_eval.evaluate``.
- ``optimize-prompts``    thin wrapper over ``geo_eval.optimize`` (meta-optimizer).
- ``runtimes``            list available runtimes and their status.

Everything honors ``GEO_EVAL_MOCK=1`` (via ``llm_client.get_client``), so the
CLI runs offline in CI without an API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, repo_root

_DEFAULT_PROMPTS = str(repo_root() / "prompts")


def _add_evaluate_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("evaluate", help="Evaluate prompt quality on a dataset (wraps geo_eval.evaluate).")
    p.add_argument("--dataset", required=True)
    p.add_argument("--prompts", default=_DEFAULT_PROMPTS)
    p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--verbose", action="store_true")


def _add_optimize_prompts_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "optimize-prompts",
        help="Meta-optimize the rewriter prompt (wraps geo_eval.optimize; non-destructive by default).",
    )
    p.add_argument("--train", required=True)
    p.add_argument("--val", required=True)
    p.add_argument("--prompts", default=_DEFAULT_PROMPTS)
    p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    p.add_argument("--meta-model", default=os.environ.get("META_MODEL", "gpt-4o"))
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--iters", type=int, default=5)
    p.add_argument(
        "--apply",
        action="store_true",
        help="Overwrite the working rewriter prompt in place (default: write *.candidate.txt).",
    )


def _add_optimize_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("optimize", help="Run the GEO pipeline on a local content file.")
    p.add_argument("input", help="Path to a local content file (Markdown/text).")
    p.add_argument("--out-dir", default="geo-output", help="Output directory (default: geo-output).")
    p.add_argument("--query", default=None, help="Search query to rank against (default: derived from the title).")
    p.add_argument(
        "--schema-type",
        default="Article",
        choices=["Organization", "Product", "Service", "Article", "FAQPage"],
        help="JSON-LD schema template to emit (default: Article).",
    )
    p.add_argument("--runtime", default="python", help="Runtime to use (default: python).")
    p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--json", action="store_true", help="Print only the machine-readable JSON summary.")


def _add_runtimes_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("runtimes", help="List available runtimes and their status.")
    p.add_argument("--json", action="store_true", help="Print machine-readable JSON.")


def _cmd_evaluate(args: argparse.Namespace) -> int:
    import geo_eval

    summary = geo_eval.evaluate(
        dataset_path=Path(args.dataset),
        prompts_dir=Path(args.prompts),
        ranker_model=args.ranker_model,
        rewriter_model=args.rewriter_model,
        temperature=args.temperature,
        seed=args.seed,
        limit=args.limit,
        verbose=args.verbose,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _cmd_optimize_prompts(args: argparse.Namespace) -> int:
    import geo_eval

    res = geo_eval.optimize(
        train_path=Path(args.train),
        val_path=Path(args.val),
        prompts_dir=Path(args.prompts),
        ranker_model=args.ranker_model,
        rewriter_model=args.rewriter_model,
        meta_model=args.meta_model,
        temperature=args.temperature,
        seed=args.seed,
        iters=args.iters,
        apply=args.apply,
    )
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0


def _cmd_optimize(args: argparse.Namespace) -> int:
    from .pipeline import optimize_content
    from .runtimes import get_runtime

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    content = input_path.read_text(encoding="utf-8")
    runtime = get_runtime(
        args.runtime,
        ranker_model=args.ranker_model,
        rewriter_model=args.rewriter_model,
        temperature=args.temperature,
    )
    if not runtime.executes_in_process:
        print(
            f"ERROR: runtime '{runtime.name}' does not execute in-process. "
            f"Use --runtime python, or run the pipeline inside Claude Code.",
            file=sys.stderr,
        )
        return 2

    result = optimize_content(
        runtime=runtime,
        content=content,
        source=str(input_path),
        output_dir=Path(args.out_dir),
        query=args.query,
        schema_type=args.schema_type,
    )

    if args.json:
        print(json.dumps(result.summary(), indent=2, sort_keys=True))
        return 0

    delta = result.rank_improvement
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    print(f"✓ Optimized: {result.title}")
    print(f"  Runtime:     {result.runtime}")
    print(f"  GEO score:   {result.analysis.total_score}/100")
    print(f"  Rank:        #{result.rank_before} → #{result.rank_after} ({delta_str})")
    print(f"  Output dir:  {result.output_dir}")
    for path in result.written_files:
        print(f"   - {path}")
    return 0


def _cmd_runtimes(args: argparse.Namespace) -> int:
    from .runtimes import runtime_status

    infos = runtime_status()
    if args.json:
        print(json.dumps([info.__dict__ for info in infos], indent=2, sort_keys=True))
        return 0

    print("Supported runtimes:\n")
    for info in infos:
        status = "available" if info.available else "unavailable"
        mode = "in-process" if info.executes_in_process else "host-executed"
        aliases = f" (aliases: {', '.join(info.aliases)})" if info.aliases else ""
        print(f"• {info.name}{aliases}")
        print(f"    status: {status} | mode: {mode}")
        print(f"    {info.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="egeo",
        description="E-GEO: runtime-agnostic Generative Engine Optimization CLI.",
    )
    parser.add_argument("--version", action="version", version=f"egeo {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_optimize_parser(sub)
    _add_evaluate_parser(sub)
    _add_optimize_prompts_parser(sub)
    _add_runtimes_parser(sub)
    return parser


_DISPATCH = {
    "optimize": _cmd_optimize,
    "evaluate": _cmd_evaluate,
    "optimize-prompts": _cmd_optimize_prompts,
    "runtimes": _cmd_runtimes,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH[args.cmd]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
