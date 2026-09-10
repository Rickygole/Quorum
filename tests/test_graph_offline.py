from __future__ import annotations

import asyncio

from agents.graph import QuorumRun, build_graph
from ingest.gazetteer import Gazetteer
from ingest.normalize import load_corpus
from tests.offline_stub import offline_model

WATCHED = ["205 East Cold Spring Lane", "4911 West Forest Park Avenue", "15 East West Street"]


def run_pipeline():
    gaz = Gazetteer.load()
    run = QuorumRun(records=load_corpus(gaz), watched=list(WATCHED))
    graph = build_graph(run, gaz, model=offline_model())
    result = asyncio.run(graph.invoke_async("Run the weekly sweep."))
    return run, result


def test_pipeline():
    run, result = run_pipeline()
    assert result.status.value == "completed", result.status
    assert [t["node"] for t in run.telemetry] == [
        "civic_analyst", "resolution", "continuity", "relevance", "action",
    ]
    assert len(run.candidates) == 6
    assert len(run.surfaced) == 6
    continued = [c for c in run.candidates if c.prior is not None]
    assert len(continued) == 3
    for c in continued:
        assert c.continuity.decision == "continuation"
        assert c.continuity.drivers
        assert c.continuity.non_drivers
    assert all(c.action is not None for c in run.surfaced)
    return run, result


if __name__ == "__main__":
    run, result = test_pipeline()
    print("status:", result.status)
    print("telemetry:")
    for t in run.telemetry:
        print(f"   {t['node']:15} {t['latency_ms']:6} ms")
    print(f"candidates {len(run.candidates)}  surfaced {len(run.surfaced)}")
    print("continuations:")
    for c in run.candidates:
        if c.prior:
            print(f"   {c.prior.file_number} -> {c.record.file_number}  ({c.watched_address})")
            print(f"      drivers: {c.continuity.drivers}")
            print(f"      non-drivers: {c.continuity.non_drivers}")
    print("dropped:", [(d['node'], d.get('count') or d.get('file_number')) for d in run.dropped][:4])
    print("\nPASSED")
