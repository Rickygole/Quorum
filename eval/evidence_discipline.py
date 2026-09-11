from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ROOT / "labeled_set.jsonl"
DECISIONS = ROOT / "agent_decisions.json"
OUT = ROOT / "evidence_discipline.json"

TITLE_TERMS = ("title cosine", "title similarity", "title score", "title jaccard")


def _mentions_title(strings) -> bool:
    return any(any(term in s.lower() for term in TITLE_TERMS) for s in strings)


def _mentions_parcel(strings) -> bool:
    return any("parcel" in s.lower() for s in strings)


def load_labels() -> dict:
    labels = {}
    for line in LABELS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        labels[row["pair_id"]] = row["label"]
    return labels


def load_decisions() -> dict:
    raw = json.loads(DECISIONS.read_text())
    return {int(k): v for k, v in raw["decisions"].items()}


def evaluate(decisions=None, labels=None) -> dict:
    decisions = decisions if decisions is not None else load_decisions()
    labels = labels if labels is not None else load_labels()

    high_cosine_new_issue = []
    parcel_exact_continuation = []
    driver_hygiene = []

    for pair_id, d in decisions.items():
        label = labels.get(pair_id)
        features = d["features"]
        cosine = features["title"]["cosine"]
        parcel_match = features["parcel"]["match"]
        drivers = d["drivers"]
        non_drivers = d["non_drivers"]

        if cosine >= 0.90 and label == "new_issue":
            high_cosine_new_issue.append({
                "pair_id": pair_id, "cosine": cosine,
                "cites_title": _mentions_title(non_drivers),
            })

        if parcel_match == "exact" and label == "continuation":
            parcel_exact_continuation.append({
                "pair_id": pair_id,
                "names_parcel": _mentions_parcel(drivers),
            })

        driver_hygiene.append({
            "pair_id": pair_id,
            "drivers_nonempty": bool(drivers),
            "disjoint": set(drivers).isdisjoint(set(non_drivers)),
        })

    def rate(items, key):
        if not items:
            return None, 0
        return sum(1 for i in items if i[key]) / len(items), len(items)

    title_rate, title_n = rate(high_cosine_new_issue, "cites_title")
    parcel_rate, parcel_n = rate(parcel_exact_continuation, "names_parcel")
    hygiene_n = len(driver_hygiene)
    hygiene_hits = sum(1 for i in driver_hygiene if i["drivers_nonempty"] and i["disjoint"])
    hygiene_rate = hygiene_hits / hygiene_n if hygiene_n else None

    return {
        "high_cosine_new_issue": {
            "n": title_n, "rate": title_rate, "pairs": high_cosine_new_issue,
        },
        "parcel_exact_continuation": {
            "n": parcel_n, "rate": parcel_rate, "pairs": parcel_exact_continuation,
        },
        "driver_hygiene": {
            "n": hygiene_n, "rate": hygiene_rate, "pairs": driver_hygiene,
        },
    }


def main():
    result = evaluate()
    hc = result["high_cosine_new_issue"]
    print(f"high cosine (>=0.90) new_issue pairs citing title in non_drivers: {hc['rate']} ({hc['n']} pairs)")
    for p in hc["pairs"]:
        if not p["cites_title"]:
            print(f"  MISS pair {p['pair_id']} cosine {p['cosine']} did not cite title as a non driver")
    pc = result["parcel_exact_continuation"]
    print(f"parcel exact continuations naming parcel in drivers: {pc['rate']} ({pc['n']} pairs)")
    for p in pc["pairs"]:
        if not p["names_parcel"]:
            print(f"  MISS pair {p['pair_id']} did not name the parcel in drivers")
    dh = result["driver_hygiene"]
    print(f"decisions with non-empty drivers disjoint from non_drivers: {dh['rate']} ({dh['n']} pairs)")
    for p in dh["pairs"]:
        if not (p["drivers_nonempty"] and p["disjoint"]):
            print(f"  MISS pair {p['pair_id']} drivers_nonempty={p['drivers_nonempty']} disjoint={p['disjoint']}")
    OUT.write_text(json.dumps(result, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
