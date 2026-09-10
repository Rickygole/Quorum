# Architecture

```
              Legistar Web API (cached, timestamped)
                            |
                   [ Ingestion adapters ]
                            |
                    Normalized CivicRecord
                            |
              +-------------+-------------+
              |                           |
        [1] Civic Analyst          Parcel gazetteer
           (Strands Agent)      (237,092 parcels, static)
              |                           |
              +------------+--------------+
                           |
                  [R] Resolution node (code, not an agent)
                           |
                  [2] Continuity Agent  <---> AgentCore Memory
                           |                   (issue timelines)
                  [3] Relevance Agent
                           |
                  [4] Action Agent
                           |
                    Human approval gate
                           |
                       (stops here)
```

## Why a Strands Graph and not a Swarm

The execution path is deterministic and dependency ordered. Every record goes
through the same five stations in the same order, and no station needs to hand
control back to a station behind it. That is what `Graph` is for.

`Swarm` exists for dynamic handoff between agents that decide among themselves
who works next. Quorum has no such decision to make. Reaching for a Swarm here
would add nondeterminism to a pipeline whose value depends on being auditable,
and would make the per node latency and token numbers on the agent run screen
meaningless.

## Why resolution is code and not an agent

Address normalization and block/lot parsing are solved deterministic problems.
A language model asked to normalize "205-209 E Cold Spring Lane" will
occasionally return a plausible and wrong block number, and a hallucinated
parcel identifier is the one error in this system that a user cannot detect.

So resolution is a `CustomNode` inside the Graph. It sits in the same
orchestration surface, appears on the agent run screen with the others, and
carries no model call. The agent budget is spent where judgment is actually
required.

Four agents, one deterministic node. Not seven.

## Why the Continuity Agent adjudicates a feature table

The naive version asks a model whether two records are the same issue. The
answer cannot be interrogated, and neither can an embedding similarity score.

The weighted numeric alternative was also rejected. Weights cannot be honestly
tuned against a population of 13 multi file cases, and "what does 0.4 mean"
has no good answer when a judge asks it.

Quorum computes comparison features in code, hands the table to the agent as
evidence, and requires the agent to name which features drove the decision and
which it explicitly did not rely on.

That last part is load bearing, and the corpus proves why. Measured on the two
canonical cases:

| | 26-0148 vs 23-0411 (same issue) | 25-0056 vs 25-0055 (different issues) |
|---|---|---|
| Parcel | `exact`, 5053I001 | `adjacent`, block 1155, lots 070 vs 101 |
| Zoning transition | R1C to EC2, both | none |
| Prior status | Failed, End of Term (`restart`) | Enacted |
| Sponsor | identical | identical |
| **Title cosine** | **0.943** | **0.944** |

Title similarity is *higher* for the pair that is not a continuation. Any
system deciding this on string or embedding similarity gets both cases wrong.
What separates them is the parcel comparison, the terminal status of the prior
item, and the zoning transition, and the agent is required to say so.

## Features computed

| Feature | Values |
|---|---|
| `parcel` | exact, adjacent, none, with shared ids, blocks or street |
| `sponsor` | overlap set and Jaccard |
| `requester` | match, both raw values |
| `title` | token Jaccard, cosine, distinctive shared tokens |
| `zoning_transition` | normalized from and to districts, match |
| `record_type` | match |
| `temporal` | gap in days, ordering, same council term |
| `committee_progression` | restart, advance, regression, unknown |
| `file_number` | identical or not |

`adjacent` is deliberately a separate value from `exact` rather than a point on
a similarity scale, because two neighbouring lots are the single most common
way for a naive matcher to be confidently wrong.

## State

Each resolved issue is a record in AgentCore Memory holding its id, first seen
date, every appearance with file number and date, status transitions, current
committee, next hearing, and which users watch it. The issue timeline is state
that must survive between scheduled runs, which is the honest reason for a
memory service rather than a checkbox one.

## Agents deliberately not built

- No "ask Quorum anything about your city" chatbot. It would be the weakest
  thing in the product and would define the product in a judge's mind.
- No autonomous submission agent. Quorum never speaks for a person.
- No multi jurisdiction router. One city, deep.
- No fine tuning, no reinforcement learning, and no vector database added for
  the sake of naming one.
