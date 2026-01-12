import argparse
import json
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from llm_client import LLMError, get_client


@dataclass
class Candidate:
    id: str
    title: str
    description: str


@dataclass
class QueryExample:
    query_id: str
    query: str
    candidates: List[Candidate]
    target_id: Optional[str] = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_template(text: str, values: Dict[str, str]) -> str:
    out = text
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _format_candidates(candidates: Sequence[Candidate]) -> str:
    parts: List[str] = []
    for c in candidates:
        parts.append(
            "\n".join(
                [
                    f"- id: {c.id}",
                    f"  title: {c.title}",
                    "  description:",
                    "  " + "\n  ".join((c.description or "").splitlines()),
                ]
            )
        )
    return "\n\n".join(parts)


def _load_dataset(path: Path, limit: Optional[int] = None) -> List[QueryExample]:
    examples: List[QueryExample] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            candidates = [
                Candidate(id=str(x["id"]), title=str(x.get("title", "")), description=str(x.get("description", "")))
                for x in obj["candidates"]
            ]
            examples.append(
                QueryExample(
                    query_id=str(obj.get("query_id", obj.get("id", ""))),
                    query=str(obj["query"]),
                    candidates=candidates,
                    target_id=str(obj["target_id"]) if obj.get("target_id") is not None else None,
                )
            )
            if limit is not None and len(examples) >= limit:
                break
    return examples


def _rank_candidates(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_template: str,
    query: str,
    candidates: Sequence[Candidate],
    temperature: float,
) -> List[str]:
    user = _render_template(
        user_template,
        {
            "query": query,
            "candidates": _format_candidates(candidates),
        },
    )
    out = client.chat_json(model=model, system=system_prompt, user=user, temperature=temperature)
    ordered_ids = out.get("ordered_ids")
    if not isinstance(ordered_ids, list) or not all(isinstance(x, str) for x in ordered_ids):
        raise LLMError("Ranker output missing ordered_ids")

    expected = {c.id for c in candidates}
    got = set(ordered_ids)
    if expected != got:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise LLMError(f"Ranker ordered_ids must be a permutation. missing={missing} extra={extra}")

    return ordered_ids


def _rewrite_description(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_template: str,
    title: str,
    description: str,
    temperature: float,
) -> str:
    user = _render_template(
        user_template,
        {
            "title": title,
            "description": description,
        },
    )
    out = client.chat_json(model=model, system=system_prompt, user=user, temperature=temperature)
    rewritten = out.get("rewritten_description")
    if not isinstance(rewritten, str) or not rewritten.strip():
        raise LLMError("Rewriter output missing rewritten_description")
    return rewritten


def _rank_position(ordered_ids: Sequence[str], target_id: str) -> int:
    return list(ordered_ids).index(target_id) + 1


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stderr(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var / len(values))


def evaluate(
    *,
    dataset_path: Path,
    prompts_dir: Path,
    ranker_model: str,
    rewriter_model: str,
    temperature: float,
    seed: int,
    limit: Optional[int],
    verbose: bool,
) -> Dict[str, Any]:
    client = get_client()

    ranker_system = _read_text(prompts_dir / "ranker_system.txt")
    ranker_user = _read_text(prompts_dir / "ranker_user.txt")
    rewriter_system = _read_text(prompts_dir / "rewriter_system.txt")
    rewriter_user = _read_text(prompts_dir / "rewriter_user.txt")

    examples = _load_dataset(dataset_path, limit=limit)
    rng = random.Random(seed)

    improvements: List[float] = []
    moved_up: int = 0

    for ex in examples:
        candidates = list(ex.candidates)
        if not candidates:
            continue

        target_id = ex.target_id
        if not target_id:
            target_id = rng.choice(candidates).id

        base_order = _rank_candidates(
            client=client,
            model=ranker_model,
            system_prompt=ranker_system,
            user_template=ranker_user,
            query=ex.query,
            candidates=candidates,
            temperature=temperature,
        )
        base_rank = _rank_position(base_order, target_id)

        id_to_idx = {c.id: i for i, c in enumerate(candidates)}
        idx = id_to_idx[target_id]
        target = candidates[idx]

        rewritten_desc = _rewrite_description(
            client=client,
            model=rewriter_model,
            system_prompt=rewriter_system,
            user_template=rewriter_user,
            title=target.title,
            description=target.description,
            temperature=temperature,
        )

        candidates_after = list(candidates)
        candidates_after[idx] = Candidate(id=target.id, title=target.title, description=rewritten_desc)

        new_order = _rank_candidates(
            client=client,
            model=ranker_model,
            system_prompt=ranker_system,
            user_template=ranker_user,
            query=ex.query,
            candidates=candidates_after,
            temperature=temperature,
        )
        new_rank = _rank_position(new_order, target_id)

        improvement = float(base_rank - new_rank)
        improvements.append(improvement)
        if improvement > 0:
            moved_up += 1

        if verbose:
            print(
                json.dumps(
                    {
                        "query_id": ex.query_id,
                        "target_id": target_id,
                        "rank_before": base_rank,
                        "rank_after": new_rank,
                        "rank_improvement": improvement,
                    }
                )
            )

    summary = {
        "n": len(improvements),
        "avg_rank_improvement": _mean(improvements),
        "stderr_rank_improvement": _stderr(improvements),
        "win_rate": (moved_up / len(improvements)) if improvements else 0.0,
    }
    return summary


def _batch_summary(result: Dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True)


def optimize(
    *,
    train_path: Path,
    val_path: Path,
    prompts_dir: Path,
    ranker_model: str,
    rewriter_model: str,
    meta_model: str,
    temperature: float,
    seed: int,
    iters: int,
) -> Dict[str, Any]:
    client = get_client()

    ranker_system = _read_text(prompts_dir / "ranker_system.txt")
    ranker_user = _read_text(prompts_dir / "ranker_user.txt")
    rewriter_system = _read_text(prompts_dir / "rewriter_system.txt")

    rewriter_user_path = prompts_dir / "rewriter_user.txt"
    current_prompt = _read_text(rewriter_user_path)

    meta_system = _read_text(prompts_dir / "meta_optimizer_system.txt")
    meta_user_tpl = _read_text(prompts_dir / "meta_optimizer_user.txt")

    history: List[Dict[str, Any]] = []
    best_val: Optional[Dict[str, Any]] = None

    rng = random.Random(seed)

    def eval_with_prompt(dataset_path: Path, prompt_text: str) -> Dict[str, Any]:
        examples = _load_dataset(dataset_path)
        rng.shuffle(examples)

        improvements: List[float] = []
        moved_up: int = 0

        for ex in examples:
            candidates = list(ex.candidates)
            if not candidates:
                continue
            target_id = ex.target_id or rng.choice(candidates).id

            base_order = _rank_candidates(
                client=client,
                model=ranker_model,
                system_prompt=ranker_system,
                user_template=ranker_user,
                query=ex.query,
                candidates=candidates,
                temperature=temperature,
            )
            base_rank = _rank_position(base_order, target_id)

            id_to_idx = {c.id: i for i, c in enumerate(candidates)}
            idx = id_to_idx[target_id]
            target = candidates[idx]

            rewritten_desc = _rewrite_description(
                client=client,
                model=rewriter_model,
                system_prompt=rewriter_system,
                user_template=prompt_text,
                title=target.title,
                description=target.description,
                temperature=temperature,
            )

            candidates_after = list(candidates)
            candidates_after[idx] = Candidate(id=target.id, title=target.title, description=rewritten_desc)

            new_order = _rank_candidates(
                client=client,
                model=ranker_model,
                system_prompt=ranker_system,
                user_template=ranker_user,
                query=ex.query,
                candidates=candidates_after,
                temperature=temperature,
            )
            new_rank = _rank_position(new_order, target_id)

            improvement = float(base_rank - new_rank)
            improvements.append(improvement)
            if improvement > 0:
                moved_up += 1

        return {
            "n": len(improvements),
            "avg_rank_improvement": _mean(improvements),
            "stderr_rank_improvement": _stderr(improvements),
            "win_rate": (moved_up / len(improvements)) if improvements else 0.0,
        }

    for i in range(iters):
        train_res = eval_with_prompt(train_path, current_prompt)
        history.append({"iter": i, "prompt": current_prompt, "train": train_res})

        val_res = eval_with_prompt(val_path, current_prompt)
        if best_val is None or val_res["avg_rank_improvement"] > best_val["val"]["avg_rank_improvement"]:
            best_val = {"iter": i, "prompt": current_prompt, "val": val_res}

        hist_compact = [
            {"iter": h["iter"], "train": h["train"], "prompt_len": len(h["prompt"]) }
            for h in history[-6:]
        ]
        meta_user = _render_template(
            meta_user_tpl,
            {
                "current_prompt": current_prompt,
                "batch_summary": _batch_summary(train_res),
                "history": json.dumps(hist_compact, indent=2, sort_keys=True),
            },
        )
        meta_out = client.chat_json(model=meta_model, system=meta_system, user=meta_user, temperature=temperature)
        new_prompt = meta_out.get("new_prompt")
        if not isinstance(new_prompt, str) or not new_prompt.strip():
            raise LLMError("Meta-optimizer output missing new_prompt")
        current_prompt = new_prompt

    if best_val is None:
        raise LLMError("No validation results")

    rewriter_user_path.write_text(best_val["prompt"], encoding="utf-8")
    return {
        "best": best_val,
        "history_len": len(history),
        "saved_to": str(rewriter_user_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    eval_p = sub.add_parser("evaluate")
    eval_p.add_argument("--dataset", required=True)
    eval_p.add_argument("--prompts", default=str(Path(__file__).parent / "prompts"))
    eval_p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    eval_p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    eval_p.add_argument("--temperature", type=float, default=0.0)
    eval_p.add_argument("--seed", type=int, default=7)
    eval_p.add_argument("--limit", type=int, default=None)
    eval_p.add_argument("--verbose", action="store_true")

    opt_p = sub.add_parser("optimize")
    opt_p.add_argument("--train", required=True)
    opt_p.add_argument("--val", required=True)
    opt_p.add_argument("--prompts", default=str(Path(__file__).parent / "prompts"))
    opt_p.add_argument("--ranker-model", default=os.environ.get("RANKER_MODEL", "gpt-4o"))
    opt_p.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-4o"))
    opt_p.add_argument("--meta-model", default=os.environ.get("META_MODEL", "gpt-4o"))
    opt_p.add_argument("--temperature", type=float, default=0.0)
    opt_p.add_argument("--seed", type=int, default=7)
    opt_p.add_argument("--iters", type=int, default=5)

    args = parser.parse_args()

    if args.cmd == "evaluate":
        summary = evaluate(
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
        return

    if args.cmd == "optimize":
        res = optimize(
            train_path=Path(args.train),
            val_path=Path(args.val),
            prompts_dir=Path(args.prompts),
            ranker_model=args.ranker_model,
            rewriter_model=args.rewriter_model,
            meta_model=args.meta_model,
            temperature=args.temperature,
            seed=args.seed,
            iters=args.iters,
        )
        print(json.dumps(res, indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
