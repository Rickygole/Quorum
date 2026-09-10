from __future__ import annotations

import json
from typing import Iterable

from pydantic import BaseModel, Field
from strands import Agent

from features.continuity_features import compute
from models import CivicRecord, ContinuityDecision
from .model import bedrock

SYSTEM = """You decide whether a new municipal legislative record continues an issue \
the system has already seen, or starts a new one.

You are given two records and a table of comparison features that were computed \
deterministically in code. The feature table is evidence. Do not recompute it, do not \
contradict it, and do not invent facts that are not in it or in the records.

How to weigh the evidence for Baltimore City Council records:

- The parcel comparison is the strongest single signal. `exact` means the records name \
the same parcel. `adjacent` means the same block but a different lot, which in this \
corpus almost always means two genuinely different properties and therefore two \
different issues.
- Title similarity is weak evidence here and must never be a primary driver. Baltimore \
uses heavy boilerplate, so two unrelated conditional use bills on different properties \
routinely score above 0.9. A high title score is not evidence of continuation.
- A prior record with a terminal status (Failed at end of term, Withdrawn) followed by a \
new introduction on the same parcel is the classic reintroduction pattern, and file \
numbers will not match because the council term changed.
- The same parcel appearing under a different legislative instrument (a zoning conversion \
and the parking permit exception that conversion requires, or a liquor licence and its \
matching zoning approval) is a continuation: it is one real world project moving through \
the approvals it needs.
- A matching zoning transition between the same two districts is strong corroboration.

Return your decision with:
- `decision`: continuation, new_issue, or uncertain.
- `rationale`: short plain sentences a resident could follow. Name the specific evidence.
- `drivers`: the feature names that actually drove the decision.
- `non_drivers`: the features you considered and explicitly did not rely on, with the \
value, for example "title cosine 0.94, boilerplate". Always fill this in. If title \
similarity was high but irrelevant, that belongs here.
- `confidence`: 0 to 1.

Use `uncertain` when the evidence genuinely conflicts, not to avoid a call."""


class ContinuityOutput(BaseModel):
    decision: str = Field(description="continuation, new_issue, or uncertain")
    rationale: str
    drivers: list[str] = Field(default_factory=list)
    non_drivers: list[str] = Field(default_factory=list)
    confidence: float = 0.0


def _brief(r: CivicRecord) -> dict:
    return {
        "file_number": r.file_number,
        "title": r.title[:700],
        "record_type": r.record_type,
        "introduced": r.introduced_date.isoformat() if r.introduced_date else None,
        "status": r.status,
        "committee": r.committee,
        "sponsors": r.sponsors,
        "parcels": [
            {"parcel_id": p.parcel_id, "block": p.block, "lots": p.lots, "address": p.address_normalized}
            for p in r.parcels
        ],
    }


def build_prompt(candidate: CivicRecord, prior: CivicRecord, features: dict) -> str:
    return (
        "NEW RECORD\n"
        + json.dumps(_brief(candidate), indent=1)
        + "\n\nEARLIER RECORD\n"
        + json.dumps(_brief(prior), indent=1)
        + "\n\nCOMPARISON FEATURES (computed in code, treat as fact)\n"
        + json.dumps(features, indent=1)
        + "\n\nDoes the new record continue the same issue as the earlier record?"
    )


class ContinuityAgent:
    def __init__(self, model=None, agent: Agent | None = None):
        self.agent = agent or Agent(
            model=model or bedrock(),
            system_prompt=SYSTEM,
            name="continuity",
            callback_handler=None,
        )

    def decide(self, candidate: CivicRecord, prior: CivicRecord, issue_id: str | None = None) -> ContinuityDecision:
        features = compute(candidate, prior)
        out = self.agent.structured_output(ContinuityOutput, build_prompt(candidate, prior, features))
        decision = out.decision.strip().lower()
        if decision not in ("continuation", "new_issue", "uncertain"):
            decision = "uncertain"
        return ContinuityDecision(
            candidate_record_id=candidate.record_id,
            matched_issue_id=issue_id if decision == "continuation" else None,
            decision=decision,
            features=features,
            rationale=out.rationale.strip(),
            drivers=out.drivers,
            non_drivers=out.non_drivers,
            confidence=max(0.0, min(1.0, out.confidence)),
        )

    def best_match(self, candidate: CivicRecord, priors: Iterable[CivicRecord]) -> ContinuityDecision | None:
        best: ContinuityDecision | None = None
        for prior in priors:
            d = self.decide(candidate, prior)
            if d.decision == "continuation" and (best is None or d.confidence > best.confidence):
                best = d
        return best
