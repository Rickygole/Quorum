from __future__ import annotations

import json
import os
import time

import boto3

RUNTIME_ARN = os.environ.get("QUORUM_RUNTIME_ARN", "")
COUNTER_BUCKET = os.environ.get("QUORUM_COUNTER_BUCKET", "")
MAX_PER_DAY = int(os.environ.get("QUORUM_MAX_PER_DAY", "300"))
MAX_BODY_BYTES = 4096
REGION = os.environ.get("AWS_REGION", "us-east-1")
ALLOWED_ORIGINS = [o for o in os.environ.get("QUORUM_ALLOWED_ORIGINS", "").split(",") if o]
CACHED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_decisions.json")

_client = None
_s3 = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def day_key():
    import datetime

    return f"counter/{datetime.datetime.now(datetime.timezone.utc).date().isoformat()}.txt"


def take_daily_slot():
    if not COUNTER_BUCKET:
        return None
    key = day_key()
    for _ in range(6):
        try:
            obj = s3().get_object(Bucket=COUNTER_BUCKET, Key=key)
            count = int(obj["Body"].read().decode().strip() or "0")
            etag = obj["ETag"]
        except s3().exceptions.NoSuchKey:
            count, etag = 0, None
        except Exception as exc:
            print(f"rate limiter read failed: {type(exc).__name__}: {str(exc)[:200]}")
            return None
        if count >= MAX_PER_DAY:
            return f"daily cap of {MAX_PER_DAY} live invocations reached"
        try:
            kwargs = {"Bucket": COUNTER_BUCKET, "Key": key, "Body": str(count + 1).encode()}
            if etag:
                kwargs["IfMatch"] = etag
            else:
                kwargs["IfNoneMatch"] = "*"
            s3().put_object(**kwargs)
            return None
        except Exception as exc:
            print(f"rate limiter write failed: {type(exc).__name__}: {str(exc)[:200]}")
            continue
    return "rate limiter contended, try again"


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

    raw = event.get("body") or "{}"
    if len(raw) > MAX_BODY_BYTES:
        return reply(413, {"live": False, "error": "body too large"}, origin)

    try:
        body = json.loads(raw)
    except Exception:
        return reply(400, {"live": False, "error": "body must be JSON"}, origin)

    if not isinstance(body, dict):
        return reply(400, {"live": False, "error": "body must be a JSON object"}, origin)

    pair_id = body.get("pair_id")
    if isinstance(pair_id, bool) or not isinstance(pair_id, int):
        return reply(400, {"live": False, "error": "pair_id must be an integer from the labeled set"}, origin)

    if str(pair_id) not in cached_decisions():
        return reply(400, {"live": False, "error": f"unknown pair_id {pair_id}"}, origin)

    if not RUNTIME_ARN:
        return fallback(pair_id, "runtime not configured", origin)

    denied = take_daily_slot()
    if denied:
        return fallback(pair_id, denied, origin)

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
