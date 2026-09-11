from __future__ import annotations

import json
from pathlib import Path

from agents.continuity import SYSTEM, build_prompt
from eval.run_eval import load_pairs, load_decisions

OUT = Path(__file__).resolve().parent / "pairs_bundle.json"


def main():
    pairs, missing = load_pairs()
    cached = load_decisions()

    bundle = {"system_prompt": SYSTEM, "pairs": {}}
    for row, older, newer, features in pairs:
        pid = str(row["pair_id"])
        decision = cached.get(row["pair_id"])
        bundle["pairs"][pid] = {
            "pair_id": row["pair_id"],
            "tier": row.get("tier", "parcel"),
            "label": row["label"],
            "prompt": build_prompt(newer, older, features),
            "features": features,
            "older": {"file_number": older.file_number, "title": older.title[:400],
                      "status": older.status, "introduced": str(older.introduced_date)},
            "newer": {"file_number": newer.file_number, "title": newer.title[:400],
                      "status": newer.status, "introduced": str(newer.introduced_date)},
            "cached": None if decision is None else {
                "decision": decision.decision, "confidence": decision.confidence,
                "rationale": decision.rationale, "drivers": decision.drivers,
                "non_drivers": decision.non_drivers,
            },
        }

    OUT.write_text(json.dumps(bundle))
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} with {len(bundle['pairs'])} pairs, {kb:.0f} KB, missing={missing}")


if __name__ == "__main__":
    main()
