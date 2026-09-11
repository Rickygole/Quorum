from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from functools import lru_cache

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.join(HERE, "pairs_bundle.json")

MODEL_ID = os.environ.get("QUORUM_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
REGION = os.environ.get("AWS_REGION", "us-east-1")
MAX_PER_MINUTE = int(os.environ.get("QUORUM_MAX_PER_MINUTE", "12"))
MAX_PER_DAY = int(os.environ.get("QUORUM_MAX_PER_DAY", "400"))

_calls = deque()
_day = {"start": time.time(), "count": 0}
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _bundle():
    with open(BUNDLE) as fh:
        return json.load(fh)


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


def _decide(prompt, system_prompt):
    from pydantic import BaseModel, Field
    from strands import Agent
    from strands.models import BedrockModel

    class ContinuityOutput(BaseModel):
        decision: str = Field(description="continuation, new_issue, or uncertain")
        rationale: str
        drivers: list[str] = Field(default_factory=list)
        non_drivers: list[str] = Field(default_factory=list)
        confidence: float = 0.0

    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION, temperature=0.2),
        system_prompt=system_prompt,
        structured_output_model=ContinuityOutput,
        name="continuity",
        callback_handler=None,
    )
    result = agent(prompt)
    out = result.structured_output
    usage = getattr(getattr(result, "metrics", None), "accumulated_usage", None) or {}
    get = (lambda k: usage.get(k)) if isinstance(usage, dict) else (lambda k: getattr(usage, k, None))
    return out, {
        "input_tokens": get("inputTokens") or get("input_tokens"),
        "output_tokens": get("outputTokens") or get("output_tokens"),
    }


def _cached_reply(entry, pair_id, reason):
    cached = entry.get("cached")
    if not cached:
        return {"error": reason, "live": False, "pair_id": pair_id}
    return {
        "pair_id": pair_id, "live": False, "cached": True, "reason": reason,
        "decision": cached["decision"], "confidence": cached["confidence"],
        "rationale": cached["rationale"], "drivers": cached["drivers"],
        "non_drivers": cached["non_drivers"],
        "older": entry["older"], "newer": entry["newer"],
        "features": entry["features"], "label": entry["label"],
    }


@app.entrypoint
def invoke(payload):
    bundle = _bundle()
    pairs = bundle["pairs"]

    if payload.get("action") == "list":
        return {"pairs": [
            {"pair_id": v["pair_id"], "a": v["older"]["file_number"],
             "b": v["newer"]["file_number"], "tier": v["tier"]}
            for v in sorted(pairs.values(), key=lambda x: x["pair_id"])
        ]}

    try:
        pair_id = int(payload.get("pair_id"))
    except (TypeError, ValueError):
        return {"error": "pair_id must be an integer from the labeled set", "live": False}

    entry = pairs.get(str(pair_id))
    if entry is None:
        return {"error": f"unknown pair_id {pair_id}", "live": False,
                "valid": sorted(int(k) for k in pairs)}

    denied = _take_slot()
    if denied:
        return _cached_reply(entry, pair_id, denied)

    started = time.time()
    try:
        out, usage = _decide(entry["prompt"], bundle["system_prompt"])
    except Exception as exc:
        return _cached_reply(entry, pair_id, f"{type(exc).__name__}: {str(exc)[:160]}")

    decision = out.decision.strip().lower()
    if decision not in ("continuation", "new_issue", "uncertain"):
        decision = "uncertain"

    return {
        "pair_id": pair_id,
        "live": True,
        "latency_ms": round((time.time() - started) * 1000),
        "region": REGION,
        "model_id": MODEL_ID,
        "usage": usage,
        "older": entry["older"],
        "newer": entry["newer"],
        "decision": decision,
        "confidence": max(0.0, min(1.0, out.confidence)),
        "rationale": out.rationale.strip(),
        "drivers": out.drivers,
        "non_drivers": out.non_drivers,
        "features": entry["features"],
        "label": entry["label"],
        "agreed": (decision == "continuation") == (entry["label"] == "continuation"),
    }


if __name__ == "__main__":
    app.run()
