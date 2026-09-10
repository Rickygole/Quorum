"""Timestamped local corpus.

Every demo Quorum gives runs off this cache, never off the live internet.
`fetched_at` is written next to the payload and shown on screen in the product,
because a corpus you can date is a corpus a judge can believe.

Layout mirrors what the S3 writer does in deploy/; local disk is the default so
the project runs from clean with no AWS account.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .legistar_client import LegistarClient

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"


def _write(path: Path, payload: Any, fetched_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched_at": fetched_at, "source": "legistar-webapi-v1-baltimore", "payload": payload}, indent=1))


def read(name: str) -> dict:
    """Returns {'fetched_at': ..., 'source': ..., 'payload': ...}."""
    return json.loads((ROOT / name).read_text())


def corpus_fetched_at() -> str:
    return read("matters.json")["fetched_at"]


def snapshot(since: date, with_detail: bool = True) -> dict:
    """Pull the corpus once and freeze it. Idempotent; safe to re-run."""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LegistarClient() as api:
        matters = api.matters_since(since)
        _write(ROOT / "matters.json", matters, stamp)
        print(f"cached {len(matters)} matters -> data/cache/matters.json")

        if not with_detail:
            return {"matters": len(matters), "fetched_at": stamp}

        hist: dict[str, list] = {}
        spon: dict[str, list] = {}
        for i, m in enumerate(matters, 1):
            mid = m["MatterId"]
            hist[str(mid)] = api.histories(mid)
            spon[str(mid)] = api.sponsors(mid)
            if i % 100 == 0:
                print(f"  detail {i}/{len(matters)}")
        _write(ROOT / "histories.json", hist, stamp)
        _write(ROOT / "sponsors.json", spon, stamp)
        print(f"cached detail for {len(hist)} matters")

    return {"matters": len(matters), "fetched_at": stamp}


if __name__ == "__main__":
    import sys

    since = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2021, 1, 1)
    print(snapshot(since))
