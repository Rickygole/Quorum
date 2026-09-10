from __future__ import annotations

import json

from pydantic import BaseModel, Field
from strands import Agent

from models import CivicRecord, ContinuityDecision
from .model import bedrock, run_structured

SYSTEM = """You write the only part of this system a resident actually reads.

Produce four things:

- `headline`: what this record does, in one sentence, in the words a neighbour would use. \
No file numbers, no zoning codes unless you say what they mean.
- `what_changed`: what is different since the previous appearance of this issue. Be \
specific about lots, scope, sponsors or status. If there is no previous appearance, \
return null.
- `why_it_matters`: two sentences at most, concrete and non alarmist. Do not tell the \
resident what to think about the proposal.
- `draft_comment`: a public comment the resident can edit and send. Address the committee. \
State the file number and the hearing date exactly as given to you. Refer to the earlier \
bill and its outcome if there was one. Leave a clearly marked placeholder for the \
resident's own view. Do not argue for or against the proposal, and do not invent facts \
about the neighbourhood, the applicant or the resident.

Write in sentence case and active voice. Never write "leverage", "seamlessly", \
"empowering communities", or "as an AI"."""


class ActionOutput(BaseModel):
    headline: str
    what_changed: str | None = None
    why_it_matters: str
    draft_comment: str
    sources_cited: list[str] = Field(default_factory=list)


class ActionAgent:
    def __init__(self, model=None, agent: Agent | None = None):
        self.agent = agent or Agent(
            model=model or bedrock(),
            system_prompt=SYSTEM,
            structured_output_model=ActionOutput,
            name="action",
            callback_handler=None,
        )
        self.usage: list[dict] = []

    def compose(
        self,
        record: CivicRecord,
        prior: CivicRecord | None = None,
        continuity: ContinuityDecision | None = None,
        watched_address: str | None = None,
    ) -> ActionOutput:
        payload = {
            "watched_address": watched_address,
            "record": {
                "file_number": record.file_number,
                "title": record.title[:900],
                "committee": record.committee,
                "status": record.status,
                "hearing_date": record.hearing_date.isoformat() if record.hearing_date else None,
                "source_url": record.source_url,
                "sponsors": record.sponsors,
            },
            "previous_appearance": None
            if prior is None
            else {
                "file_number": prior.file_number,
                "title": prior.title[:400],
                "introduced": prior.introduced_date.isoformat() if prior.introduced_date else None,
                "status": prior.status,
            },
            "continuity_rationale": None if continuity is None else continuity.rationale,
            "parcel_change": None
            if continuity is None
            else {
                "lots_now": continuity.features.get("parcel", {}).get("lots_a"),
                "lots_before": continuity.features.get("parcel", {}).get("lots_b"),
            },
        }
        out, usage = run_structured(self.agent, "Write the resident facing summary and the draft comment.\n\n" + json.dumps(payload, indent=1))

        self.usage.append(usage)

        return out
