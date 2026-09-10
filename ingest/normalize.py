from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from models import Appearance, CivicRecord
from .gazetteer import Gazetteer, parse_parcel_refs
from .legistar_client import LegistarClient

TYPE_MAP = {
    "Ordinance": "ordinance",
    "City Council Resolution": "resolution",
    "Mayor and City Council Res.": "resolution",
    "Legislative Oversight": "agenda_item",
    "Executive Nomination": "agenda_item",
}

HEARING_ACTIONS = ("Scheduled for a Public Hearing",)
COMMITTEE_EXCLUDE = ("Baltimore City Council", "Mayor")

def _d(v: Any) -> date | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).date()
    except ValueError:
        return None

def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def to_record(
    matter: dict,
    histories: list[dict] | None,
    sponsors: list[dict] | None,
    fetched_at: datetime,
    gaz: Gazetteer | None = None,
) -> CivicRecord:
    histories = sorted(histories or [], key=lambda h: h.get("MatterHistoryActionDate") or "")
    title = _clean(matter.get("MatterTitle") or matter.get("MatterName"))
    file_number = _clean(matter.get("MatterFile")) or f"ID-{matter['MatterId']}"

    appearances = [
        Appearance(
            record_id=str(matter["MatterId"]),
            file_number=file_number,
            action_date=_d(h.get("MatterHistoryActionDate")),
            action=_clean(h.get("MatterHistoryActionName")),
            body=_clean(h.get("MatterHistoryActionBodyName")),
        )
        for h in histories
    ]

    committee = next(
        (a.body for a in reversed(appearances) if a.body and a.body not in COMMITTEE_EXCLUDE),
        None,
    )

    today = date.today()
    hearing = next(
        (a.action_date for a in appearances
         if a.action in HEARING_ACTIONS and a.action_date and a.action_date >= today),
        None,
    )

    parcels = parse_parcel_refs(title)
    if gaz:
        parcels = [gaz.resolve(p) for p in parcels]

    return CivicRecord(
        record_id=str(matter["MatterId"]),
        file_number=file_number,
        record_type=TYPE_MAP.get(matter.get("MatterTypeName", ""), "agenda_item"),
        title=title,
        body_excerpt=title[:1200],
        sponsors=[_clean(s.get("MatterSponsorName")) for s in (sponsors or []) if s.get("MatterSponsorName")],
        requester=_clean(matter.get("MatterRequester")) or None,
        committee=committee,
        addresses_raw=[p.address_raw for p in parcels if p.address_raw],
        parcels=parcels,
        hearing_date=hearing,
        introduced_date=_d(matter.get("MatterIntroDate")),
        status=_clean(matter.get("MatterStatusName")) or None,
        source_url=LegistarClient.portal_url(matter),
        fetched_at=fetched_at,
        history=appearances,
    )

def load_corpus(gaz: Gazetteer | None = None, parcels_only: bool = False) -> list[CivicRecord]:
    from . import cache

    matters = cache.read("matters.json")
    fetched_at = datetime.fromisoformat(matters["fetched_at"])
    hist = cache.read("histories.json")["payload"]
    spon = cache.read("sponsors.json")["payload"]

    out = []
    for m in matters["payload"]:
        mid = str(m["MatterId"])
        rec = to_record(m, hist.get(mid), spon.get(mid), fetched_at, gaz)
        if parcels_only and not rec.parcels:
            continue
        out.append(rec)
    out.sort(key=lambda r: r.introduced_date or date.min, reverse=True)
    return out
