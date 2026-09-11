# Perturbation results

Each transform in eval/perturbations.py is applied to the newer record's title in all 50 labeled pairs, the comparison features are recomputed, and every rule in BASELINES is re-scored against the same, unchanged labels. A label preserving transform that flips accuracy is evidence the rule is reading formatting noise rather than the underlying fact.

Rows marked cached, not re-run report the accuracy of the Continuity Agent decisions already on file, unchanged, because the perturbation was not sent to the model. That row cannot show an effect by construction, and it is kept only for side by side comparison with the deterministic rows.

Pass --perturb-agent to spend real model calls and re-run the agent live, but only on direction abbreviation, the one transform above that actually changes the feature table (it moves title cosine and nothing else). The other four transforms are proven inert on every deterministic rule in the table above, including the ones that read title cosine, so re-running the agent on them would spend model calls to confirm something already shown by simpler means. They stay cached and are documented here as negative controls, not as untested claims.

## Transforms and where they come from

| Transform | Corpus example |
|---|---|
| direction abbreviation | 23-0411 titles the property 'East Cold Spring Lane'; 26-0148, the reintroduction of the same bill, titles it 'E Cold Spring Lane'. |
| dash style normalization | 23-0411 opens with a hyphen after 'Rezoning'; 26-0148, the reintroduction of the same bill, opens with an en dash character there instead. 254 of 1679 corpus titles carry an en dash. |
| zoning code spacing | 23-0411 writes the zoning code as 'R-1-C'; 26-0148 writes the same code as 'R 1 C'. 21-0011 ('C-1-E') and 24-0474 ('A-56-A') show the hyphenated style elsewhere in the corpus. |
| lot list reorder | 23-0411 lists 'Lots 001, 002, 003'; 22-0321 lists five lots ('Lots 043, 044, 045, 046, 047') in a single fixed order, the same kind of list this transform reverses. |
| boilerplate preamble stripped | 154 of 1679 corpus titles carry the phrase 'as outlined in red on the accompanying plat'; the remaining 1525, including every non zoning record type, carry no such preamble, so its absence is a realistic formatting variant and not an invented one. |

## Accuracy by transform and rule

| Transform | Titles changed | Rule | Accuracy before | Accuracy after | Delta |
|---|---|---|---|---|---|
| direction abbreviation | 12 | always continuation | 38% | 38% | +0.000 |
| direction abbreviation | 12 | parcel exact | 78% | 78% | +0.000 |
| direction abbreviation | 12 | parcel exact AND owner unchanged | 78% | 78% | +0.000 |
| direction abbreviation | 12 | title cosine >= 0.90 | 64% | 60% | -0.040 |
| direction abbreviation | 12 | title cosine >= 0.99 | 70% | 64% | -0.060 |
| direction abbreviation | 12 | shared sponsor | 46% | 46% | +0.000 |
| direction abbreviation | 12 | prior terminal | 84% | 84% | +0.000 |
| direction abbreviation | 12 | parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 96% | -0.040 |
| direction abbreviation | 12 | Continuity Agent (re-run live) | 100% | 100% | +0.000 |
| dash style normalization | 16 | always continuation | 38% | 38% | +0.000 |
| dash style normalization | 16 | parcel exact | 78% | 78% | +0.000 |
| dash style normalization | 16 | parcel exact AND owner unchanged | 78% | 78% | +0.000 |
| dash style normalization | 16 | title cosine >= 0.90 | 64% | 64% | +0.000 |
| dash style normalization | 16 | title cosine >= 0.99 | 70% | 70% | +0.000 |
| dash style normalization | 16 | shared sponsor | 46% | 46% | +0.000 |
| dash style normalization | 16 | prior terminal | 84% | 84% | +0.000 |
| dash style normalization | 16 | parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 100% | +0.000 |
| dash style normalization | 16 | Continuity Agent (cached, not re-run) | 100% | 100% | +0.000 |
| zoning code spacing | 0 | always continuation | 38% | 38% | +0.000 |
| zoning code spacing | 0 | parcel exact | 78% | 78% | +0.000 |
| zoning code spacing | 0 | parcel exact AND owner unchanged | 78% | 78% | +0.000 |
| zoning code spacing | 0 | title cosine >= 0.90 | 64% | 64% | +0.000 |
| zoning code spacing | 0 | title cosine >= 0.99 | 70% | 70% | +0.000 |
| zoning code spacing | 0 | shared sponsor | 46% | 46% | +0.000 |
| zoning code spacing | 0 | prior terminal | 84% | 84% | +0.000 |
| zoning code spacing | 0 | parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 100% | +0.000 |
| zoning code spacing | 0 | Continuity Agent (cached, not re-run) | 100% | 100% | +0.000 |
| lot list reorder | 2 | always continuation | 38% | 38% | +0.000 |
| lot list reorder | 2 | parcel exact | 78% | 78% | +0.000 |
| lot list reorder | 2 | parcel exact AND owner unchanged | 78% | 78% | +0.000 |
| lot list reorder | 2 | title cosine >= 0.90 | 64% | 64% | +0.000 |
| lot list reorder | 2 | title cosine >= 0.99 | 70% | 70% | +0.000 |
| lot list reorder | 2 | shared sponsor | 46% | 46% | +0.000 |
| lot list reorder | 2 | prior terminal | 84% | 84% | +0.000 |
| lot list reorder | 2 | parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 100% | +0.000 |
| lot list reorder | 2 | Continuity Agent (cached, not re-run) | 100% | 100% | +0.000 |
| boilerplate preamble stripped | 19 | always continuation | 38% | 38% | +0.000 |
| boilerplate preamble stripped | 19 | parcel exact | 78% | 78% | +0.000 |
| boilerplate preamble stripped | 19 | parcel exact AND owner unchanged | 78% | 78% | +0.000 |
| boilerplate preamble stripped | 19 | title cosine >= 0.90 | 64% | 64% | +0.000 |
| boilerplate preamble stripped | 19 | title cosine >= 0.99 | 70% | 70% | +0.000 |
| boilerplate preamble stripped | 19 | shared sponsor | 46% | 46% | +0.000 |
| boilerplate preamble stripped | 19 | prior terminal | 84% | 84% | +0.000 |
| boilerplate preamble stripped | 19 | parcel exact OR (cosine >= 0.97 AND prior terminal) | 100% | 100% | +0.000 |
| boilerplate preamble stripped | 19 | Continuity Agent (cached, not re-run) | 100% | 100% | +0.000 |

## Pairs where a transform flipped a rule's decision

| Transform | Rule | Pair | Label | Cosine before | Cosine after |
|---|---|---|---|---|---|
| direction abbreviation | title cosine >= 0.90 | 35 | continuation | 0.971 | 0.826 |
| direction abbreviation | title cosine >= 0.90 | 40 | continuation | 1.0 | 0.899 |
| direction abbreviation | title cosine >= 0.99 | 5 | continuation | 1.0 | 0.979 |
| direction abbreviation | title cosine >= 0.99 | 16 | continuation | 1.0 | 0.93 |
| direction abbreviation | title cosine >= 0.99 | 40 | continuation | 1.0 | 0.899 |
| direction abbreviation | parcel exact OR (cosine >= 0.97 AND prior terminal) | 35 | continuation | 0.971 | 0.826 |
| direction abbreviation | parcel exact OR (cosine >= 0.97 AND prior terminal) | 40 | continuation | 1.0 | 0.899 |

Every flip above happened without changing which parcel, sponsor, or status the record names. Only the surface form of the title moved.


## Continuity Agent, re-run live under perturbation

On direction abbreviation, the agent was re-run on all 50 perturbed pairs with real model calls. Accuracy went from 100% to 100%, a delta of +0.000.

Confidence moved on 7 of 50 pairs, mean delta -0.0006, largest single move 0.030. Confidence moved in both directions on this set, not only downward, so this is not read as one-sided degradation; it is read as the model noticing the title changed and adjusting how much weight it gave it, without changing what it decided.

No individual decision flipped. Confidence may still have moved; decision, the number that accuracy is computed from, did not.

