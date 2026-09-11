from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus
from features.continuity_features import compute
from ingest.zoning import context_for
from eval.base_rates import compute as compute_base_rates

OUT = Path(__file__).resolve().parent / "docs" / "data"
ACTION_CACHE = Path(__file__).resolve().parent / "data" / "action_cache.json"

WATCHED = [
    "205 East Cold Spring Lane",
    "4911 West Forest Park Avenue",
    "15 East West Street",
]


def _action_cache_key(older, newer):
    return f"{older.file_number}:{newer.file_number}"


def load_action_cache():
    if not ACTION_CACHE.exists():
        return {}
    return json.loads(ACTION_CACHE.read_text())


def save_action_cache(cache):
    ACTION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ACTION_CACHE.write_text(json.dumps(cache, indent=1))


def action_json(older, newer, continuity, watched_address, cache, agent):
    key = _action_cache_key(older, newer)
    if key in cache:
        return cache[key]
    out = agent.compose(newer, older, continuity, watched_address, zoning_context=context_for(newer.title))
    payload = {
        "headline": out.headline,
        "what_changed": out.what_changed,
        "why_it_matters": out.why_it_matters,
        "draft_comment": out.draft_comment,
        "sources_cited": out.sources_cited,
    }
    cache[key] = payload
    return payload


def _iso(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def record_json(r, gaz):
    parcel = r.parcels[0] if r.parcels else None
    hit = gaz.lookup(parcel) if parcel else None
    return {
        "record_id": r.record_id,
        "file_number": r.file_number,
        "record_type": r.record_type,
        "title": r.title,
        "sponsors": r.sponsors,
        "committee": r.committee,
        "status": r.status,
        "introduced_date": _iso(r.introduced_date),
        "hearing_date": _iso(r.hearing_date),
        "source_url": r.source_url,
        "fetched_at": _iso(r.fetched_at),
        "parcels": [
            {"parcel_id": p.parcel_id, "block": p.block, "lots": p.lots,
             "address": p.address_normalized}
            for p in r.parcels
        ],
        "neighborhood": (hit or {}).get("NEIGHBOR"),
        "owner": ((hit or {}).get("OWNER_1") or "").strip() or None,
        "zone": (hit or {}).get("ZONECODE"),
        "history": [
            {"date": _iso(a.action_date), "action": a.action, "body": a.body}
            for a in r.history
        ],
    }


def main():
    from eval.run_eval import load_decisions

    gaz = Gazetteer.load()
    corpus = load_corpus(gaz)
    by_file = {r.file_number: r for r in corpus}
    resolvable = [r for r in corpus if r.parcels]

    OUT.mkdir(parents=True, exist_ok=True)

    action_cache = load_action_cache()
    cached_decisions = load_decisions()
    action_agent = None
    cache_hits = cache_misses = 0

    pairs = [json.loads(l) for l in open("eval/labeled_set.jsonl")]
    threads = []
    for p in pairs:
        if p["label"] != "continuation":
            continue
        a, b = by_file.get(p["a"]), by_file.get(p["b"])
        if not a or not b:
            continue
        older, newer = (a, b) if (a.introduced_date or date.min) <= (b.introduced_date or date.min) else (b, a)
        watched_norm = {w.lower() for w in WATCHED}
        touches = sorted({
            w for rec in (older, newer) for par in rec.parcels
            for w in WATCHED
            if (par.address_normalized or "").lower() == w.lower()
        })

        cache_key = _action_cache_key(older, newer)
        if cache_key in action_cache:
            cache_hits += 1
        else:
            cache_misses += 1
            if action_agent is None:
                from agents.action import ActionAgent

                action_agent = ActionAgent()
        action = action_json(
            older, newer, cached_decisions.get(p["pair_id"]),
            touches[0] if touches else None, action_cache, action_agent,
        )

        closed = not newer.hearing_date and (newer.status or "") not in ("In Committee",)
        threads.append({
            "comment_window": {
                "open": bool(newer.hearing_date),
                "status": newer.status,
                "hearing_date": _iso(newer.hearing_date),
                "closed_reason": None if newer.hearing_date else (
                    f"{newer.status}. No comment window." if closed
                    else "No hearing on the calendar yet."
                ),
            },
            "sources": [
                {"file_number": r.file_number, "url": r.source_url}
                for r in (older, newer)
            ],
            "pair_id": p["pair_id"],
            "label": p["note"],
            "tier": p.get("tier", "parcel"),
            "watched": touches,
            "records": [record_json(older, gaz), record_json(newer, gaz)],
            "features": compute(newer, older),
            "action": action,
        })

    save_action_cache(action_cache)
    print(f"action agent: {cache_hits} cache hits, {cache_misses} live calls")

    negatives = []
    for p in pairs:
        if p["label"] != "new_issue" or not p["hard"]:
            continue
        a, b = by_file.get(p["a"]), by_file.get(p["b"])
        if not a or not b:
            continue
        negatives.append({
            "pair_id": p["pair_id"], "label": p["note"],
            "records": [record_json(a, gaz), record_json(b, gaz)],
            "features": compute(b, a),
        })

    streets = {w.split(" ", 1)[1] for w in WATCHED}
    addresses = sorted({
        a for a in (
            g_addr for g_addr in (
                __import__("ingest.gazetteer", fromlist=["normalize_address"]).normalize_address(r.get("FULLADDR") or "")
                for r in gaz.rows
            ) if g_addr
        ) if a.split(" ", 1)[-1] in streets
    })[:400]
    addresses = sorted(set(addresses) | set(WATCHED))

    from eval.run_eval import BASELINES, confusion, load_pairs, threshold_sweep

    eval_pairs, eval_missing = load_pairs()
    evaluation = {
        "pairs": len(eval_pairs),
        "continuations": sum(1 for p in eval_pairs if p[0]["label"] == "continuation"),
        "hard": sum(1 for p in eval_pairs if p[0]["hard"]),
        "missing": eval_missing,
        "baselines": [
            {"rule": name, **{k: round(v, 3) for k, v in confusion(eval_pairs, fn).items() if k != "errors"}}
            for name, fn in BASELINES.items()
        ],
        "sweep": [{"threshold": t, "accuracy": round(a, 3)} for t, a in threshold_sweep(eval_pairs)],
        "agent": None,
    }

    cached = cached_decisions
    if cached:
        stats = confusion(eval_pairs, lambda r, o, n, f: cached[r["pair_id"]].decision == "continuation")
        evaluation["agent"] = {
            k: round(v, 3) for k, v in stats.items() if k != "errors"
        }
        evaluation["agent"]["misses"] = [
            {"pair_id": row["pair_id"], "a": row["a"], "b": row["b"], "kind": kind,
             "label": row["label"], "said": cached[row["pair_id"]].decision,
             "confidence": cached[row["pair_id"]].confidence,
             "rationale": cached[row["pair_id"]].rationale,
             "note": row["note"]}
            for row, kind in stats["errors"]
        ]
        evaluation["agent"]["decisions"] = [
            {"pair_id": row["pair_id"], "a": older.file_number, "b": newer.file_number,
             "tier": row.get("tier", "parcel"), "label": row["label"],
             "said": cached[row["pair_id"]].decision,
             "confidence": round(cached[row["pair_id"]].confidence, 2),
             "drivers": cached[row["pair_id"]].drivers,
             "non_drivers": cached[row["pair_id"]].non_drivers}
            for row, older, newer, f in eval_pairs if row["pair_id"] in cached
        ]

    from eval.run_eval import heldout_report

    heldout = heldout_report(eval_pairs, cached)
    evaluation["heldout"] = {
        "tune_size": heldout["tune_size"],
        "test_size": heldout["test_size"],
        "tune_ids": heldout["tune_ids"],
        "test_ids": heldout["test_ids"],
        "frozen_threshold": heldout["frozen_threshold"],
        "tune_accuracy": round(heldout["tune_accuracy"], 3),
        "baselines_on_test": [
            {"rule": name, **{k: round(v, 3) for k, v in c.items() if k != "errors"}}
            for name, c in heldout["baselines_on_test"].items()
        ],
        "frozen_rule_on_test": {
            k: round(v, 3) for k, v in heldout["frozen_rule_on_test"].items() if k != "errors"
        },
        "agent_on_test": (
            {k: round(v, 3) for k, v in heldout["agent_on_test"].items() if k != "errors"}
            if heldout["agent_on_test"] else None
        ),
    }

    live_endpoint = os.environ.get(
        "QUORUM_LIVE_ENDPOINT",
        "https://1gpbm1pph4.execute-api.us-east-1.amazonaws.com",
    )

    fetched = corpus[0].fetched_at if corpus else None
    payload = {
        "fetched_at": _iso(fetched),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "matters": len(corpus),
            "parcel_resolvable": len(resolvable),
            "parcels": len(gaz.rows),
            "labeled_pairs": len(pairs),
        },
        "watched": WATCHED,
        "live": {
            "endpoint": live_endpoint,
            "runtime_arn": "arn:aws:bedrock-agentcore:us-east-1:162774483375:runtime/quorum_continuity-eEoCT98tX4",
            "note": "Posting a pair id runs the Continuity Agent on AgentCore Runtime against Amazon Bedrock. The response carries the runtime arn, the AgentCore session id, the model id and the measured latency, so a live call can be told apart from a cached one.",
        },
        "evaluation": evaluation,
        "base_rates": compute_base_rates(corpus),
        "addresses": addresses,
        "graph": [
            {"node": "Civic Analyst", "kind": "agent"},
            {"node": "Resolution", "kind": "code"},
            {"node": "Continuity", "kind": "agent"},
            {"node": "Relevance", "kind": "agent"},
            {"node": "Action", "kind": "agent"},
        ],
        "threads": threads,
        "negatives": negatives,
    }
    (OUT / "site.json").write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT/'site.json'}: {len(threads)} threads, {len(negatives)} hard negatives")


if __name__ == "__main__":
    main()
