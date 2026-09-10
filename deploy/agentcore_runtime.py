from __future__ import annotations

import json
import os
from functools import lru_cache

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agents.continuity import ContinuityAgent
from features.continuity_features import compute
from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus

app = BedrockAgentCoreApp()

LABELS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "labeled_set.jsonl")


@lru_cache(maxsize=1)
def _corpus():
    gaz = Gazetteer.load()
    return {r.file_number: r for r in load_corpus(gaz)}


@lru_cache(maxsize=1)
def _pairs():
    out = {}
    with open(LABELS) as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                out[int(row["pair_id"])] = row
    return out


@lru_cache(maxsize=1)
def _agent():
    return ContinuityAgent()


def _order(a, b):
    return (a, b) if (a.introduced_date <= b.introduced_date) else (b, a)


@app.entrypoint
def invoke(payload):
    pairs = _pairs()
    corpus = _corpus()

    if payload.get("action") == "list":
        return {
            "pairs": [
                {"pair_id": pid, "a": row["a"], "b": row["b"],
                 "tier": row.get("tier", "parcel"), "hard": row["hard"]}
                for pid, row in sorted(pairs.items())
            ]
        }

    try:
        pair_id = int(payload.get("pair_id"))
    except (TypeError, ValueError):
        return {"error": "pair_id must be an integer from the labeled set"}

    row = pairs.get(pair_id)
    if row is None:
        return {"error": f"unknown pair_id {pair_id}", "valid": sorted(pairs)}

    a, b = corpus.get(row["a"]), corpus.get(row["b"])
    if not a or not b:
        return {"error": f"records not in cached corpus: {row['a']}, {row['b']}"}

    older, newer = _order(a, b)
    decision = _agent().decide(newer, older)

    return {
        "pair_id": pair_id,
        "older": {"file_number": older.file_number, "title": older.title[:400],
                  "status": older.status, "introduced": str(older.introduced_date)},
        "newer": {"file_number": newer.file_number, "title": newer.title[:400],
                  "status": newer.status, "introduced": str(newer.introduced_date)},
        "decision": decision.decision,
        "confidence": decision.confidence,
        "rationale": decision.rationale,
        "drivers": decision.drivers,
        "non_drivers": decision.non_drivers,
        "features": compute(newer, older),
        "label": row["label"],
        "agreed": (decision.decision == "continuation") == (row["label"] == "continuation"),
    }


if __name__ == "__main__":
    app.run()
