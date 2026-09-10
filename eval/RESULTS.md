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

The 50 pairs are split into a tune half (24) and a test half (26), stratified on (tier, label) and assigned by a sha256 hash of the pair id, so the split is the same every time this runs and was not chosen by looking at which pairs are easy. The two clause rule's cosine threshold is swept on the tune half only, frozen at **0.900** (tune accuracy 100%), and every number below is that frozen rule and every other rule scored on the test half, which the threshold never saw.

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
| parcel exact OR (cosine >= 0.900 AND prior terminal), threshold frozen from tune half | 96% | 0.91 | 1.00 | 0.95 |
| Continuity Agent, cached decisions | 100% | 1.00 | 1.00 | 1.00 |

The row above labelled 'threshold frozen from tune half' is the honest version of the tuned two clause rule: its threshold was never allowed to see the test half it is scored on. Compare its test accuracy to the 100% the same rule shape gets when tuned on all 50 pairs at once. Any drop here is the amount of that 100% that was an artefact of tuning on the evaluation set, not a property of the rule.

