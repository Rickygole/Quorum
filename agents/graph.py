from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from strands.agent.agent_result import AgentResult
from strands.multiagent import GraphBuilder
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status

from ingest.gazetteer import Gazetteer
from models import CivicRecord, ContinuityDecision, RelevanceDecision
from .action import ActionAgent, ActionOutput
from .civic_analyst import CivicAnalyst
from .continuity import ContinuityAgent
from .relevance import RelevanceAgent
from .resolution_node import ResolutionNode


@dataclass
class Surfaced:
    record: CivicRecord
    watched_address: str
    parcel_match: str
    prior: CivicRecord | None = None
    continuity: ContinuityDecision | None = None
    relevance: RelevanceDecision | None = None
    action: ActionOutput | None = None


@dataclass
class QuorumRun:
    records: list[CivicRecord] = field(default_factory=list)
    watched: list[str] = field(default_factory=list)
    resolution: dict = field(default_factory=dict)
    candidates: list[Surfaced] = field(default_factory=list)
    surfaced: list[Surfaced] = field(default_factory=list)
    dropped: list[dict] = field(default_factory=list)
    telemetry: list[dict] = field(default_factory=list)

    def note(self, node: str, ms: int, detail: dict | None = None) -> None:
        self.telemetry.append({"node": node, "latency_ms": ms, **(detail or {})})


class _Node(MultiAgentBase):
    node_name = "node"

    def __init__(self, run: QuorumRun, node_id: str | None = None):
        super().__init__()
        self.run = run
        self.id = node_id or self.node_name
        self.name = self.id

    def work(self) -> str:
        raise NotImplementedError

    async def invoke_async(self, task, invocation_state: dict[str, Any] | None = None, **kwargs) -> MultiAgentResult:
        start = time.time()
        summary = self.work()
        ms = round((time.time() - start) * 1000)
        self.run.note(self.id, ms)
        result = AgentResult(
            stop_reason="end_turn",
            message={"role": "assistant", "content": [{"text": summary}]},
            metrics=None,
            state={},
        )
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.id: NodeResult(result=result, execution_time=ms, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=ms,
        )

    async def stream_async(self, task, invocation_state: dict[str, Any] | None = None, **kwargs) -> AsyncIterator[dict[str, Any]]:
        yield {"result": await self.invoke_async(task, invocation_state, **kwargs)}


class AnalystNode(_Node):
    node_name = "civic_analyst"

    def __init__(self, run: QuorumRun, analyst: CivicAnalyst, limit: int = 40):
        super().__init__(run)
        self.analyst = analyst
        self.limit = limit

    def work(self) -> str:
        targets = [r for r in self.run.records if r.parcels][: self.limit]
        for r in targets:
            out = self.analyst.analyze(r)
            self.analyst.apply(r, out)
        return f"Read {len(targets)} parcel bearing records."


class ResolutionGraphNode(_Node):
    node_name = "resolution"

    def __init__(self, run: QuorumRun, gazetteer: Gazetteer):
        super().__init__(run)
        self.resolver = ResolutionNode(gazetteer, run=run, node_id="resolution")

    def work(self) -> str:
        report = self.resolver.report(self.run.records, self.run.watched)
        self.run.resolution = report
        by_id = {r.record_id: r for r in self.run.records}
        self.run.candidates = [
            Surfaced(record=by_id[h["record_id"]], watched_address=h["watched_address"], parcel_match=h["match"])
            for h in report["watch_hits"]
        ]
        dropped = len(self.run.records) - report["with_parcel"]
        self.run.dropped.append({"node": "resolution", "count": dropped, "reason": "named no parcel Quorum could resolve"})
        return f"{len(self.run.candidates)} records touch a watched address."


class ContinuityNode(_Node):
    node_name = "continuity"

    def __init__(self, run: QuorumRun, agent: ContinuityAgent):
        super().__init__(run)
        self.agent = agent

    def work(self) -> str:
        by_addr: dict[str, list[Surfaced]] = {}
        for c in self.run.candidates:
            by_addr.setdefault(c.watched_address, []).append(c)

        found = 0
        for _, group in by_addr.items():
            group.sort(key=lambda s: s.record.introduced_date or __import__("datetime").date.min)
            for i, cand in enumerate(group):
                for prior in reversed(group[:i]):
                    decision = self.agent.decide(cand.record, prior.record)
                    if decision.decision == "continuation":
                        cand.prior = prior.record
                        cand.continuity = decision
                        found += 1
                        break
                    cand.continuity = cand.continuity or decision
        return f"{found} of {len(self.run.candidates)} records continue an earlier issue."


class RelevanceNode(_Node):
    node_name = "relevance"

    def __init__(self, run: QuorumRun, agent: RelevanceAgent):
        super().__init__(run)
        self.agent = agent

    def work(self) -> str:
        kept = []
        for c in self.run.candidates:
            c.relevance = self.agent.assess(c.record, c.watched_address, c.parcel_match)
            if c.relevance.relevant:
                kept.append(c)
            else:
                self.run.dropped.append({
                    "node": "relevance", "file_number": c.record.file_number,
                    "reason": c.relevance.reason,
                })
        self.run.surfaced = kept
        return f"Surfaced {len(kept)} of {len(self.run.candidates)}. The rest stay silent."


class ActionNode(_Node):
    node_name = "action"

    def __init__(self, run: QuorumRun, agent: ActionAgent):
        super().__init__(run)
        self.agent = agent

    def work(self) -> str:
        for c in self.run.surfaced:
            c.action = self.agent.compose(c.record, c.prior, c.continuity, c.watched_address)
        return f"Composed {len(self.run.surfaced)} resident facing summaries."


def build_graph(run: QuorumRun, gazetteer: Gazetteer, model=None):
    analyst = AnalystNode(run, CivicAnalyst(model=model))
    resolution = ResolutionGraphNode(run, gazetteer)
    continuity = ContinuityNode(run, ContinuityAgent(model=model))
    relevance = RelevanceNode(run, RelevanceAgent(model=model))
    action = ActionNode(run, ActionAgent(model=model))

    b = GraphBuilder()
    for n in (analyst, resolution, continuity, relevance, action):
        b.add_node(n, n.id)
    b.add_edge("civic_analyst", "resolution")
    b.add_edge("resolution", "continuity")
    b.add_edge("continuity", "relevance")
    b.add_edge("relevance", "action")
    b.set_entry_point("civic_analyst")
    b.set_max_node_executions(10)
    return b.build()
