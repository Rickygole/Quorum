from __future__ import annotations

import json
from pathlib import Path

from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus
from features.continuity_features import zoning_transition

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "base_rates.json"

TERMINAL_STATUSES = {
    "Enacted", "Confirmed", "Adopted", "Failed - End of Term",
    "Confirmed after 3 Meetings without Council Action", "Withdrawn",
    "Matter Concluded", "Failed", "Vetoed by Mayor",
}


def reached_hearing(r) -> bool:
    return any(a.action == "Scheduled for a Public Hearing" for a in r.history)


def is_terminal(r) -> bool:
    return r.status in TERMINAL_STATUSES


def is_rezoning(r) -> bool:
    return r.record_type == "ordinance" and bool(zoning_transition(r.title))


def is_conditional_use(r) -> bool:
    return r.record_type == "ordinance" and r.title.startswith("Zoning") and "Conditional Use" in r.title


def is_property_sale(r) -> bool:
    return r.record_type == "ordinance" and r.title.startswith("Sale of Property")


CATEGORIES = {
    "rezoning ordinance": is_rezoning,
    "conditional use petition": is_conditional_use,
    "sale of property ordinance": is_property_sale,
}


def category_outcome(records, predicate, outcome_status="Enacted") -> dict:
    matched = [r for r in records if predicate(r)]
    heard = [r for r in matched if reached_hearing(r)]
    outcome = [r for r in heard if r.status == outcome_status]
    return {
        "n_total": len(matched),
        "n_reached_hearing": len(heard),
        "n_outcome": len(outcome),
        "outcome_status": outcome_status,
        "rate": round(len(outcome) / len(heard), 3) if heard else None,
    }


def corpus_outcome_distribution(records) -> dict:
    n = len(records)
    terminal = [r for r in records if is_terminal(r)]
    from collections import Counter

    counts = Counter(r.status for r in records)
    return {
        "n_total": n,
        "n_terminal": len(terminal),
        "by_status": [
            {"status": status, "n": count, "rate": round(count / n, 3)}
            for status, count in sorted(counts.items(), key=lambda kv: -kv[1])
        ],
    }


def compute(records=None) -> dict:
    if records is None:
        records = load_corpus(Gazetteer.load())
    return {
        "n_matters": len(records),
        "categories": {
            name: category_outcome(records, predicate)
            for name, predicate in CATEGORIES.items()
        },
        "status_distribution": corpus_outcome_distribution(records),
    }


def main():
    result = compute()
    print(f"corpus: {result['n_matters']} matters")
    for name, stat in result["categories"].items():
        print(
            f"  {name:28} n={stat['n_total']:4} reached hearing={stat['n_reached_hearing']:4} "
            f"{stat['outcome_status'].lower()}={stat['n_outcome']:4} rate={stat['rate']}"
        )
    print("status distribution:")
    for row in result["status_distribution"]["by_status"]:
        print(f"  {row['status']:50} n={row['n']:4} rate={row['rate']}")
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
