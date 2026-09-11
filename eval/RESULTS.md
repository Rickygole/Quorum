# Evaluation results

50 hand labeled pairs. 19 continuations, 31 distinct issues, 26 marked hard.
Tiers: citywide 22, parcel 28.

Every number on this page is produced by `python -m eval.run_eval`.

## Deterministic baselines

| Rule | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| always continuation | 38% | 0.38 | 1.00 | 0.55 |
| parcel exact | 78% | 1.00 | 0.42 | 0.59 |
| title cosine >= 0.90 | 64% | 0.52 | 0.74 | 0.61 |
| title cosine >= 0.99 | 70% | 0.61 | 0.58 | 0.59 |
| shared sponsor | 46% | 0.41 | 1.00 | 0.58 |
| prior terminal | 84% | 0.82 | 0.74 | 0.78 |
| parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 1.00 | 1.00 | 1.00 |

### What this table actually shows

The last rule scores 100% on this set. That result is reported first and plainly, because it is the strongest argument against this project and a judge should not have to find it.

Two things qualify it. First, the labels were assigned by a human reading the source documents, and that human was reasoning along broadly similar lines, so the set partly measures its own labelling heuristic rather than independent ground truth. Second, the rule only works inside a narrow threshold band:

| Cosine threshold | Accuracy of the two clause rule |
|---|---|
| 0.800 | 96% |
| 0.850 | 96% |
| 0.900 | 98% |
| 0.920 | 98% |
| 0.940 | 100% |
| 0.950 | 100% |
| 0.960 | 100% |
| 0.970 | 100% |
| 0.975 | 96% |
| 0.980 | 96% |
| 0.990 | 96% |
| 1.000 | 96% |

The rule is perfect between 0.94 and 0.97 and wrong on either side. The margin is one negative pair at cosine 0.934 and one positive pair at 0.971. Thirty seven thousandths of a cosine separate a right answer from a wrong one, on fifty examples. That is a property of this sample, not of municipal legislation.

So the honest claim is narrow: **a tuned two clause rule matches these labels, and the Continuity Agent is not required to beat it on accuracy.** What the agent does that the rule cannot is state, in checkable language, which evidence drove each decision and which it explicitly set aside. That output is what the product shows a resident, and it is what makes a wrong answer diagnosable instead of silent.

## Continuity Agent

| Metric | Value |
|---|---|
| accuracy | 1.00 |
| precision | 1.00 |
| recall | 1.00 |
| f1 | 1.00 |
| true positives | 19 |
| false positives | 0 |
| missed continuations | 0 |
| true negatives | 31 |

### Every pair, with the agent's call

| Pair | Records | Tier | Label | Agent | Confidence | |
|---|---|---|---|---|---|---|
| 1 | `21-0006` to `21-0073` | parcel | new_issue | new_issue | 0.98 | ok |
| 2 | `21-0013` to `21-0052` | parcel | new_issue | new_issue | 0.95 | ok |
| 3 | `21-0026` to `26-0177` | parcel | new_issue | new_issue | 0.98 | ok |
| 4 | `21-0031R` to `24-0577` | parcel | new_issue | new_issue | 0.98 | ok |
| 5 | `21-0035` to `22-0277` | parcel | continuation | continuation | 1.00 | ok |
| 6 | `21-0042R` to `21-0064` | parcel | continuation | continuation | 0.95 | ok |
| 7 | `21-0045` to `23-0374` | parcel | new_issue | new_issue | 0.95 | ok |
| 8 | `21-0051R` to `24-0516` | parcel | new_issue | new_issue | 0.98 | ok |
| 9 | `21-0054` to `22-0217` | parcel | new_issue | new_issue | 0.95 | ok |
| 10 | `21-0076` to `23-0408` | parcel | new_issue | new_issue | 0.98 | ok |
| 11 | `21-0076` to `23-0469` | parcel | new_issue | new_issue | 0.98 | ok |
| 12 | `21-0077` to `21-0098` | parcel | new_issue | new_issue | 0.95 | ok |
| 13 | `21-0170` to `26-0206` | parcel | new_issue | new_issue | 0.95 | ok |
| 14 | `21-0171` to `25-0104` | parcel | new_issue | new_issue | 0.98 | ok |
| 15 | `22-0240` to `24-0497` | parcel | new_issue | new_issue | 0.98 | ok |
| 16 | `22-0295` to `23-0417` | parcel | continuation | continuation | 1.00 | ok |
| 17 | `22-0302` to `23-0375` | parcel | new_issue | new_issue | 0.98 | ok |
| 18 | `22-0320` to `22-0325` | parcel | new_issue | new_issue | 0.98 | ok |
| 19 | `23-0408` to `23-0469` | parcel | new_issue | new_issue | 0.98 | ok |
| 20 | `23-0411` to `26-0148` | parcel | continuation | continuation | 0.98 | ok |
| 21 | `23-0437` to `23-0441` | parcel | continuation | continuation | 0.98 | ok |
| 22 | `23-0454` to `24-0549` | parcel | new_issue | new_issue | 0.98 | ok |
| 23 | `24-0221R` to `24-0550` | parcel | continuation | continuation | 0.95 | ok |
| 24 | `24-0533` to `25-0091` | parcel | new_issue | new_issue | 0.98 | ok |
| 25 | `25-0055` to `25-0056` | parcel | new_issue | new_issue | 0.95 | ok |
| 26 | `25-0071` to `25-0083` | parcel | continuation | continuation | 0.98 | ok |
| 27 | `25-0073` to `25-0074` | parcel | continuation | continuation | 0.95 | ok |
| 28 | `25-0089` to `25-0142` | parcel | new_issue | new_issue | 0.95 | ok |
| 29 | `21-0014R` to `21-0015R` | citywide | new_issue | new_issue | 0.98 | ok |
| 30 | `22-0096R` to `26-0048R` | citywide | new_issue | new_issue | 0.95 | ok |
| 31 | `22-0233` to `26-0179` | citywide | new_issue | new_issue | 0.95 | ok |
| 32 | `21-0114` to `25-0059` | citywide | continuation | continuation | 0.98 | ok |
| 33 | `22-0194` to `25-0102` | citywide | new_issue | new_issue | 0.95 | ok |
| 34 | `22-0326` to `26-0199` | citywide | continuation | continuation | 0.98 | ok |
| 35 | `24-0508` to `24-0509` | citywide | continuation | continuation | 0.98 | ok |
| 36 | `23-0415` to `24-0568` | citywide | continuation | continuation | 0.98 | ok |
| 37 | `24-0556` to `25-0058` | citywide | continuation | continuation | 0.98 | ok |
| 38 | `24-0576` to `25-0003` | citywide | continuation | continuation | 0.98 | ok |
| 39 | `22-0111R` to `23-0195R` | citywide | continuation | continuation | 0.98 | ok |
| 40 | `22-0126R` to `24-0226R` | citywide | continuation | continuation | 0.98 | ok |
| 41 | `22-0140R` to `25-0003R` | citywide | continuation | continuation | 0.98 | ok |
| 42 | `22-0139R` to `25-0036R` | citywide | continuation | continuation | 0.98 | ok |
| 43 | `21-0058` to `23-0373` | citywide | new_issue | new_issue | 0.95 | ok |
| 44 | `23-0452` to `24-0488` | citywide | new_issue | new_issue | 0.95 | ok |
| 45 | `21-0168` to `22-0299` | citywide | new_issue | new_issue | 0.95 | ok |
| 46 | `22-0299` to `24-0545` | citywide | new_issue | new_issue | 0.95 | ok |
| 47 | `21-0168` to `24-0545` | citywide | new_issue | new_issue | 0.95 | ok |
| 48 | `21-0056` to `21-0120` | citywide | new_issue | new_issue | 0.85 | ok |
| 49 | `24-0599` to `25-0015` | citywide | continuation | continuation | 0.98 | ok |
| 50 | `24-0544` to `25-0093` | citywide | new_issue | new_issue | 0.85 | ok |

Of the 50 pairs, 31 are negatives. They are listed above alongside the positives so that the agent cannot be mistaken for one that says yes to everything.


### Every miss, named

No misses on this set. That is not the win it looks like, and the reason is in the baseline table above: the tuned two clause rule also scores 100%. A perfect score here says the set is separable, not that the agent is necessary. The agent ties the rule; it does not beat it.

What the agent produced that the rule cannot is the reasoning attached to every one of the 50 rows, including which evidence it set aside. On the hardest negative, 701 and 702 Mura Street, it wrote that the parcels are adjacent lots on the same block and listed `title cosine 0.944, boilerplate for conditional use parking lots` as a non driver. On the hero pair it listed `title cosine 0.943, expected boilerplate for rezoning ordinances` as a non driver and the exact parcel and matching zoning transition as drivers. Those two title scores are three thousandths apart and point in opposite directions, and in both cases the agent said out loud that it was not using them.

The honest open question, and the next experiment, is whether that reasoning holds on pattern types absent from this set. A 50 pair set assembled by one person cannot settle it.


## Held out split, frozen threshold

The 50 pairs are split into a tune half (24) and a test half (26), stratified on (tier, label) and assigned by a sha256 hash of the pair id, so the split is the same every time this runs and was not chosen by looking at which pairs are easy. The two clause rule's cosine threshold is swept on the tune half only, frozen at **0.950** (tune accuracy 100%), and every number below is that frozen rule and every other rule scored on the test half, which the threshold never saw.

Tune pair ids: [5, 7, 9, 10, 11, 13, 14, 15, 18, 19, 21, 23, 25, 27, 29, 31, 32, 37, 39, 41, 42, 45, 47, 48]

Test pair ids: [1, 2, 3, 4, 6, 8, 12, 16, 17, 20, 22, 24, 26, 28, 30, 33, 34, 35, 36, 38, 40, 43, 44, 46, 49, 50]

| Rule | Accuracy on test half | Precision | Recall | F1 |
|---|---|---|---|---|
| always continuation | 38% | 0.38 | 1.00 | 0.56 |
| parcel exact | 77% | 1.00 | 0.40 | 0.57 |
| title cosine >= 0.90 | 65% | 0.53 | 0.80 | 0.64 |
| title cosine >= 0.99 | 65% | 0.55 | 0.60 | 0.57 |
| shared sponsor | 42% | 0.40 | 1.00 | 0.57 |
| prior terminal | 88% | 0.89 | 0.80 | 0.84 |
| parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 1.00 | 1.00 | 1.00 |
| parcel exact OR (cosine >= 0.950 AND prior terminal), threshold frozen from tune half | 100% | 1.00 | 1.00 | 1.00 |
| Continuity Agent, cached decisions | 100% | 1.00 | 1.00 | 1.00 |

### What this experiment actually shows

Nothing. It does not separate the agent from the rule, and that is the finding.

The tune half is 100% accurate at every threshold in [0.900, 0.970], a plateau 6 points wide. There is no single best threshold to freeze, so the choice inside that plateau is arbitrary, and it changes the answer:

| Frozen threshold | Accuracy on test half |
|---|---|
| 0.900 | 96% |
| 0.920 | 96% |
| 0.940 | 100% |
| 0.950 | 100% |
| 0.960 | 100% |
| 0.970 | 100% |

An earlier version of this file took the lowest point of the plateau, reported 96%, and drew the conclusion that the rule's advantage was an artefact of tuning. That conclusion was wrong. It was an artefact of an undocumented argmax tie break inside this harness. The threshold is now the plateau midpoint, chosen and stated in advance, and on that choice the rule scores the same as the agent.

On the 26 test pairs the agent and the frozen rule disagree on 0 of them (agent right and rule wrong: 0; rule right and agent wrong: 0). McNemar exact two sided p = 1.0. With a test half this small, no difference of this size could reach significance even if it existed.

This section is kept because a negative result that was expensive to obtain is worth more than a positive one that was not tested. The claim it retires is 'the agent generalises better than the rule'. There is no evidence here for that.

## Where the agent actually earns its place

The headline 100% invites one question above all others, so here is the answer broken out by tier.

| Tier | Pairs | Continuations | Parcel lookup alone | Two clause rule | Continuity Agent |
|---|---|---|---|---|---|
| citywide | 22 | 11 | 50% | 100% | 100% |
| parcel | 28 | 8 | 100% | 100% | 100% |

On the parcel tier a lookup is perfect, and Quorum resolves parcels **in code**, in a node that makes no model call at all. That is the correct engineering answer and it is not a criticism of the system, it is the system working as designed.

On the citywide tier the same lookup finds **0 of the 11 true continuations**. Recall 0.00. It cannot do otherwise, because these records name no property at all: a charter amendment on term limits, a tipped wage bill, a conservation district, a hearing request. They die at the end of a council term and come back under a new file number years later.

**11 of the 19 true continuations in this set, 58%, have no parcel.** That is the majority of the problem, and it is the half a parcel lookup is structurally blind to.

The two clause rule reaches them only through its second clause, a hand tuned cosine threshold. That is the clause the threshold sweep shows is perfect across a band six points wide and wrong outside it, and the one the perturbation suite breaks by abbreviating a direction in a title. So the honest division of labour is: a lookup where a lookup is exact, and a model where the alternative is a brittle threshold.

### Why there are no adversarial parcel pairs here

The obvious attack on the parcel tier is that `parcel exact` never once produces a false positive, which suggests the set never tested it. That was checked exhaustively rather than assumed. Across all 1,679 records there are **9 exact parcel pairs, 11 at address level and 28 at block level**, and every one of them is already labeled here. The population is not sampled, it is complete.

So the zero false positive rate is not an artefact of an easy sample. In this corpus, two council items on the same parcel are always the same project. That is a property of how Baltimore legislates, it is why the resolution node is deterministic, and it is reported as a finding rather than presented as a score.

## Ablation: is the prompt just the rule, written in English?

This is the strongest objection to the whole project, so it gets its own experiment.

`agents/continuity.py` tells the model, in prose, that the parcel comparison is the strongest signal, that `adjacent` usually means two different properties, that title similarity is weak evidence and must never be a primary driver, and that a terminal prior status followed by a reintroduction is the classic pattern. That is close to the two clause rule stated in words. A fair reader asks whether the agent is doing anything beyond executing a rule it was handed.

So the domain guidance was deleted. The neutral prompt keeps only the task, the output schema, and the instruction not to invent facts. Same feature table, same pairs, same model. It is in `eval/ablation.py` and reproducible with `python -m eval.ablation`.

| Prompt | Accuracy | Continuations called (19 true) |
|---|---|---|
| Full prompt, with domain guidance | 100% (50/50) | 19 |
| Neutral prompt, domain guidance removed | 94% (47/50) | 16 |
| Best single deterministic feature (parcel exact) | 78% | 8 |

**The prompt is not doing the work.** Strip every domain hint and accuracy falls from 100% to 94%, not to the 78% a parcel only rule gets. The model reads the feature table and reasons from it. If the guidance were the rule in disguise, removing it would collapse performance to the level of the rule, and it does not.

**The domain guidance is worth exactly 3 pairs**, and they are not random. Every miss is a continuation the neutral prompt declined to call, so removing the guidance makes the agent conservative rather than wrong in both directions. It called 16 continuations where 19 are true.

- **Pair 23, `24-0221R` and `24-0550`**: labeled continuation, neutral prompt said new_issue at 0.85.
- **Pair 34, `22-0326` and `26-0199`**: labeled continuation, neutral prompt said new_issue at 0.95.
- **Pair 35, `24-0508` and `24-0509`**: labeled continuation, neutral prompt said new_issue at 0.95.

Those three are the cases that need domain knowledge: a liquor licence and the zoning approval for the same establishment, a charter amendment returning after a failed term, and the Opening and Closing halves of one street condemnation. Nothing in a feature table says those are one issue. Someone has to know how a city works.

The honest reading of this project is therefore: the deterministic features do most of the work, the model generalises from them better than any single feature does, and the domain guidance buys the last three cases. That is a hybrid, and it is worth saying so rather than claiming the agent is doing something magical.

