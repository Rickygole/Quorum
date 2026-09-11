from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import httpx

from models import ParcelRef

LAYER = "https://egisdata.baltimorecity.gov/egis/rest/services/Housing/dmxOwnership/MapServer/0/query"
FIELDS = "BLOCKLOT,BLOCK,LOT,FULLADDR,NEIGHBOR,ZONECODE,OWNER_1,NO_IMPRV,VACIND"
PAGE = 5000
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache" / "gazetteer.json.gz"

_SUFFIX = {
    "st": "Street", "street": "Street", "ave": "Avenue", "av": "Avenue", "avenue": "Avenue",
    "rd": "Road", "road": "Road", "blvd": "Boulevard", "boulevard": "Boulevard",
    "ln": "Lane", "lane": "Lane", "ct": "Court", "court": "Court", "pl": "Place",
    "place": "Place", "dr": "Drive", "drive": "Drive", "way": "Way", "ter": "Terrace",
    "terrace": "Terrace", "sq": "Square", "square": "Square", "pkwy": "Parkway",
    "parkway": "Parkway", "hwy": "Highway", "highway": "Highway", "cir": "Circle",
    "circle": "Circle", "aly": "Alley", "alley": "Alley",
}
_DIR = {"n": "North", "s": "South", "e": "East", "w": "West",
        "north": "North", "south": "South", "east": "East", "west": "West"}

_SUFFIX_RE = "|".join(sorted(_SUFFIX, key=len, reverse=True))
_ADDR_RE = re.compile(
    r"\b(?P<num>\d{1,5})(?:\s*-\s*(?P<num2>\d{1,5}))?\s+"
    r"(?P<rest>(?:[A-Za-z'\.]+\s+){1,4}?)"
    r"(?P<suf>" + _SUFFIX_RE + r")\b\.?",
    re.IGNORECASE,
)

_BLOCK_RE = re.compile(
    r"Block\s+(?P<block>[0-9]{3,5}[A-Z]?)\s*,?\s*Lots?\s+(?P<lots>[0-9A-Z]{1,4}(?:\s*(?:,|and|&)\s*[0-9A-Z]{1,4})*)",
    re.IGNORECASE,
)

def normalize_address(raw: str) -> str | None:
    m = _ADDR_RE.search(raw or "")
    if not m:
        return None
    words = [w for w in m.group("rest").replace(".", " ").split() if w]
    if not words:
        return None
    out = []
    if words[0].lower() in _DIR:
        out.append(_DIR[words[0].lower()])
        words = words[1:]
    if not words:
        return None
    out += [w.capitalize() if not w.isupper() or len(w) > 2 else w.capitalize() for w in words]
    out.append(_SUFFIX[m.group("suf").lower()])
    return f"{int(m.group('num'))} " + " ".join(out)

def blocklot_key(block: str, lot: str) -> str:
    return f"{(block or '').upper().strip():<5}{(lot or '').strip().zfill(3)}"

def _norm_key(addr: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (addr or "").lower()).strip()

def clean_owner(raw: str | None) -> str | None:
    s = re.sub(r"\s+", " ", (raw or "")).strip()
    return s or None

def parse_parcel_refs(text: str) -> list[ParcelRef]:
    text = re.sub(r"\s+", " ", text or "")
    refs: list[ParcelRef] = []

    addrs: list[str] = []
    for m in _ADDR_RE.finditer(text):
        n = normalize_address(m.group(0))
        if n and n not in addrs:
            addrs.append(n)

    for m in _BLOCK_RE.finditer(text):
        lots = [l.strip().zfill(3) for l in re.split(r"\s*(?:,|and|&)\s*", m.group("lots")) if l.strip()]
        block = m.group("block").upper()
        refs.append(ParcelRef(
            address_raw=addrs[0] if addrs else None,
            address_normalized=addrs[0] if addrs else None,
            block=block,
            lots=lots,
            parcel_id=f"{block}{lots[0]}" if lots else None,
        ))

    if not refs:
        for a in addrs:
            refs.append(ParcelRef(address_raw=a, address_normalized=a))
    return refs

class Gazetteer:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.by_blocklot: dict[str, dict] = {}
        self.by_address: dict[str, dict] = {}
        for r in rows:
            bl = (r.get("BLOCKLOT") or "").strip().upper()
            if bl:
                self.by_blocklot.setdefault(bl, r)
            addr = normalize_address(r.get("FULLADDR") or "")
            if addr:
                self.by_address.setdefault(_norm_key(addr), r)

    @classmethod
    def load(cls, path: Path = CACHE) -> "Gazetteer":
        with gzip.open(path, "rt") as fh:
            return cls(json.load(fh)["payload"])

    def lookup(self, ref: ParcelRef) -> dict | None:
        if ref.block:
            for lot in ref.lots or []:
                hit = self.by_blocklot.get(blocklot_key(ref.block, lot))
                if hit:
                    return hit
        if ref.address_normalized:
            return self.by_address.get(_norm_key(ref.address_normalized))
        return None

    def resolve(self, ref: ParcelRef) -> ParcelRef:
        hit = self.lookup(ref)
        if not hit:
            return ref
        out = ref.model_copy(deep=True)
        out.parcel_id = (hit.get("BLOCKLOT") or "").strip().upper() or out.parcel_id
        out.block = out.block or (hit.get("BLOCK") or "").strip().upper() or None
        addr = normalize_address(hit.get("FULLADDR") or "")
        out.address_normalized = out.address_normalized or addr
        out.owner = clean_owner(hit.get("OWNER_1"))
        return out

    def autocomplete(self, prefix: str, limit: int = 8) -> list[str]:
        k = _norm_key(prefix)
        if len(k) < 3:
            return []
        out = [normalize_address(r["FULLADDR"]) for key, r in self.by_address.items() if key.startswith(k)]
        return sorted({o for o in out if o})[:limit]

def build(path: Path = CACHE) -> int:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    with httpx.Client(timeout=120.0) as http:
        offset = 0
        while True:
            r = http.get(LAYER, params={
                "where": "1=1", "outFields": FIELDS, "returnGeometry": "false",
                "resultOffset": offset, "resultRecordCount": PAGE, "f": "json",
            })
            r.raise_for_status()
            feats = r.json().get("features", [])
            rows += [f["attributes"] for f in feats]
            print(f"  parcels {len(rows)}")
            if len(feats) < PAGE:
                break
            offset += PAGE
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as fh:
        json.dump({"fetched_at": stamp, "source": "baltimore-egis-dmxOwnership", "payload": rows}, fh)
    return len(rows)

if __name__ == "__main__":
    print("parcels cached:", build())
