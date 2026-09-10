from __future__ import annotations

import json
import os
import time

import boto3

RUNTIME_ARN = os.environ.get("QUORUM_RUNTIME_ARN", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")
ALLOWED_ORIGINS = [o for o in os.environ.get("QUORUM_ALLOWED_ORIGINS", "").split(",") if o]
CACHED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_decisions.json")

_client = None


def client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=REGION)
    return _client


def cached_decisions():
    try:
        with open(CACHED) as fh:
            return json.load(fh)["decisions"]
    except (OSError, KeyError, ValueError):
        return {}


def cors_headers(origin):
    allow = origin if (origin and origin in ALLOWED_ORIGINS) else (ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*")
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
    }


def reply(status, body, origin):
    return {"statusCode": status, "headers": cors_headers(origin), "body": json.dumps(body)}


def fallback(pair_id, reason, origin):
    row = cached_decisions().get(str(pair_id))
    if not row:
        return reply(503, {"live": False, "error": reason}, origin)
    return reply(200, {
        "live": False, "cached": True, "reason": reason, "pair_id": pair_id,
        "decision": row["decision"], "confidence": row["confidence"],
        "rationale": row["rationale"], "drivers": row["drivers"],
        "non_drivers": row["non_drivers"],
    }, origin)


def handler(event, context):
    origin = (event.get("headers") or {}).get("origin") or ""
    method = (event.get("requestContext") or {}).get("http", {}).get("method", "GET")

    if method == "OPTIONS":
        return reply(204, {}, origin)

    if method == "GET":
        return reply(200, {
            "runtime_arn": RUNTIME_ARN, "region": REGION,
            "pairs": sorted(int(k) for k in cached_decisions()),
        }, origin)

    try:
        body = json.loads(event.get("body") or "{}")
        pair_id = int(body.get("pair_id"))
    except (TypeError, ValueError):
        return reply(400, {"live": False, "error": "pair_id must be an integer from the labeled set"}, origin)

    if str(pair_id) not in cached_decisions():
        return reply(400, {"live": False, "error": f"unknown pair_id {pair_id}"}, origin)

    if not RUNTIME_ARN:
        return fallback(pair_id, "runtime not configured", origin)

    started = time.time()
    try:
        resp = client().invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            payload=json.dumps({"pair_id": pair_id}).encode(),
        )
        raw = resp["response"].read()
        out = json.loads(raw)
    except Exception as exc:
        return fallback(pair_id, f"{type(exc).__name__}: {str(exc)[:160]}", origin)

    out["live"] = out.get("live", True)
    out["runtime_arn"] = RUNTIME_ARN
    out["region"] = REGION
    out["session_id"] = resp.get("runtimeSessionId") or resp.get("ResponseMetadata", {}).get("RequestId")
    out["proxy_latency_ms"] = round((time.time() - started) * 1000)
    return reply(200, out, origin)
