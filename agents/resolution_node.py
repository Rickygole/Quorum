from __future__ import annotations

import time
from typing import Any, AsyncIterator

from strands.agent.agent_result import AgentResult
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status

from ingest.gazetteer import Gazetteer
from models import CivicRecord


class ResolutionNode(MultiAgentBase):
    def __init__(self, gazetteer: Gazetteer, run=None, node_id: str = "resolution"):
        super().__init__()
        self.id = node_id
        self.name = node_id
        self.gazetteer = gazetteer
        self.run = run
        self.last_report: dict[str, Any] = {}

    def resolve(self, record: CivicRecord) -> CivicRecord:
        resolved = []
        for ref in record.parcels:
            resolved.append(self.gazetteer.resolve(ref))
        record.parcels = resolved
        return record

    def matches(self, record: CivicRecord, watched: list[str]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        watched_norm = {w.lower().strip(): w for w in watched}
        watched_blocks = {}
        for w in watched:
            hit = self.gazetteer.by_address.get(_key(w))
            if hit:
                watched_blocks[(hit.get("BLOCK") or "").strip().upper()] = w

        best: dict[str, str] = {}
        rank = {"exact": 2, "adjacent": 1}
        for p in record.parcels:
            addr = (p.address_normalized or "").lower().strip()
            if addr in watched_norm:
                w = watched_norm[addr]
                if rank["exact"] > rank.get(best.get(w, ""), 0):
                    best[w] = "exact"
                continue
            if p.block and p.block.upper() in watched_blocks:
                w = watched_blocks[p.block.upper()]
                if rank["adjacent"] > rank.get(best.get(w, ""), 0):
                    best[w] = "adjacent"
        for w in watched:
            if w in best:
                out.append((w, best[w]))
        return out

    def report(self, records: list[CivicRecord], watched: list[str]) -> dict:
        resolved = [self.resolve(r) for r in records]
        hits = []
        for r in resolved:
            for address, kind in self.matches(r, watched):
                hits.append({"record_id": r.record_id, "file_number": r.file_number,
                             "watched_address": address, "match": kind})
        self.last_report = {
            "records_in": len(records),
            "with_parcel": sum(1 for r in resolved if r.parcels),
            "resolved_to_gazetteer": sum(1 for r in resolved if any(p.parcel_id for p in r.parcels)),
            "watch_hits": hits,
        }
        return self.last_report

    async def invoke_async(self, task, invocation_state: dict[str, Any] | None = None, **kwargs) -> MultiAgentResult:
        start = time.time()
        records = (invocation_state or {}).get("records") or (self.run.records if self.run else [])
        watched = (invocation_state or {}).get("watched") or (self.run.watched if self.run else [])
        report = self.report(records, watched)
        if self.run is not None:
            self.run.resolution = report
        elapsed = round((time.time() - start) * 1000)
        result = AgentResult(
            stop_reason="end_turn",
            message={"role": "assistant", "content": [{"text": _summary(report)}]},
            metrics=None,
            state={},
        )
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.id: NodeResult(result=result, execution_time=elapsed, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=elapsed,
        )

    async def stream_async(self, task, invocation_state: dict[str, Any] | None = None, **kwargs) -> AsyncIterator[dict[str, Any]]:
        result = await self.invoke_async(task, invocation_state, **kwargs)
        yield {"result": result}


def _key(addr: str) -> str:
    import re

    return re.sub(r"[^a-z0-9 ]", "", (addr or "").lower()).strip()


def _summary(report: dict) -> str:
    return (
        f"Resolved {report['resolved_to_gazetteer']} of {report['records_in']} records to a parcel. "
        f"{len(report['watch_hits'])} touch a watched address."
    )
