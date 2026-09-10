from __future__ import annotations

import json

from pydantic import BaseModel, Field
from strands import Agent

from models import CivicRecord
from .model import bedrock, run_structured

SYSTEM = """You read one Baltimore City Council legislative record and extract structured \
facts from it.

The record is prose, not a form. The same fact can appear in an ordinance preamble, a \
title, or a passing clause, and the drafting style varies between clerks and across years.

Rules that matter more than completeness:

- Never invent a file number, a block, a lot, an address or a date. If the record does not \
state it, return null.
- Copy identifiers exactly as printed. Do not reformat "R 1 C" into "R-1-C", and do not \
expand or abbreviate street names.
- `action_requested` is what the council is being asked to do, in one plain sentence a \
resident would understand. Not the legal formula.
- `plain_summary` is one or two sentences explaining the practical effect on the property \
and the people near it. No jargon, no "leverage", no "seamlessly".
- `confidence` is your honest per field confidence from 0 to 1. Use low values freely. A \
field you are unsure of is worth more as a low confidence flag than as a guess."""


class AnalystOutput(BaseModel):
    action_requested: str | None = None
    plain_summary: str | None = None
    addresses_mentioned: list[str] = Field(default_factory=list)
    blocks_mentioned: list[str] = Field(default_factory=list)
    zoning_from: str | None = None
    zoning_to: str | None = None
    applicant: str | None = None
    confidence: dict[str, float] = Field(default_factory=dict)


class CivicAnalyst:
    def __init__(self, model=None, agent: Agent | None = None, threshold: float = 0.4):
        self.threshold = threshold
        self.agent = agent or Agent(
            model=model or bedrock(),
            system_prompt=SYSTEM,
            structured_output_model=AnalystOutput,
            name="civic_analyst",
            callback_handler=None,
        )
        self.usage: list[dict] = []

    def analyze(self, record: CivicRecord) -> AnalystOutput:
        payload = {
            "file_number": record.file_number,
            "record_type": record.record_type,
            "title": record.title[:2000],
            "sponsors": record.sponsors,
            "status": record.status,
            "introduced": record.introduced_date.isoformat() if record.introduced_date else None,
        }
        out, usage = run_structured(self.agent, "Extract the structured facts from this record.\n\n" + json.dumps(payload, indent=1))

        self.usage.append(usage)
        return self._suppress_low_confidence(out)

    def _suppress_low_confidence(self, out: AnalystOutput) -> AnalystOutput:
        for field, score in (out.confidence or {}).items():
            if score < self.threshold and hasattr(out, field):
                current = getattr(out, field)
                if isinstance(current, list):
                    setattr(out, field, [])
                else:
                    setattr(out, field, None)
        return out

    def apply(self, record: CivicRecord, out: AnalystOutput) -> CivicRecord:
        record.action_requested = out.action_requested
        record.requester = record.requester or out.applicant
        record.extraction_confidence = out.confidence or {}
        for a in out.addresses_mentioned:
            if a not in record.addresses_raw:
                record.addresses_raw.append(a)
        return record
