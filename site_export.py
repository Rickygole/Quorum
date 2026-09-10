from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus
from features.continuity_features import compute

OUT = Path(__file__).resolve().parent / "docs" / "data"

WATCHED = [
    "205 East Cold Spring Lane",
    "4911 West Forest Park Avenue",
    "15 East West Street",
]


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
    gaz = Gazetteer.load()
    corpus = load_corpus(gaz)
    by_file = {r.file_number: r for r in corpus}
    resolvable = [r for r in corpus if r.parcels]

    OUT.mkdir(parents=True, exist_ok=True)

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
        threads.append({
            "pair_id": p["pair_id"],
            "label": p["note"],
            "tier": p.get("tier", "parcel"),
            "watched": touches,
            "records": [record_json(older, gaz), record_json(newer, gaz)],
            "features": compute(newer, older),
        })

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

    from eval.run_eval import confusion, load_decisions

    cached = load_decisions()
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
        "evaluation": evaluation,
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
