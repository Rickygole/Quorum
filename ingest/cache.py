from __future__ import annotations

import gzip
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .legistar_client import LegistarClient

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"

def _write(path: Path, payload: Any, fetched_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"fetched_at": fetched_at, "source": "legistar-webapi-v1-baltimore", "payload": payload}
    with gzip.open(path.with_suffix(path.suffix + ".gz"), "wt") as fh:
        json.dump(body, fh)

def read(name: str) -> dict:
    path = ROOT / name
    if not path.exists():
        path = path.with_suffix(path.suffix + ".gz")
    if path.suffix == ".gz":
        with gzip.open(path, "rt") as fh:
            return json.load(fh)
    return json.loads(path.read_text())

def corpus_fetched_at() -> str:
    return read("matters.json")["fetched_at"]

def snapshot(since: date, with_detail: bool = True) -> dict:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LegistarClient() as api:
        matters = api.matters_since(since)
        _write(ROOT / "matters.json", matters, stamp)
        print(f"cached {len(matters)} matters -> data/cache/matters.json")

        if not with_detail:
            return {"matters": len(matters), "fetched_at": stamp}

        hist: dict[str, list] = {}
        spon: dict[str, list] = {}
        skipped = []
        for i, m in enumerate(matters, 1):
            mid = m["MatterId"]
            try:
                hist[str(mid)] = api.histories(mid)
                spon[str(mid)] = api.sponsors(mid)
            except Exception as exc:
                skipped.append({"matter_id": mid, "file": m.get("MatterFile"), "error": str(exc)[:200]})
                print(f"  skipped {mid}: {str(exc)[:120]}")
            if i % 100 == 0:
                print(f"  detail {i}/{len(matters)}")
        if skipped:
            _write(ROOT / "skipped.json", skipped, stamp)
            print(f"{len(skipped)} matters skipped, recorded in data/cache/skipped.json.gz")
        _write(ROOT / "histories.json", hist, stamp)
        _write(ROOT / "sponsors.json", spon, stamp)
        print(f"cached detail for {len(hist)} matters")

    return {"matters": len(matters), "fetched_at": stamp}

if __name__ == "__main__":
    import sys

    since = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2021, 1, 1)
    print(snapshot(since))
