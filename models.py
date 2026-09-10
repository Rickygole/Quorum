from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RecordType = Literal["ordinance", "resolution", "agenda_item", "minutes_entry"]

class ParcelRef(BaseModel):

    address_raw: str | None = None
    address_normalized: str | None = None
    block: str | None = None
    lots: list[str] = Field(default_factory=list)
    parcel_id: str | None = None

class Appearance(BaseModel):

    record_id: str
    file_number: str
    action_date: date | None = None
    action: str | None = None
    body: str | None = None
    status: str | None = None
    what_changed: str | None = None

class CivicRecord(BaseModel):

    record_id: str
    file_number: str
    record_type: RecordType
    title: str
    body_excerpt: str = ""
    sponsors: list[str] = Field(default_factory=list)
    requester: str | None = None
    committee: str | None = None
    action_requested: str | None = None
    addresses_raw: list[str] = Field(default_factory=list)
    parcels: list[ParcelRef] = Field(default_factory=list)
    hearing_date: date | None = None
    introduced_date: date | None = None
    status: str | None = None
    source_url: str
    source_page: int | None = None
    fetched_at: datetime
    history: list[Appearance] = Field(default_factory=list)
    extraction_confidence: dict[str, float] = Field(default_factory=dict)

class Issue(BaseModel):

    issue_id: str
    label: str
    first_seen: date | None = None
    appearances: list[Appearance] = Field(default_factory=list)
    file_numbers: list[str] = Field(default_factory=list)
    current_status: str | None = None
    current_committee: str | None = None
    next_hearing: date | None = None
    parcels: list[str] = Field(default_factory=list)
    watchers: list[str] = Field(default_factory=list)

class ContinuityDecision(BaseModel):
    candidate_record_id: str
    matched_issue_id: str | None = None
    decision: Literal["continuation", "new_issue", "uncertain"]
    features: dict = Field(default_factory=dict)
    rationale: str
    drivers: list[str] = Field(default_factory=list)
    non_drivers: list[str] = Field(default_factory=list)
    confidence: float = 0.0

class RelevanceDecision(BaseModel):
    record_id: str
    relevant: bool
    reason: str
    confidence: float
