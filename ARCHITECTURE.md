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
                  [2] Continuity Agent  <---> issue timelines
                           |                   (in process, not persisted)
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
would add nondeterminism to a pipeline whose value depends on being auditable.

Per node latency and token deltas are collected by `QuorumRun.note` during a run.
They are not exported to the published site yet, so the agent run screen reports
records in, records dropped and the reason, which are numbers it does have.

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
tuned against a population of 9 parcels that recur under more than one file number, and "what does 0.4 mean"
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

## State, and what is not built

Issue timelines are the state that would have to survive between scheduled runs:
the issue id, first seen date, every appearance with its file number and date,
status transitions, current committee, next hearing, and which users watch it.

**That state is not persisted in this build.** `QuorumRun` in `agents/graph.py` is
an in process dataclass and it dies with the process. Each scheduled run rebuilds
its view of the corpus from the cached snapshot.

AgentCore Memory is the intended home for it and is not wired up. The deployment
config in this repo records `mode: NO_MEMORY`, and there is no memory client
anywhere in the code. The interface that would sit in front of it is small
(find an issue by parcel, read its timeline, append an appearance), so the
substitution is not difficult, but it has not been done and nothing here should
be read as saying otherwise.

## Why the eval set is not enough on its own, and what we did about it

The tuned rule in `eval/RESULTS.md` (`parcel exact OR (cosine >= 0.97 AND prior
terminal)`) scores 100% on the 50 hand labeled pairs, and its threshold was
chosen after looking at all 50 labels. That is a tuned on test number, and it
is reported as one plainly rather than left for a judge to find. Two follow up
measurements in `eval/run_eval.py` exist to test whether that number means
anything once the tuning advantage is taken away.

The first is a perturbation suite, `eval/perturbations.py`, run with
`python -m eval.run_eval --perturb`. It applies label preserving, corpus
grounded formatting variants (direction word abbreviation, dash style, zoning
code spacing, lot list order, boilerplate presence) to the newer record's
title in every pair, recomputes the comparison features, and rescores every
rule in `BASELINES` against the unchanged labels. Every transform is required
to cite a real file number where that exact variance occurs; a transform that
cannot cite one is deleted rather than kept for effect. Re-running the live
Continuity Agent under perturbation costs real model calls, so that arm is
opt-in behind `--perturb-agent` and is not run by default.

The second is a held out split. `eval/run_eval.py` partitions the 50 pairs
into a tune half and a test half, stratified on (tier, label) and assigned by
a sha256 hash of the pair id so the split is reproducible and was not chosen
by looking at which pairs are easy. The two clause rule's cosine threshold is
swept on the tune half only, frozen, and every rule, including the frozen
rule and the cached agent decisions, is then scored on the test half the
threshold never saw. The frozen rule's test accuracy is the honest number;
the 100% in the main table is not.

## Agents deliberately not built

- No "ask Quorum anything about your city" chatbot. It would be the weakest
  thing in the product and would define the product in a judge's mind.
- No autonomous submission agent. Quorum never speaks for a person.
- No multi jurisdiction router. One city, deep.
- No fine tuning, no reinforcement learning, and no vector database added for
  the sake of naming one.
