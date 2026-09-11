from __future__ import annotations

import collections
import re
from functools import lru_cache

from .gazetteer import Gazetteer


def _norm(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


@lru_cache(maxsize=1)
def _index():
    gaz = Gazetteer.load()
    by_code: dict[str, list[dict]] = collections.defaultdict(list)
    for row in gaz.rows:
        code = _norm(row.get("ZONECODE") or "")
        if code:
            by_code[code].append(row)
    return by_code


def describe(code: str) -> dict | None:
    rows = _index().get(_norm(code))
    if not rows:
        return None
    owners = collections.Counter((r.get("OWNER_1") or "").strip() for r in rows if (r.get("OWNER_1") or "").strip())
    hoods = collections.Counter((r.get("NEIGHBOR") or "").strip() for r in rows if (r.get("NEIGHBOR") or "").strip())
    return {
        "code": (rows[0].get("ZONECODE") or "").strip(),
        "parcels_citywide": len(rows),
        "top_owners": [{"owner": o, "parcels": n} for o, n in owners.most_common(4)],
        "top_neighborhoods": [h for h, _ in hoods.most_common(4)],
    }


def context_for(text: str) -> dict:
    out = {}
    for m in re.finditer(r"\b([A-Z]{1,4}[\s-]?\d{0,2}[\s-]?[A-Z]?)\s+Zoning District\b", text or ""):
        d = describe(m.group(1))
        if d:
            out[d["code"]] = d
    return out
