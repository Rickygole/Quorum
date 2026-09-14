# Quorum

Devpost submission text for the Agents for Humans Hackathon, Good Neighbor track.

## What it does

Quorum watches Baltimore City Council's published legislative record for anything that
touches a resident's address, and decides whether a new record continues an issue it has
already seen. It reads the record, matches it to a parcel, checks it against everything
that came before at that address, decides whether it affects the resident, and drafts a
public comment with the correct file number and hearing date. Then it stops. It never
submits anything on a person's behalf.

Right now, live on the site: bill 23-0411 rezoned 205-209 East Cold Spring Lane, owned by
Loyola University Maryland, from R-1-C to EC-2. It failed at the end of the council term in
2023. Two and a half years later the same sponsor, Mark Conway, reintroduced it under a
different file number, 26-0148, one lot smaller. Nothing in the file numbers or the exact
title wording links the two. A public hearing on the reintroduced bill is scheduled for
**2026-09-24**, inside this hackathon's judging window. A judge can go and check.

## Who it is for

A resident who owns or lives near a property in Baltimore and cannot read every council
agenda to find out when something that affects their block comes back around under a new
name. It is built for the person who would show up to a hearing if they knew about it in
time, and does not, because city business moves slowly, across years, under changing file
numbers, and nobody is watching on their behalf.

## Why it matters

City councils do not decide things once. Bills die at the end of a term and come back.
Zoning cases get renamed. A resident who missed the first round has no way of knowing the
second round is the same fight, unless someone holds the thread between the two. Quorum
holds that thread and hands it to the resident before the hearing, not after the vote.

## How it works

Quorum is a Strands Graph of five fixed-order nodes running as a single pipeline, deployed
to Amazon Bedrock AgentCore Runtime:

1. **Civic Analyst** (agent) reads each record's prose and extracts structured facts:
   addresses, blocks, zoning transitions, the action being requested. It is instructed to
   copy identifiers exactly and never invent one it cannot find in the text.
2. **Resolution** (deterministic code, no model call) matches the record's address and
   block/lot references against Baltimore's 237,092-parcel eGIS gazetteer. Address parsing
   is a solved problem, and a hallucinated parcel identifier is the one error in this system
   a resident cannot detect, so this step makes no model call at all.
3. **Continuity Agent** decides whether the record continues an issue already on file for
   that parcel or starts a new one. It is handed a table of deterministic comparison
   features (parcel match, sponsor overlap, title similarity, zoning transition, prior
   status, temporal gap) computed in code, and is required to name which features drove its
   decision and which it explicitly set aside.
4. **Relevance Agent** decides whether the record actually affects a resident watching that
   address, and is expected to say no most of the time. A citywide budget line naming a
   street in a schedule does not affect a resident in any way they could act on.
5. **Action Agent** writes the headline, what changed since the last appearance, why it
   matters in plain language, and a draft public comment carrying the correct file number
   and hearing date, only when a comment window is actually open.

Where the pipeline stops: if the underlying record is already decided (enacted, withdrawn,
failed), Quorum shows the resident the record, the sponsors, and the committee, and says
plainly that there is nothing to send. Of the 19 continuation threads on the site today,
only 1 has an open comment window. Quorum never fabricates urgency where none exists, and it
never drafts a comment for a decision that has already been taken.

The whole run stops at a human approval gate. Quorum drafts. It does not send. The button
opens the resident's own email client with the draft loaded, and nothing leaves the system
before a person decides to act.

## What we built with

- **Amazon Bedrock**: Sonnet 4.5 and Haiku 4.5 as the model provider for all
  four agent nodes.
- **Bedrock AgentCore Runtime**: the Continuity Agent is deployed and live, invoking Bedrock
  from a running AgentCore Runtime instance, not just from a local script.
- **AgentCore Observability**: OpenTelemetry instrumentation enabled on the deployed
  runtime.
- **Amazon CloudWatch**: receives the runtime's observability traces.
- **AWS Lambda**: fronts the AgentCore Runtime with a signer, since a static page cannot
  sign a SigV4 request on its own.
- **AWS IAM**: the runtime's execution role and the Lambda's invocation role.
- **Amazon S3**: the source bucket AgentCore's direct code deploy builds from.
- The **Strands Agents SDK**, using `Graph` rather than `Swarm`, because every record moves
  through the same five stations in the same order and nothing needs to hand control back.

## What we learned

The most useful thing we found was not a win, it was a boundary. A tuned two-clause rule
(parcel exact, or title cosine at or above 0.97 with a terminal prior status) matches the
Continuity Agent's accuracy on our 50 hand-labeled pairs exactly, both scoring 100%. We say
that plainly rather than let a judge find it, because it is the strongest objection to the
whole project.

The interesting result is the per-tier split. Baltimore's legislation splits cleanly into
two kinds of continuation: 28 pairs that share a parcel, and 22 that do not (shared sponsor
and near-identical titles instead). A parcel lookup alone is perfect on the parcel tier, 8
of 8 true continuations found, because it is deterministic code doing exactly the job it was
built for. On the citywide tier the same lookup finds 0 of 11 true continuations, because
those records name no property at all: a charter amendment on term limits, a tipped-wage
bill, a conservation district. 11 of the 19 true continuations in our set, 58%, have no
parcel anywhere in them. That is the majority of the problem a parcel lookup is structurally
blind to, and it is exactly where a language model reasoning over a feature table earns its
place instead of a database join.

We also ran an ablation: strip every domain-specific hint out of the Continuity Agent's
prompt, keep only the task, the schema, and an instruction not to invent facts. Accuracy
fell from 100% (50/50) to 94% (47/50), still above the 84% of the best single deterministic
feature gets on its own. The three cases the stripped prompt missed were a liquor license
matched to its own zoning approval, a charter amendment returning after a failed term, and
one street condemnation filed as two file numbers. Nothing in a feature table alone flags
those as one issue. Someone, or something, has to know how a city works.

## Challenges

Deployment surfaced three bugs that never show up locally. AgentCore Runtime's cold start
has a 30-second limit, and importing Strands, boto3, pydantic, and the OpenTelemetry distro
at module load time blew past it; every heavy import is now lazy, and module load is 0.3
seconds. Direct code deploy flattens the entrypoint into the image root rather than keeping
it one directory below a repo root, which broke a path assumption. Direct code deploy also
only packages the entrypoint's own directory, so the full corpus and the parcel gazetteer
never made it into the image; the runtime now ships a self-contained 329 KB bundle of the 50
labeled pairs with their prompts and feature tables, generated from the same source modules
so nothing drifts out of sync. Verified live: the runtime returns a correct decision on the
hero pair, continuation at 0.95, in about 9 seconds on Sonnet 4.5.

Getting a public endpoint in front of the runtime hit an account-level wall: Lambda function
URLs with `AuthType: NONE` return 403 in this account even with the documented public-access
policy attached byte for byte. The Lambda itself works, verified by direct invocation; the
public route needs an HTTP API instead of a function URL, and that is recorded as an open
item rather than worked around with something that would misrepresent what is actually
running.

## What is next

since the current build recomputes its view of the corpus from the cached snapshot on every
run and keeps no state between runs. A larger, independently labeled evaluation set, since
50 pairs assembled by one person is what our corpus of 1,679 records supports honestly, not
what would be needed to settle the open question the ablation raises about how the agent's
reasoning holds on patterns absent from this set.

## Limitations

Stated here rather than left for a judge to find.

- **One city, one source.** Baltimore City Council legislation via Legistar. Zoning appeals,
  liquor licenses, and tax sale run through three other Baltimore agencies and are out of
  scope.
- **A small evaluation population.** 50 hand-labeled pairs, 19 of them continuations. A
  tuned two-clause rule reproduces the same labels exactly, and both the rule and that fact
  are published, not hidden.
- **The labels are one person's judgment**, assigned by reading the source documents.
- **AgentCore Memory is not wired up.** Issue timelines are rebuilt from the cached corpus
  on every run and do not persist between runs. The deployment config records
  `mode: NO_MEMORY`.
- **The live endpoint is deliberately small.** Anyone can invoke the deployed agent from the
  site, but only on one of the 50 labeled pairs, at 0.1 requests a second and 300 live calls a
  day, after which it returns the cached decision and says so. It is there so a judge can check
  that the system runs, not to serve traffic.
- **Quorum never submits.** It drafts a comment and stops. That is a design decision, not a
  missing feature.
