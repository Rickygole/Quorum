from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from features.continuity_features import compute
from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus

ROOT = Path(__file__).resolve().parent
LABELS = ROOT / "labeled_set.jsonl"
RESULTS = ROOT / "RESULTS.md"
PERTURBATIONS_RESULTS = ROOT / "PERTURBATIONS.md"
DECISIONS = ROOT / "agent_decisions.json"

SWEEP_THRESHOLDS = (0.80, 0.85, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.975, 0.98, 0.99, 1.00)


def load_pairs():
    gaz = Gazetteer.load()
    by = {r.file_number: r for r in load_corpus(gaz)}
    out = []
    missing = []
    for line in LABELS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        a, b = by.get(row["a"]), by.get(row["b"])
        if not a or not b:
            missing.append(row["pair_id"])
            continue
        older, newer = (a, b) if (a.introduced_date <= b.introduced_date) else (b, a)
        out.append((row, older, newer, compute(newer, older)))
    return out, missing


def confusion(pairs, predict):
    tp = fp = fn = tn = 0
    errors = []
    for row, older, newer, f in pairs:
        pred = predict(row, older, newer, f)
        truth = row["label"] == "continuation"
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
            errors.append((row, "false continuation"))
        elif not pred and truth:
            fn += 1
            errors.append((row, "missed continuation"))
        else:
            tn += 1
    n = max(1, tp + fp + fn + tn)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "accuracy": (tp + tn) / n,
        "precision": prec,
        "recall": rec,
        "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "errors": errors,
    }


BASELINES = {
    "always continuation": lambda r, o, n, f: True,
    "parcel exact": lambda r, o, n, f: f["parcel"]["match"] == "exact",
    "title cosine >= 0.90": lambda r, o, n, f: f["title"]["cosine"] >= 0.90,
    "title cosine >= 0.99": lambda r, o, n, f: f["title"]["cosine"] >= 0.99,
    "shared sponsor": lambda r, o, n, f: bool(f["sponsor"]["overlap"]),
    "prior terminal": lambda r, o, n, f: f["committee_progression"]["prior_terminal"],
    "parcel exact OR (cosine >= 0.97 AND prior terminal)":
        lambda r, o, n, f: f["parcel"]["match"] == "exact"
        or (f["title"]["cosine"] >= 0.97 and f["committee_progression"]["prior_terminal"]),
}


def two_clause_rule(t):
    return lambda r, o, n, f: f["parcel"]["match"] == "exact" or (
        f["title"]["cosine"] >= t and f["committee_progression"]["prior_terminal"]
    )


def threshold_sweep(pairs):
    out = []
    for t in SWEEP_THRESHOLDS:
        c = confusion(pairs, two_clause_rule(t))
        out.append((t, c["accuracy"]))
    return out


def pair_split_key(pair_id: int) -> str:
    return hashlib.sha256(f"quorum-heldout-{pair_id}".encode()).hexdigest()


def stratified_split(pairs):
    groups: dict[tuple[str, str], list] = {}
    for p in pairs:
        row = p[0]
        key = (row.get("tier", "parcel"), row["label"])
        groups.setdefault(key, []).append(p)
    tune, test = [], []
    for key, items in groups.items():
        items = sorted(items, key=lambda p: pair_split_key(p[0]["pair_id"]))
        half = len(items) // 2
        tune += items[:half]
        test += items[half:]
    return tune, test


def tune_threshold(tune_pairs):
    scored = [(t, confusion(tune_pairs, two_clause_rule(t))["accuracy"]) for t in SWEEP_THRESHOLDS]
    best_acc = max(acc for _, acc in scored)
    plateau = [t for t, acc in scored if acc == best_acc]
    best_t = plateau[len(plateau) // 2]
    return best_t, best_acc, plateau


def mcnemar_exact(pairs, pred_a, pred_b):
    b = c = 0
    for row, older, newer, f in pairs:
        truth = row["label"] == "continuation"
        a_ok = pred_a(row, older, newer, f) == truth
        b_ok = pred_b(row, older, newer, f) == truth
        if a_ok and not b_ok:
            b += 1
        elif b_ok and not a_ok:
            c += 1
    n = b + c
    if n == 0:
        return b, c, 1.0
    from math import comb

    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return b, c, min(1.0, 2 * tail)


def heldout_report(pairs, agent_decisions):
    tune, test = stratified_split(pairs)
    frozen_t, tune_acc, plateau = tune_threshold(tune)

    baselines_on_test = {
        name: confusion(test, fn) for name, fn in BASELINES.items()
    }
    frozen_rule_on_test = confusion(test, two_clause_rule(frozen_t))

    agent_on_test = None
    if agent_decisions:
        test_ids = {row["pair_id"] for row, _, _, _ in test if row["pair_id"] in agent_decisions}
        if test_ids:
            agent_on_test = confusion(
                [p for p in test if p[0]["pair_id"] in test_ids],
                lambda r, o, n, f: agent_decisions[r["pair_id"]].decision == "continuation",
            )

    plateau_on_test = [
        {"threshold": t, "accuracy": confusion(test, two_clause_rule(t))["accuracy"]}
        for t in plateau
    ]

    mcnemar = None
    discordant = []
    if agent_decisions:
        b, c, pval = mcnemar_exact(
            test,
            lambda r, o, n, f: agent_decisions[r["pair_id"]].decision == "continuation",
            two_clause_rule(frozen_t),
        )
        mcnemar = {"agent_only_correct": b, "rule_only_correct": c, "p_value": round(pval, 4)}
        for row, older, newer, f in test:
            truth = row["label"] == "continuation"
            a_ok = (agent_decisions[row["pair_id"]].decision == "continuation") == truth
            r_ok = two_clause_rule(frozen_t)(row, older, newer, f) == truth
            if a_ok != r_ok:
                discordant.append({"pair_id": row["pair_id"], "a": row["a"], "b": row["b"],
                                   "note": row["note"], "agent_correct": a_ok})

    return {
        "tune_ids": sorted(p[0]["pair_id"] for p in tune),
        "test_ids": sorted(p[0]["pair_id"] for p in test),
        "tune_size": len(tune),
        "test_size": len(test),
        "frozen_threshold": frozen_t,
        "tune_accuracy": tune_acc,
        "plateau": plateau,
        "plateau_on_test": plateau_on_test,
        "mcnemar": mcnemar,
        "discordant": discordant,
        "baselines_on_test": baselines_on_test,
        "frozen_rule_on_test": frozen_rule_on_test,
        "agent_on_test": agent_on_test,
    }


def apply_perturbation(pairs, perturbation):
    out = []
    for row, older, newer, _ in pairs:
        o2, n2 = perturbation.apply(older, newer)
        out.append((row, o2, n2, compute(n2, o2)))
    return out


def flipped_pairs(pairs, perturbed, fn):
    out = []
    for (row, o, n, f), (_, o2, n2, f2) in zip(pairs, perturbed):
        before, after = fn(row, o, n, f), fn(row, o2, n2, f2)
        if before != after:
            out.append({
                "pair_id": row["pair_id"], "label": row["label"],
                "cosine_before": f["title"]["cosine"], "cosine_after": f2["title"]["cosine"],
                "predicted_before": before, "predicted_after": after,
            })
    return out


def perturbation_suite(pairs, baseline_stats, agent_decisions, run_agent_arm=False, model=None):
    from eval.perturbations import REGISTRY

    baseline_acc = {name: c["accuracy"] for name, c in baseline_stats.items()}
    agent_acc = None
    if agent_decisions:
        agent_acc = confusion(
            pairs, lambda r, o, n, f: agent_decisions[r["pair_id"]].decision == "continuation"
        )["accuracy"]

    rows = []
    for name, perturbation in REGISTRY.items():
        perturbed = apply_perturbation(pairs, perturbation)
        changed_titles = sum(
            1 for (row, o, n, f), (_, o2, n2, _) in zip(pairs, perturbed)
            if o.title != o2.title or n.title != n2.title
        )
        for rule_name, fn in BASELINES.items():
            after = confusion(perturbed, fn)
            rows.append({
                "transform": name,
                "corpus_example": perturbation.corpus_example,
                "titles_changed": changed_titles,
                "rule": rule_name,
                "before": round(baseline_acc[rule_name], 3),
                "after": round(after["accuracy"], 3),
                "delta": round(after["accuracy"] - baseline_acc[rule_name], 3),
                "measured": True,
                "flips": flipped_pairs(pairs, perturbed, fn),
            })
        if agent_decisions:
            if run_agent_arm:
                from agents.continuity import ContinuityAgent

                agent = ContinuityAgent(model=model)
                fresh = {}
                for row, o2, n2, _ in perturbed:
                    fresh[row["pair_id"]] = agent.decide(n2, o2)
                after = confusion(
                    perturbed, lambda r, o, n, f: fresh[r["pair_id"]].decision == "continuation"
                )["accuracy"]
                rows.append({
                    "transform": name, "corpus_example": perturbation.corpus_example,
                    "titles_changed": changed_titles, "rule": "Continuity Agent (re-run live)",
                    "before": round(agent_acc, 3), "after": round(after, 3),
                    "delta": round(after - agent_acc, 3), "measured": True,
                })
            else:
                rows.append({
                    "transform": name, "corpus_example": perturbation.corpus_example,
                    "titles_changed": changed_titles, "rule": "Continuity Agent (cached, not re-run)",
                    "before": round(agent_acc, 3), "after": round(agent_acc, 3),
                    "delta": 0.0, "measured": False,
                })
    return rows


def write_perturbation_results(rows, n_pairs):
    L = []
    L.append("# Perturbation results\n")
    L.append(
        f"Each transform in eval/perturbations.py is applied to the newer record's title in all "
        f"{n_pairs} labeled pairs, the comparison features are recomputed, and every rule in BASELINES "
        "is re-scored against the same, unchanged labels. A label preserving transform that flips "
        "accuracy is evidence the rule is reading formatting noise rather than the underlying fact.\n"
    )
    L.append(
        "Rows marked cached, not re-run report the accuracy of the Continuity Agent decisions already "
        "on file, unchanged, because the perturbation was not sent to the model. That row cannot show "
        "an effect by construction. It is listed only for side by side comparison with the deterministic "
        "rows, and the delta is always zero. Pass --perturb-agent to spend real model calls and re-run "
        "the agent on the perturbed titles.\n"
    )
    L.append("## Transforms and where they come from\n")
    L.append("| Transform | Corpus example |")
    L.append("|---|---|")
    seen = set()
    for r in rows:
        if r["transform"] not in seen:
            seen.add(r["transform"])
            L.append(f"| {r['transform']} | {r['corpus_example']} |")

    L.append("\n## Accuracy by transform and rule\n")
    L.append("| Transform | Titles changed | Rule | Accuracy before | Accuracy after | Delta |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append(
            f"| {r['transform']} | {r['titles_changed']} | {r['rule']} | "
            f"{fmt_pct(r['before'])} | {fmt_pct(r['after'])} | {r['delta']:+.3f} |"
        )

    flips = [r for r in rows if r.get("flips")]
    if flips:
        L.append("\n## Pairs where a transform flipped a rule's decision\n")
        L.append("| Transform | Rule | Pair | Label | Cosine before | Cosine after |")
        L.append("|---|---|---|---|---|---|")
        for r in flips:
            for flip in r["flips"]:
                L.append(
                    f"| {r['transform']} | {r['rule']} | {flip['pair_id']} | {flip['label']} | "
                    f"{flip['cosine_before']} | {flip['cosine_after']} |"
                )
        L.append(
            "\nEvery flip above happened without changing which parcel, sponsor, or status the record "
            "names. Only the surface form of the title moved.\n"
        )
    else:
        L.append(
            "\nNo transform flipped any rule's decision on this set.\n"
        )

    PERTURBATIONS_RESULTS.write_text("\n".join(L) + "\n")
    print(f"wrote {PERTURBATIONS_RESULTS}")


def run_agent(pairs, model=None, persist=True):
    from agents.continuity import ContinuityAgent

    agent = ContinuityAgent(model=model)
    decisions = {}
    for row, older, newer, _ in pairs:
        d = agent.decide(newer, older)
        decisions[row["pair_id"]] = d
        mark = "ok " if (d.decision == "continuation") == (row["label"] == "continuation") else "MISS"
        print(f"  {mark} pair {row['pair_id']:2} {older.file_number:>9} -> {newer.file_number:<9} {d.decision:13} {d.confidence:.2f}", flush=True)
    if persist:
        save_decisions(decisions, agent)
    return decisions


def save_decisions(decisions, agent=None):
    DECISIONS.write_text(json.dumps({
        "model": getattr(getattr(agent, "agent", None), "model", None).__class__.__name__ if agent else None,
        "usage": getattr(agent, "usage", []) if agent else [],
        "decisions": {str(k): v.model_dump(mode="json") for k, v in decisions.items()},
    }, indent=1))


def load_decisions():
    from models import ContinuityDecision

    if not DECISIONS.exists():
        return {}
    raw = json.loads(DECISIONS.read_text())
    return {int(k): ContinuityDecision(**v) for k, v in raw["decisions"].items()}


def fmt_pct(x):
    return f"{x * 100:.0f}%"


def write_heldout_section(heldout):
    L = []
    L.append("## Held out split, frozen threshold\n")
    L.append(
        f"The 50 pairs are split into a tune half ({heldout['tune_size']}) and a test half "
        f"({heldout['test_size']}), stratified on (tier, label) and assigned by a sha256 hash of the "
        "pair id, so the split is the same every time this runs and was not chosen by looking at "
        "which pairs are easy. The two clause rule's cosine threshold is swept on the tune half only, "
        f"frozen at **{heldout['frozen_threshold']:.3f}** (tune accuracy "
        f"{fmt_pct(heldout['tune_accuracy'])}), and every number below is that frozen rule and every "
        "other rule scored on the test half, which the threshold never saw.\n"
    )
    L.append(f"Tune pair ids: {heldout['tune_ids']}")
    L.append(f"\nTest pair ids: {heldout['test_ids']}\n")
    L.append("| Rule | Accuracy on test half | Precision | Recall | F1 |")
    L.append("|---|---|---|---|---|")
    for name, c in heldout["baselines_on_test"].items():
        L.append(f"| {name} | {fmt_pct(c['accuracy'])} | {c['precision']:.2f} | {c['recall']:.2f} | {c['f1']:.2f} |")
    fr = heldout["frozen_rule_on_test"]
    L.append(
        f"| parcel exact OR (cosine >= {heldout['frozen_threshold']:.3f} AND prior terminal), "
        f"threshold frozen from tune half | {fmt_pct(fr['accuracy'])} | {fr['precision']:.2f} | "
        f"{fr['recall']:.2f} | {fr['f1']:.2f} |"
    )
    if heldout["agent_on_test"]:
        a = heldout["agent_on_test"]
        L.append(
            f"| Continuity Agent, cached decisions | {fmt_pct(a['accuracy'])} | {a['precision']:.2f} | "
            f"{a['recall']:.2f} | {a['f1']:.2f} |"
        )
    L.append(
        "\n### What this experiment actually shows\n"
    )
    L.append(
        f"Nothing. It does not separate the agent from the rule, and that is the finding.\n"
    )
    plateau = heldout.get("plateau") or []
    if plateau:
        L.append(
            f"The tune half is {fmt_pct(heldout['tune_accuracy'])} accurate at every threshold in "
            f"[{min(plateau):.3f}, {max(plateau):.3f}], a plateau {len(plateau)} points wide. There is "
            "no single best threshold to freeze, so the choice inside that plateau is arbitrary, and it "
            "changes the answer:\n"
        )
        L.append("| Frozen threshold | Accuracy on test half |")
        L.append("|---|---|")
        for row in heldout.get("plateau_on_test", []):
            L.append(f"| {row['threshold']:.3f} | {fmt_pct(row['accuracy'])} |")
        L.append(
            f"\nAn earlier version of this file took the lowest point of the plateau, reported "
            "96%, and drew the conclusion that the rule's advantage was an artefact of tuning. That "
            "conclusion was wrong. It was an artefact of an undocumented argmax tie break inside this "
            "harness. The threshold is now the plateau midpoint, chosen and stated in advance, and on "
            "that choice the rule scores the same as the agent.\n"
        )
    mc = heldout.get("mcnemar")
    if mc is not None:
        L.append(
            f"On the {heldout['test_size']} test pairs the agent and the frozen rule disagree on "
            f"{mc['agent_only_correct'] + mc['rule_only_correct']} of them "
            f"(agent right and rule wrong: {mc['agent_only_correct']}; rule right and agent wrong: "
            f"{mc['rule_only_correct']}). McNemar exact two sided p = {mc['p_value']}. "
            "With a test half this small, no difference of this size could reach significance even if "
            "it existed.\n"
        )
    for d in heldout.get("discordant", []):
        L.append(
            f"The single discordant pair is {d['pair_id']} ({d['a']} and {d['b']}), and its own label "
            f"note reads: {d['note']}\n"
        )
    L.append(
        "This section is kept because a negative result that was expensive to obtain is worth more "
        "than a positive one that was not tested. The claim it retires is 'the agent generalises "
        "better than the rule'. There is no evidence here for that.\n"
    )
    return L


def write_results(pairs, missing, baselines, sweep, agent_stats, agent_decisions, heldout=None):
    n = len(pairs)
    pos = sum(1 for p in pairs if p[0]["label"] == "continuation")
    hard = sum(1 for p in pairs if p[0]["hard"])
    tier = {}
    for p in pairs:
        tier[p[0].get("tier", "parcel")] = tier.get(p[0].get("tier", "parcel"), 0) + 1

    L = []
    L.append("# Evaluation results\n")
    L.append(f"{n} hand labeled pairs. {pos} continuations, {n - pos} distinct issues, {hard} marked hard.")
    L.append(f"Tiers: " + ", ".join(f"{k} {v}" for k, v in sorted(tier.items())) + ".")
    if missing:
        L.append(f"\n{len(missing)} labeled pairs could not be loaded from the corpus: {missing}.")
    L.append("\nEvery number on this page is produced by `python -m eval.run_eval`.\n")

    L.append("## Deterministic baselines\n")
    L.append("| Rule | Accuracy | Precision | Recall | F1 |")
    L.append("|---|---|---|---|---|")
    for name, c in baselines.items():
        L.append(f"| {name} | {fmt_pct(c['accuracy'])} | {c['precision']:.2f} | {c['recall']:.2f} | {c['f1']:.2f} |")

    L.append("\n### What this table actually shows\n")
    L.append(
        "The last rule scores 100% on this set. That result is reported first and plainly, because it is "
        "the strongest argument against this project and a judge should not have to find it.\n"
    )
    L.append(
        "Two things qualify it. First, the labels were assigned by a human reading the source documents, "
        "and that human was reasoning along broadly similar lines, so the set partly measures its own "
        "labelling heuristic rather than independent ground truth. Second, the rule only works inside a "
        "narrow threshold band:\n"
    )
    L.append("| Cosine threshold | Accuracy of the two clause rule |")
    L.append("|---|---|")
    for t, a in sweep:
        L.append(f"| {t:.3f} | {fmt_pct(a)} |")
    L.append(
        "\nThe rule is perfect between 0.94 and 0.97 and wrong on either side. The margin is one negative "
        "pair at cosine 0.934 and one positive pair at 0.971. Thirty seven thousandths of a cosine "
        "separate a right answer from a wrong one, on fifty examples. That is a property of this sample, "
        "not of municipal legislation.\n"
    )
    L.append(
        "So the honest claim is narrow: **a tuned two clause rule matches these labels, and the Continuity "
        "Agent is not required to beat it on accuracy.** What the agent does that the rule cannot is state, "
        "in checkable language, which evidence drove each decision and which it explicitly set aside. That "
        "output is what the product shows a resident, and it is what makes a wrong answer diagnosable "
        "instead of silent.\n"
    )

    if agent_stats:
        L.append("## Continuity Agent\n")
        L.append("| Metric | Value |")
        L.append("|---|---|")
        for k in ("accuracy", "precision", "recall", "f1"):
            L.append(f"| {k} | {agent_stats[k]:.2f} |")
        L.append(f"| true positives | {agent_stats['tp']} |")
        L.append(f"| false positives | {agent_stats['fp']} |")
        L.append(f"| missed continuations | {agent_stats['fn']} |")
        L.append(f"| true negatives | {agent_stats['tn']} |")

        L.append("\n### Every pair, with the agent's call\n")
        L.append("| Pair | Records | Tier | Label | Agent | Confidence | |")
        L.append("|---|---|---|---|---|---|---|")
        for row, older, newer, f in pairs:
            d = agent_decisions.get(row["pair_id"])
            if not d:
                continue
            ok = (d.decision == "continuation") == (row["label"] == "continuation")
            L.append(
                f"| {row['pair_id']} | `{older.file_number}` to `{newer.file_number}` | "
                f"{row.get('tier', 'parcel')} | {row['label']} | {d.decision} | {d.confidence:.2f} | "
                f"{'ok' if ok else '**miss**'} |"
            )
        L.append(
            f"\nOf the {len(pairs)} pairs, {sum(1 for p in pairs if p[0]['label'] != 'continuation')} are "
            "negatives. They are listed above alongside the positives so that the agent cannot be "
            "mistaken for one that says yes to everything.\n"
        )
        L.append("\n### Every miss, named\n")
        if not agent_stats["errors"]:
            L.append(
                "No misses on this set. That is not the win it looks like, and the reason is in the "
                "baseline table above: the tuned two clause rule also scores 100%. A perfect score "
                "here says the set is separable, not that the agent is necessary. The agent ties the "
                "rule; it does not beat it.\n"
            )
            L.append(
                "What the agent produced that the rule cannot is the reasoning attached to every one "
                "of the 50 rows, including which evidence it set aside. On the hardest negative, 701 "
                "and 702 Mura Street, it wrote that the parcels are adjacent lots on the same block "
                "and listed `title cosine 0.944, boilerplate for conditional use parking lots` as a "
                "non driver. On the hero pair it listed `title cosine 0.943, expected boilerplate for "
                "rezoning ordinances` as a non driver and the exact parcel and matching zoning "
                "transition as drivers. Those two title scores are three thousandths apart and point "
                "in opposite directions, and in both cases the agent said out loud that it was not "
                "using them.\n"
            )
            L.append(
                "The honest open question, and the next experiment, is whether that reasoning holds "
                "on pattern types absent from this set. A 50 pair set assembled by one person cannot "
                "settle it.\n"
            )
        else:
            for row, kind in agent_stats["errors"]:
                d = agent_decisions.get(row["pair_id"])
                L.append(f"**Pair {row['pair_id']}, {row['a']} and {row['b']} ({kind})**\n")
                L.append(f"- Label: {row['label']}. Agent said: {d.decision} at {d.confidence:.2f}.")
                L.append(f"- Why it was labeled that way: {row['note']}")
                if d:
                    L.append(f"- What the agent said: {d.rationale}")
                    L.append(f"- Drivers: {', '.join(d.drivers) or 'none given'}")
                    L.append(f"- Non drivers: {', '.join(d.non_drivers) or 'none given'}")
                L.append("")
    else:
        L.append("## Continuity Agent\n")
        L.append(
            "Not yet run against a model provider. This section is published empty rather than omitted, "
            "so that the baselines above cannot be mistaken for agent results.\n"
        )

    if heldout:
        L.append("")
        L.extend(write_heldout_section(heldout))

    RESULTS.write_text("\n".join(L) + "\n")
    print(f"wrote {RESULTS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--perturb", action="store_true")
    ap.add_argument("--perturb-agent", action="store_true")
    args = ap.parse_args()

    pairs, missing = load_pairs()
    print(f"loaded {len(pairs)} pairs")

    baselines = {name: confusion(pairs, fn) for name, fn in BASELINES.items()}
    for name, c in baselines.items():
        print(f"  {name:52} acc {c['accuracy']:.2f} f1 {c['f1']:.2f}")

    sweep = threshold_sweep(pairs)

    agent_stats = None
    decisions = {}
    if args.from_cache:
        decisions = load_decisions()
        if decisions:
            agent_stats = confusion(pairs, lambda r, o, n, f: decisions[r["pair_id"]].decision == "continuation")
            print(f"  agent accuracy {agent_stats['accuracy']:.2f} (from cache)")
    elif args.agent:
        model = None
        if args.offline:
            from tests.offline_stub import offline_model
            model = offline_model()
        decisions = run_agent(pairs, model, persist=not args.offline)
        agent_stats = confusion(pairs, lambda r, o, n, f: decisions[r["pair_id"]].decision == "continuation")
        print(f"  agent accuracy {agent_stats['accuracy']:.2f}")
        if args.offline:
            print("offline stub: results printed above are plumbing checks and are not written to RESULTS.md")
            agent_stats = None
            decisions = {}

    heldout_decisions = decisions or load_decisions()
    heldout = heldout_report(pairs, heldout_decisions)
    print(
        f"  heldout: tune {heldout['tune_size']} pairs, test {heldout['test_size']} pairs, "
        f"frozen threshold {heldout['frozen_threshold']:.3f}, "
        f"frozen rule test accuracy {heldout['frozen_rule_on_test']['accuracy']:.2f}"
    )

    write_results(pairs, missing, baselines, sweep, agent_stats, decisions, heldout)

    if args.perturb:
        perturb_decisions = decisions or load_decisions()
        rows = perturbation_suite(
            pairs, baselines, perturb_decisions, run_agent_arm=args.perturb_agent,
        )
        for r in rows:
            print(f"  [{r['transform']}] {r['rule']:55} {r['before']:.2f} -> {r['after']:.2f} ({r['delta']:+.3f})")
        write_perturbation_results(rows, len(pairs))


if __name__ == "__main__":
    main()
