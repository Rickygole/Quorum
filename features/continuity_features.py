from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date

from models import CivicRecord, ParcelRef

STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "as", "at", "by",
    "purpose", "property", "properties", "known", "outlined", "red", "accompanying",
    "plat", "certain", "conditions", "subject", "city", "baltimore", "mayor", "council",
    "ordinance", "resolution", "be", "is", "are", "from", "with", "that", "this", "which",
}

STAGE_ORDER = {
    "introduced": 0, "assigned": 0, "refer": 1, "scheduled for a public hearing": 2,
    "recommended favorably": 3, "2nd reader": 4, "advanced to 3rd reader": 5,
    "approved and sent to the mayor": 6, "signed by mayor": 7,
    "withdrawn": 8, "failed": 8,
}

_ZONE = re.compile(r"\b([A-Z]{1,4})[\s-]?(\d{1,2})?[\s-]?([A-Z])?\s+Zoning District\b")
_ZONE_PAIR = re.compile(r"from the (.{2,12}?) Zoning District to the (.{2,12}?) Zoning District", re.I)

OWNER_SUFFIX_CANON = {
    "INCORPORATED": "INC", "CORPORATION": "CORP", "COMPANY": "CO",
    "LIMITED": "LTD", "LC": "LLC",
}

def _tokens(text: str) -> Counter:
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    return Counter(w for w in words if w not in STOPWORDS and len(w) > 2)

def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return round(num / den, 3) if den else 0.0

def _jaccard(a: Counter, b: Counter) -> float:
    sa, sb = set(a), set(b)
    return round(len(sa & sb) / len(sa | sb), 3) if (sa | sb) else 0.0

def _norm_zone(z: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (z or "").upper())

def _norm_owner(o: str) -> str:
    s = re.sub(r"[.,]", "", (o or "").upper())
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(OWNER_SUFFIX_CANON.get(t, t) for t in s.split())

def compare_owners(a: list[ParcelRef], b: list[ParcelRef]) -> dict:
    if not a or not b:
        return {"match": "unknown", "reason": "no parcel", "a": [], "b": []}
    owners_a = sorted({p.owner for p in a if p.owner})
    owners_b = sorted({p.owner for p in b if p.owner})
    if not owners_a or not owners_b:
        return {"match": "unknown", "reason": "parcel not in gazetteer", "a": owners_a, "b": owners_b}
    norm_a = {_norm_owner(o) for o in owners_a}
    norm_b = {_norm_owner(o) for o in owners_b}
    if norm_a & norm_b:
        return {"match": "same", "a": owners_a, "b": owners_b}
    return {"match": "changed", "a": owners_a, "b": owners_b}

def zoning_transition(text: str) -> tuple[str, str] | None:
    m = _ZONE_PAIR.search(text or "")
    return (_norm_zone(m.group(1)), _norm_zone(m.group(2))) if m else None

def _stage(action: str | None) -> int | None:
    a = (action or "").lower()
    for k, v in STAGE_ORDER.items():
        if a.startswith(k):
            return v
    return None

def compare_parcels(a: list[ParcelRef], b: list[ParcelRef]) -> dict:
    ids_a = {p.parcel_id for p in a if p.parcel_id}
    ids_b = {p.parcel_id for p in b if p.parcel_id}
    shared = ids_a & ids_b
    if shared:
        return {"match": "exact", "shared_parcel_ids": sorted(shared),
                "lots_a": sorted({l for p in a for l in p.lots}),
                "lots_b": sorted({l for p in b for l in p.lots})}

    blocks_a = {p.block for p in a if p.block}
    blocks_b = {p.block for p in b if p.block}
    if blocks_a & blocks_b:
        return {"match": "adjacent", "shared_blocks": sorted(blocks_a & blocks_b),
                "lots_a": sorted({l for p in a for l in p.lots}),
                "lots_b": sorted({l for p in b for l in p.lots})}

    addr_a = {p.address_normalized for p in a if p.address_normalized}
    addr_b = {p.address_normalized for p in b if p.address_normalized}
    if addr_a & addr_b:
        return {"match": "exact", "shared_addresses": sorted(addr_a & addr_b)}

    st = lambda s: " ".join(s.split()[1:])
    if {st(x) for x in addr_a} & {st(x) for x in addr_b}:
        return {"match": "adjacent", "shared_street": sorted({st(x) for x in addr_a} & {st(x) for x in addr_b}),
                "addresses_a": sorted(addr_a), "addresses_b": sorted(addr_b)}
    return {"match": "none", "addresses_a": sorted(addr_a), "addresses_b": sorted(addr_b)}

def compute(candidate: CivicRecord, prior: CivicRecord) -> dict:
    ta, tb = _tokens(candidate.title), _tokens(prior.title)

    sp_a = {s.lower() for s in candidate.sponsors}
    sp_b = {s.lower() for s in prior.sponsors}

    zt_a, zt_b = zoning_transition(candidate.title), zoning_transition(prior.title)

    stage_a = max((s for s in (_stage(h.action) for h in candidate.history) if s is not None), default=None)
    stage_b = max((s for s in (_stage(h.action) for h in prior.history) if s is not None), default=None)

    d_a, d_b = candidate.introduced_date, prior.introduced_date
    gap = (d_a - d_b).days if (d_a and d_b) else None

    prior_terminal = prior.status in ("Failed - End of Term", "Withdrawn", "Failed")
    if prior_terminal:
        progression = "restart"
    elif stage_a is not None and stage_b is not None:
        progression = "advance" if stage_a >= stage_b else "regression"
    else:
        progression = "unknown"

    return {
        "parcel": compare_parcels(candidate.parcels, prior.parcels),
        "owner": compare_owners(candidate.parcels, prior.parcels),
        "sponsor": {
            "overlap": sorted(sp_a & sp_b),
            "jaccard": round(len(sp_a & sp_b) / len(sp_a | sp_b), 3) if (sp_a | sp_b) else 0.0,
            "a": sorted(sp_a), "b": sorted(sp_b),
        },
        "requester": {
            "match": bool(candidate.requester and candidate.requester == prior.requester),
            "a": candidate.requester, "b": prior.requester,
        },
        "title": {
            "token_jaccard": _jaccard(ta, tb),
            "cosine": _cosine(ta, tb),
            "distinctive_shared": sorted(set(ta) & set(tb))[:12],
        },
        "zoning_transition": {
            "match": bool(zt_a and zt_a == zt_b),
            "a": "->".join(zt_a) if zt_a else None,
            "b": "->".join(zt_b) if zt_b else None,
        },
        "record_type": {"match": candidate.record_type == prior.record_type,
                        "a": candidate.record_type, "b": prior.record_type},
        "temporal": {
            "candidate_introduced": d_a.isoformat() if d_a else None,
            "prior_introduced": d_b.isoformat() if d_b else None,
            "gap_days": gap,
            "ordered": bool(gap is not None and gap > 0),
            "same_council_term": bool(candidate.file_number[:2] == prior.file_number[:2]),
        },
        "committee_progression": {
            "shape": progression,
            "consistent": progression in ("restart", "advance"),
            "prior_furthest_stage": stage_b,
            "candidate_furthest_stage": stage_a,
            "prior_terminal": prior_terminal,
            "prior_status": prior.status,
            "candidate_committee": candidate.committee,
            "prior_committee": prior.committee,
        },
        "file_number": {
            "identical": candidate.file_number == prior.file_number,
            "a": candidate.file_number, "b": prior.file_number,
        },
    }
