from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
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


MAX_PER_MINUTE = int(os.environ.get("QUORUM_MAX_PER_MINUTE", "12"))
MAX_PER_DAY = int(os.environ.get("QUORUM_MAX_PER_DAY", "400"))

_calls = deque()
_day = {"start": time.time(), "count": 0}
_lock = threading.Lock()


def _take_slot():
    now = time.time()
    with _lock:
        while _calls and now - _calls[0] > 60:
            _calls.popleft()
        if now - _day["start"] > 86400:
            _day["start"] = now
            _day["count"] = 0
        if len(_calls) >= MAX_PER_MINUTE:
            return "rate limit reached, try again in a minute"
        if _day["count"] >= MAX_PER_DAY:
            return "daily invocation cap reached"
        _calls.append(now)
        _day["count"] += 1
        return None


def _agent():
    return ContinuityAgent()


@lru_cache(maxsize=1)
def _cached_decisions():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "agent_decisions.json")
    try:
        with open(path) as fh:
            return json.load(fh)["decisions"]
    except (OSError, KeyError, ValueError):
        return {}


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

    denied = _take_slot()
    if denied:
        cached = _cached_decisions().get(str(pair_id))
        if not cached:
            return {"error": denied, "live": False}
        return {
            "pair_id": pair_id, "live": False, "cached": True, "reason": denied,
            "decision": cached["decision"], "confidence": cached["confidence"],
            "rationale": cached["rationale"], "drivers": cached["drivers"],
            "non_drivers": cached["non_drivers"],
        }

    started = time.time()
    decision = _agent().decide(newer, older)

    return {
        "pair_id": pair_id,
        "live": True,
        "latency_ms": round((time.time() - started) * 1000),
        "region": os.environ.get("AWS_REGION", "us-east-1"),
        "model_id": os.environ.get("QUORUM_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
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
