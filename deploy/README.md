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

## The public endpoint, and why it is not live

A static page cannot sign a SigV4 request, so a judge clicking a button needs a signer in
front of the runtime. `invoke_proxy.py` and `deploy_proxy.sh` build that: a Lambda that
accepts only a pair id from the labeled set, returns the runtime ARN, region, session id
and latency so a live call is distinguishable from a cached one, and falls back to the
cached decision rather than erroring.

The Lambda is deployed and verified working by direct invocation. **Its public Function
URL returns 403 and the cause is account level.** The function URL is created with
`AuthType: NONE` and the resource policy is byte identical to the public access statement
in the AWS documentation:

```json
{"Sid":"FunctionURLAllowPublicAccess","Effect":"Allow","Principal":"*",
 "Action":"lambda:InvokeFunctionUrl",
 "Condition":{"StringEquals":{"lambda:FunctionUrlAuthType":"NONE"}}}
```

Recreating the URL config, widening CORS to `*` and recreating the permission under the
documented statement id all produce the same result. This account does not permit public
Lambda function URLs.

The remaining route is an HTTP API in front of the same Lambda, which needs
`apigateway:*` on the deploying identity. Until that is granted the site reports cached
decisions and labels them as cached, which is the honest presentation. Nothing on the
site claims a live invocation that did not happen.

## Cost and rate limits

A full 50 pair evaluation on Sonnet 4.5 costs about 0.62 USD, 116k input and 18k output
tokens. The runtime enforces its own caps, 12 invocations per minute and 400 per day,
behind a lock, and degrades to the cached decision rather than refusing. Reserved Lambda
concurrency is best effort: a new account's total concurrency limit is 10 and reserving
any drops the unreserved pool below its minimum.
