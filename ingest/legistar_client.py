"""Legistar Web API client for Baltimore City.

Gate A finding (see README): baltimore.legistar.com exposes a live, public,
unauthenticated Legistar Web API at webapi.legistar.com/v1/baltimore. Every
item type Quorum commits to comes from this one source, so there is no
multi-agency publishing-habit problem to absorb.

The API caps $top at 1000, so every list call pages on $skip.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Iterator

import httpx

BASE = "https://webapi.legistar.com/v1/baltimore"
PAGE = 1000
PORTAL = "https://baltimore.legistar.com/LegislationDetail.aspx?ID={matter_id}&GUID={guid}"


class LegistarClient:
    """Thin, polite wrapper. Read-only; never writes to the city's systems."""

    def __init__(self, timeout: float = 30.0, pause: float = 0.15):
        self._http = httpx.Client(timeout=timeout, headers={"Accept": "application/json"})
        self._pause = pause

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LegistarClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(4):
            try:
                r = self._http.get(f"{BASE}{path}", params=params)
                r.raise_for_status()
                time.sleep(self._pause)
                return r.json()
            except (httpx.HTTPStatusError, httpx.TransportError):
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("unreachable")

    def _paged(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict]:
        params = dict(params or {})
        skip = 0
        while True:
            params.update({"$top": PAGE, "$skip": skip})
            batch = self._get(path, params)
            yield from batch
            if len(batch) < PAGE:
                return
            skip += PAGE

    # -- the four calls Quorum actually needs -----------------------------

    def matters_since(self, since: date) -> list[dict]:
        """Every matter introduced on or after `since`."""
        flt = f"MatterIntroDate ge datetime'{since.isoformat()}'"
        return list(self._paged("/matters", {"$filter": flt}))

    def histories(self, matter_id: int) -> list[dict]:
        """Action history: the appearances of one matter across bodies."""
        return self._get(f"/matters/{matter_id}/histories")

    def sponsors(self, matter_id: int) -> list[dict]:
        return self._get(f"/matters/{matter_id}/sponsors")

    def attachments(self, matter_id: int) -> list[dict]:
        return self._get(f"/matters/{matter_id}/attachments")

    @staticmethod
    def portal_url(matter: dict) -> str:
        """Citation link a human can actually open."""
        return PORTAL.format(matter_id=matter["MatterId"], guid=matter["MatterGuid"])
