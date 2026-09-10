from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
from pathlib import Path

from strands import Agent

from agents.continuity import ContinuityOutput, build_prompt
from agents.model import bedrock, run_structured
from eval.run_eval import load_pairs

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ablation.json"

NEUTRAL = """You decide whether a new municipal legislative record continues an issue \
the system has already seen, or starts a new one.

You are given two records and a table of comparison features that were computed \
deterministically in code. The feature table is evidence. Do not recompute it, do not \
contradict it, and do not invent facts that are not in it or in the records.

Return your decision with:
- `decision`: continuation, new_issue, or uncertain.
- `rationale`: short plain sentences a resident could follow. Name the specific evidence.
- `drivers`: the feature names that actually drove the decision.
- `non_drivers`: the features you considered and explicitly did not rely on, with the value.
- `confidence`: 0 to 1.

Use `uncertain` when the evidence genuinely conflicts, not to avoid a call."""


def decide(pair, system_prompt):
    row, older, newer, features = pair
    agent = Agent(
        model=bedrock(),
        system_prompt=system_prompt,
        structured_output_model=ContinuityOutput,
        name="ablation",
        callback_handler=None,
    )
    out, usage = run_structured(agent, build_prompt(newer, older, features))
    decision = out.decision.strip().lower()
    if decision not in ("continuation", "new_issue", "uncertain"):
        decision = "uncertain"
    return {
        "pair_id": row["pair_id"],
        "a": row["a"],
        "b": row["b"],
        "tier": row.get("tier", "parcel"),
        "label": row["label"],
        "said": decision,
        "confidence": out.confidence,
        "drivers": out.drivers,
        "non_drivers": out.non_drivers,
        "usage": usage,
    }


def run(system_prompt, workers=6):
    pairs, _ = load_pairs()
    results = []
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(lambda p: decide(p, system_prompt), pairs):
            correct = (r["said"] == "continuation") == (r["label"] == "continuation")
            print(f"  {'ok ' if correct else 'MISS'} pair {r['pair_id']:2} {r['a']:>9} {r['b']:<9} {r['said']}", flush=True)
            results.append(r)
    return sorted(results, key=lambda r: r["pair_id"])


def score(results):
    correct = [r for r in results if (r["said"] == "continuation") == (r["label"] == "continuation")]
    misses = [r for r in results if r not in correct]
    return {
        "n": len(results),
        "correct": len(correct),
        "accuracy": len(correct) / len(results) if results else 0.0,
        "called_continuation": sum(1 for r in results if r["said"] == "continuation"),
        "misses": misses,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    print("Neutral prompt, all domain guidance removed:")
    results = run(NEUTRAL, args.workers)
    stats = score(results)
    print(f"\nneutral accuracy {stats['correct']}/{stats['n']} = {stats['accuracy']:.2%}")
    print("misses:", [m["pair_id"] for m in stats["misses"]])

    OUT.write_text(json.dumps({
        "system_prompt": NEUTRAL,
        "accuracy": stats["accuracy"],
        "correct": stats["correct"],
        "n": stats["n"],
        "called_continuation": stats["called_continuation"],
        "results": results,
    }, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
