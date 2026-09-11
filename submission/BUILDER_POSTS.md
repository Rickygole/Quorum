# Builder posts

Three posts drafted for builder.aws.com, written from material already in this repository.
Each title includes "Agents for Humans." Word counts are for the body only.

---

## Post 1: Agents for Humans, why one node in our Strands Graph makes no model call

Quorum watches Baltimore City Council's published legislative record for anything that
touches a resident's address, and decides whether a new record continues an issue it has
already seen. It is built as a Strands Graph, not a Swarm, because the execution path is
deterministic and dependency ordered: every record passes through the same five stations in
the same order, and no station needs to hand control back to one behind it. That is what
`Graph` is for. `Swarm` exists for dynamic handoff between agents deciding among themselves
who works next, and Quorum has no such decision to make. Reaching for a Swarm here would add
nondeterminism to a pipeline whose entire value depends on being auditable.

Four of the five nodes are Strands agents: Civic Analyst, Continuity, Relevance, and Action.
The fifth, Resolution, is a `CustomNode` that runs as code and makes no model call at all.
It sits in the same orchestration surface as the agents, appears on the same run screen, and
does one job: match a record's address and block and lot references against Baltimore's
eGIS parcel layer, a static gazetteer of 237,092 parcels.

We built it that way on purpose. Address normalization and block and lot parsing are solved
deterministic problems. A language model asked to normalize "205-209 E Cold Spring Lane"
into a block and lot reference will occasionally return a plausible and wrong answer, and a
hallucinated parcel identifier is the one error in this system a resident cannot detect from
reading the output. They would just see an address that looks right. So resolution runs in
code, with no model in the loop, and the agent budget is spent only where judgment is
actually required.

That same principle shapes the Continuity Agent, the node that decides whether a new record
is the same issue as one Quorum has already seen. The naive version of this agent asks a
model whether two records are the same thing and takes the answer on faith. That answer
cannot be interrogated, and neither can an embedding similarity score. We also tried, and
rejected, a purely weighted numeric rule: weights cannot be honestly tuned against a
population of 9 parcels in our corpus that recur under more than one file number, and "what
does 0.4 mean" has no good answer when someone asks it directly.

Instead, Quorum computes a table of comparison features in code (parcel match, sponsor
overlap, title similarity, zoning transition, prior status, temporal gap) and hands that
table to the Continuity Agent as evidence. The agent is required to name which features
drove its decision and which it explicitly did not rely on. That last part turns out to
matter more than we expected. Take our two canonical cases from the corpus: bill 26-0148
against bill 23-0411, the same rezoning reintroduced two and a half years apart under a
different file number, and bill 25-0056 against bill 25-0055, two entirely different
projects on adjacent lots. Title cosine similarity is 0.943 for the first pair and 0.944 for
the second, higher for the pair that is not a continuation. Any system deciding this on
string or embedding similarity alone gets both cases backwards. What actually separates them
is the parcel comparison, exact against merely adjacent, the terminal status of the prior
bill, and whether the zoning transition repeats, and the Continuity Agent is required to say
so out loud rather than just emit a label.

We tested whether that domain guidance is doing real work or just restating a rule in
English. We deleted every domain hint from the prompt, keeping only the task, the output
schema, and an instruction not to invent facts. Accuracy on our 50 hand-labeled pairs fell
from 100% to 94%, three misses, not down to the 78% a parcel-only rule gets on its own. If
the guidance were the rule in disguise, removing it should have collapsed performance to the
rule's level. It did not. The three cases the stripped prompt missed were a liquor license
matched to its own zoning approval, a charter amendment returning after a failed council
term, and one street condemnation split across two file numbers. Nothing in a deterministic
feature table flags those as one issue on its own. Someone, or something, has to know how a
city actually works, and that is the three-pair gap between a feature table and an agent
reading one.

The honest way to describe this architecture is a hybrid: deterministic code does the
parcel matching and the feature computation, and does it exactly, with zero false positives
across all 9 exact-parcel pairs in the entire 1,679-record corpus. A model reasons over that
evidence table for the harder cases a lookup cannot see, and is required to show its work.
Four agents, one deterministic node, not five agents and not zero.

*(approximately 820 words)*

---

## Post 2: Agents for Humans, publishing the evaluation that ties instead of the one that flatters us

We built Quorum to decide whether a new Baltimore City Council record continues an issue it
has already seen or starts a new one. Before we called the evaluation done, we asked the
question a skeptical reader would ask first: does the agent actually beat a simple rule, or
does it just look like it does?

Our evaluation set is 50 hand-labeled pairs, 19 of them true continuations, split into two
tiers. 28 pairs share a parcel or a block. 22 do not, and were matched instead on shared
sponsor and a title cosine similarity at or above 0.97. We built the second tier on purpose,
because the first tier alone hides a whole class of continuation a parcel match cannot see:
citywide bills, naming no property at all, that die at the end of a council term and return
years later under a new file number.

A tuned two-clause rule, parcel exact or (title cosine at or above 0.97 and the prior record
terminal), scores 100% on all 50 pairs. So does our Continuity Agent. We report that plainly
and first, because it is the strongest argument against the whole project, not something to
bury in a footnote. We also checked how fragile that rule's threshold is: swept from 0.80 to
1.00, it scores 100% only between 0.94 and 0.97, four points on the sweep and 0.03 of cosine, and drops to 96%
immediately outside it. The margin between a right answer and a wrong one on this set is a
single pair at cosine 0.934 and another at 0.971, thirty-seven thousandths apart. That is a
property of this particular sample of fifty pairs, not a property of municipal legislation
in general, and it is exactly the kind of number that should make you distrust a headline
accuracy figure, including ours.

So we ran a held-out split to see if the tie survives once tuning advantage is removed. The
50 pairs are partitioned into a 24-pair tune half and a 26-pair test half, stratified by
tier and label, assigned by a hash of the pair id so the split is reproducible and was not
chosen by looking at which pairs are easy. We swept the rule's threshold on the tune half
only, froze it at 0.950, and scored every rule, including the frozen rule and the cached
agent decisions, on the test half the threshold never saw. Result: the frozen rule and the
agent agree on every single one of the 26 test pairs. Zero disagreements. McNemar's exact
test gives p equals 1.0. With a test half this small, no difference of any meaningful size
could reach statistical significance even if one existed. We titled that section of our
results file "Nothing. It does not separate the agent from the rule, and that is the
finding," because publishing a negative result that cost real engineering time to obtain is
worth more than a positive one we did not actually test.

The number that changed our own thinking is the per-tier breakdown. On the parcel tier, a
parcel lookup alone is perfect: 8 of 8 true continuations found, because deterministic code
is exactly the right tool for a problem that is genuinely deterministic. On the citywide
tier, the same lookup finds 0 of the 11 true continuations, because those records name no
property Quorum can match. 11 of the 19 true continuations across the whole set, 58%, have
no parcel anywhere in them. That is the actual argument for the agent, not the tied 100% on
the full set: a lookup where a lookup is exact, and a model reasoning over evidence exactly
where the alternative is a brittle, hand-tuned threshold.

We also ran an ablation, stripping every domain-specific hint from the prompt down to task,
schema, and a rule against inventing facts. Accuracy dropped from 100% to 94%, three misses,
still well above the 78% the best single deterministic feature manages alone. That gap of
three pairs, a liquor license tied to its own zoning approval, a returning charter
amendment, and a street condemnation split into two filings, is what the domain knowledge
actually buys.

None of this makes the agent look magical. It makes the honest claim narrower and more
useful: the agent ties a good rule where the rule already works, and does something a rule
cannot on the majority of cases the rule cannot reach. Publishing the tie, the fragile
threshold, and the null result from the held-out split is the part of this evaluation we are
most glad we did not skip.

*(approximately 770 words)*

---

## Post 3: Agents for Humans, three bugs that only appear once you deploy to AgentCore Runtime

Quorum's Continuity Agent runs locally without any trouble. It failed three different ways
the moment we deployed it to Amazon Bedrock AgentCore Runtime, and none of the three
reproduced in local testing. Recording them here because each one cost a deploy cycle to
find, and each one is a category of bug, not a one-off typo.

**Cold start exceeded the 30-second limit.** AgentCore Runtime enforces a cold-start budget,
and our entrypoint module was importing Strands, boto3, pydantic, and the AWS OpenTelemetry
distribution at module load time, before the entrypoint function ever ran. Locally, that
import cost was invisible, a fraction of a second on a warm interpreter with everything
already cached on disk. On a fresh runtime instance, loading all four packages cold pushed
module initialization past the limit before the runtime ever got to invoke our function. The
fix was to make every heavy import lazy, moved inside the functions that actually need them,
so the module itself has almost nothing to load at import time. Module load is now 0.3
seconds, and the runtime initializes well inside its budget.

**Path resolution assumed a repository layout that direct code deploy does not preserve.**
Locally, our entrypoint script sits one directory below the repository root, so a
`dirname(dirname(__file__))` walk correctly reached the root and found the labeled
evaluation set relative to it. AgentCore's direct code deploy flattens the entrypoint into
the root of its own image, not one level below anything. The same path arithmetic that
worked locally walked one directory too high in the deployed image and went looking for our
data in a directory that does not exist there. The lesson generalizes past this one bug: any
path built by walking up from `__file__` is making an assumption about the surrounding
directory structure, and a deployment target is under no obligation to honor the layout of
your development checkout.

**Direct code deploy only packages the entrypoint's own directory.** This was the most
consequential of the three. We assumed the whole repository, or at least everything our
entrypoint imports, would travel with it into the deployed image. It does not. Direct code
deploy packages the directory containing the entrypoint file and nothing outside it, so our
`agents`, `ingest`, `eval`, and `features` packages, along with the corpus and the
237,092-parcel gazetteer, were simply never present at runtime. Rather than restructure the
whole repository around the deployment tool's packaging assumption, we built a small
one-way export: `deploy/build_bundle.py` reads the real Continuity Agent module, the real
prompt, and the real labeled pairs, and writes a single self-contained 329-kilobyte JSON
bundle carrying exactly the 50 labeled pairs with their prompts, feature tables, and cached
decisions. The deployed entrypoint ships with that bundle and needs nothing else, because
the deployed endpoint only ever accepts a pair id from that known set; it does not need the
full corpus or the gazetteer at runtime at all. The system prompt in the bundle is generated
from the same source file the local agent uses, so the deployed prompt cannot drift out of
sync with the one we evaluate against.

With all three fixed, the runtime is live and verified by direct invocation. Calling it with
the hero pair, bill 26-0148 against bill 23-0411, returns a continuation decision at 0.95
confidence, agreeing with our hand label, in about nine seconds on Sonnet 4.5, using
roughly 2,400 input tokens and 400 output tokens. Calling it with our hardest labeled
negative returns new_issue, also agreeing with the label, in a comparable time. Both calls
carry real usage numbers back from Bedrock, not simulated ones.

One more finding worth recording honestly: the public-facing side of this is not fully live
yet. A static page cannot sign a SigV4 request on its own, so we put a small AWS Lambda in
front of the runtime to act as a signer. The Lambda itself works, verified by direct
invocation. Its public function URL returns a 403 in this AWS account even with the
documented public-access resource policy attached exactly as written in AWS's own
documentation, byte for byte. Recreating the URL configuration and the permission did not
change the result. That appears to be an account-level restriction on public Lambda function
URLs, not a bug in our configuration, and the fix is an HTTP API in front of the same
Lambda instead of a bare function URL, and that is what now runs:

```
https://1gpbm1pph4.execute-api.us-east-1.amazonaws.com
```

Two caps sit in front of it, and the reason there are two is the interesting part. The runtime
holds an in process counter behind a lock, and that counter cannot do the job on its own,
because AgentCore isolates every invocation to its own execution environment and the counters
never see each other. The real limits had to go outside the process: throttling at the API
Gateway stage, and a shared daily counter in S3 incremented with a conditional write so two
concurrent containers cannot claim the same slot.

*(approximately 770 words)*
