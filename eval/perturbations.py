from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from models import CivicRecord

DIRECTION_RE = re.compile(r"\b(East|West|North|South)\b")
DIRECTION_ABBREV = {"East": "E", "West": "W", "North": "N", "South": "S"}
ZONE_CODE_RE = re.compile(r"\b([A-Za-z]{1,3})-(\d{1,2})-([A-Za-z])\b")
LOT_LIST_RE = re.compile(r"(Lots?\s+)((?:[0-9A-Z]{2,4}(?:,\s*|\s+and\s+))*[0-9A-Z]{2,4})")
PREAMBLE = ", as outlined in red on the accompanying plat"


def _retitle(rec: CivicRecord, title: str) -> CivicRecord:
    return rec.model_copy(update={"title": title})


def _abbreviate_directions(title: str) -> str:
    return DIRECTION_RE.sub(lambda m: DIRECTION_ABBREV[m.group(1)], title)


def _normalize_dash(title: str) -> str:
    return title.replace("–", "-")


def _space_zone_code(title: str) -> str:
    return ZONE_CODE_RE.sub(lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}", title)


def _reverse_lot_list(title: str) -> str:
    m = LOT_LIST_RE.search(title)
    if not m:
        return title
    items = re.split(r",\s*|\s+and\s+", m.group(2))
    if len(items) < 2:
        return title
    items = list(reversed(items))
    joined = ", ".join(items[:-1]) + ", and " + items[-1] if len(items) > 2 else " and ".join(items)
    return title[: m.start()] + m.group(1) + joined + title[m.end():]


def _strip_preamble(title: str) -> str:
    return title.replace(PREAMBLE, "")


@dataclass
class Perturbation:
    name: str
    target: str
    corpus_example: str
    transform: Callable[[str], str]

    def apply(self, older: CivicRecord, newer: CivicRecord) -> tuple[CivicRecord, CivicRecord]:
        if self.target in ("older", "both"):
            older = _retitle(older, self.transform(older.title))
        if self.target in ("newer", "both"):
            newer = _retitle(newer, self.transform(newer.title))
        return older, newer


REGISTRY: dict[str, Perturbation] = {
    p.name: p
    for p in [
        Perturbation(
            name="direction abbreviation",
            target="newer",
            corpus_example="23-0411 titles the property 'East Cold Spring Lane'; 26-0148, the reintroduction of the same bill, titles it 'E Cold Spring Lane'.",
            transform=_abbreviate_directions,
        ),
        Perturbation(
            name="dash style normalization",
            target="newer",
            corpus_example="23-0411 opens with a hyphen after 'Rezoning'; 26-0148, the reintroduction of the same bill, opens with an en dash character there instead. 254 of 1679 corpus titles carry an en dash.",
            transform=_normalize_dash,
        ),
        Perturbation(
            name="zoning code spacing",
            target="newer",
            corpus_example="23-0411 writes the zoning code as 'R-1-C'; 26-0148 writes the same code as 'R 1 C'. 21-0011 ('C-1-E') and 24-0474 ('A-56-A') show the hyphenated style elsewhere in the corpus.",
            transform=_space_zone_code,
        ),
        Perturbation(
            name="lot list reorder",
            target="newer",
            corpus_example="23-0411 lists 'Lots 001, 002, 003'; 22-0321 lists five lots ('Lots 043, 044, 045, 046, 047') in a single fixed order, the same kind of list this transform reverses.",
            transform=_reverse_lot_list,
        ),
        Perturbation(
            name="boilerplate preamble stripped",
            target="newer",
            corpus_example="154 of 1679 corpus titles carry the phrase 'as outlined in red on the accompanying plat'; the remaining 1525, including every non zoning record type, carry no such preamble, so its absence is a realistic formatting variant and not an invented one.",
            transform=_strip_preamble,
        ),
    ]
}
