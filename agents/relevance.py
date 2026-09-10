from __future__ import annotations

import json

from pydantic import BaseModel
from strands import Agent

from models import CivicRecord, RelevanceDecision
from .model import bedrock, run_structured

SYSTEM = """You decide whether a municipal record actually affects a resident who watches \
a specific address, and you are expected to say no most of the time.

Proximity is not relevance. Apply these distinctions:

- A zoning change, conditional use, demolition, liquor licence or property sale on the \
watched parcel or its immediate block affects the resident. Say yes.
- A citywide ordinance that happens to name a street in a schedule does not affect them \
in any way they could act on. Say no.
- A procurement contract, a bond issue, a personnel matter or a budget line does not \
become relevant because a vendor's headquarters sits on the block. Say no.
- A parking permit rule covering the block the resident lives on does affect them. Say yes.

`reason` must be one sentence, addressed to the resident, naming the specific thing and \
the specific address. Not a category label.

Silence is the correct output for most records. Returning `relevant: false` with a clear \
reason is a good answer, not a failure."""


class RelevanceOutput(BaseModel):
    relevant: bool
    reason: str
    confidence: float = 0.0


class RelevanceAgent:
    def __init__(self, model=None, agent: Agent | None = None, threshold: float = 0.55):
        self.threshold = threshold
        self.agent = agent or Agent(
            model=model or bedrock(),
            system_prompt=SYSTEM,
            structured_output_model=RelevanceOutput,
            name="relevance",
            callback_handler=None,
        )
        self.usage: list[dict] = []

    def assess(self, record: CivicRecord, watched_address: str, parcel_match: str) -> RelevanceDecision:
        payload = {
            "watched_address": watched_address,
            "parcel_match": parcel_match,
            "file_number": record.file_number,
            "record_type": record.record_type,
            "title": record.title[:900],
            "status": record.status,
            "hearing_date": record.hearing_date.isoformat() if record.hearing_date else None,
            "parcels": [
                {"parcel_id": p.parcel_id, "address": p.address_normalized, "block": p.block}
                for p in record.parcels
            ],
        }
        out, usage = run_structured(self.agent, "Does this affect the resident who watches this address?\n\n" + json.dumps(payload, indent=1))

        self.usage.append(usage)
        relevant = out.relevant and out.confidence >= self.threshold
        return RelevanceDecision(
            record_id=record.record_id,
            relevant=relevant,
            reason=out.reason.strip(),
            confidence=max(0.0, min(1.0, out.confidence)),
        )
