# Deployment

## What is deployed and working

**AgentCore Runtime**, the Continuity Agent, live and invoking Amazon Bedrock.

```
arn:aws:bedrock-agentcore:us-east-1:162774483375:runtime/quorum_continuity-eEoCT98tX4
status: READY
OpenTelemetry instrumentation enabled
```

Verified by invocation:

```
pair 20: continuation  conf 0.95  agreed=True  live=True  8759ms  2404/423 tokens
pair 25: new_issue     conf 0.95  agreed=True  live=True  7880ms  2448/361 tokens
```

Pair 20 is the hero case and pair 25 is the hardest negative, both decided correctly
against their hand labels, on real model calls.

## How to deploy it

```bash
python -m deploy.build_bundle
agentcore configure --entrypoint deploy/agentcore_runtime.py --name quorum_continuity \
  --requirements-file deploy/requirements.txt --disable-memory
agentcore deploy
```

## Three things that only break in deployment

Recorded because each cost a deploy cycle and none of them reproduce locally.

**Cold start has a 30 second limit.** Importing Strands, boto3, pydantic and the
OpenTelemetry distro at module scope exceeded it. Every heavy import in
`agentcore_runtime.py` is now inside the function that needs it, and module load is 0.3
seconds.

**Direct code deploy flattens the entrypoint into the image root.** Resolving paths with
`dirname(dirname(__file__))` therefore walked one directory too high and looked for the
labeled set in `/var/eval`.

**Direct code deploy packages only the entrypoint's own directory.** The `agents`,
`ingest`, `eval`, `features` and `data` trees were never in the image. Rather than
package the whole repository, the runtime now ships `pairs_bundle.json`, 329 KB holding
exactly the 50 labeled pairs with their prompts, feature tables and cached decisions,
generated from the real modules by `build_bundle.py` so the system prompt stays single
sourced. The corpus and the 237,092 parcel gazetteer are not needed at runtime, because
the endpoint only ever accepts a pair id from that set.

## The public endpoint

```
https://1gpbm1pph4.execute-api.us-east-1.amazonaws.com
```

`GET` returns the runtime identifier and the list of valid pair ids. `POST {"pair_id": N}`
runs the Continuity Agent on AgentCore Runtime against Amazon Bedrock and returns the
decision, the rationale, the drivers and non drivers, the runtime arn, the AgentCore
session id, the model id and the measured latency. The session id differs on every call,
which is how a live answer can be told from a replay.

Public Lambda function urls are blocked at the account level, so an HTTP API fronts the
Lambda that signs the request.

## Cost and rate limits

A full 50 pair evaluation on Sonnet 4.5 costs about 0.62 USD, 116k input and 18k output
tokens, which is roughly 0.0124 USD per invocation.

The endpoint is capped in two places, and the reason there are two is worth recording.
The runtime holds an in process counter behind a lock, and **that counter cannot do the
job on its own**: AgentCore isolates each invocation to its own execution environment, so
the counters live in separate containers and never see each other. Measured against the
account's Lambda concurrency ceiling of 10 and a live latency of roughly 14 seconds, a
single machine holding 10 connections open could sustain about 43 calls a minute, which
is around 760 USD a day against an intended budget of 5.

So the real limits are outside the process:

- **API Gateway throttling**, 0.1 requests per second with a burst of 2, applied at the
  stage. This is enforced at the edge, before Lambda, and is global.
- **A shared daily counter in S3**, 300 live invocations per day, incremented with a
  conditional write so concurrent containers cannot both claim the same slot. Past the
  cap the endpoint returns the cached decision with `live` set to false and says why.

Worst case is therefore about 3.72 USD a day rather than 760. Reserved Lambda concurrency
would be a third layer but cannot be set: the account's total concurrency limit is 10 and
reserving any amount drops the unreserved pool below its minimum.

Input is validated before anything is spent. The body must be JSON, must be an object,
must be under 4 KB, and `pair_id` must be a real integer present in the 50 pair bundle.
Floats, booleans, nulls, arrays, bare strings, deeply nested payloads and unknown extra
fields are all rejected or ignored, and no field an attacker controls reaches a model
prompt. The prompt is built server side from the bundle.
