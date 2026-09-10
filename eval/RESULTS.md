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

Not yet run against a model provider. This section is published empty rather than omitted, so that the baselines above cannot be mistaken for agent results.

