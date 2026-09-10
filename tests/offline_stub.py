from __future__ import annotations

import json
import re
from typing import Any

from agents.action import ActionOutput
from agents.civic_analyst import AnalystOutput
from agents.continuity import ContinuityOutput
from agents.model import OfflineModel
from agents.relevance import RelevanceOutput


def _text(prompt: Any) -> str:
    if isinstance(prompt, str):
        return prompt
    out = []
    for m in prompt or []:
        for block in (m.get("content") or []) if isinstance(m, dict) else []:
            if "text" in block:
                out.append(block["text"])
    return "\n".join(out)


def _features(text: str) -> dict:
    m = re.search(r"COMPARISON FEATURES.*?\n(\{.*)", text, re.S)
    if not m:
        return {}
    depth = 0
    for i, ch in enumerate(m.group(1)):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            try:
                return json.loads(m.group(1)[: i + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def handler(output_model: type, prompt: Any):
    text = _text(prompt)

    if output_model is AnalystOutput:
        return AnalystOutput(
            action_requested="offline stub",
            plain_summary="offline stub",
            confidence={"action_requested": 1.0},
        )

    if output_model is ContinuityOutput:
        f = _features(text)
        parcel = (f.get("parcel") or {}).get("match")
        cosine = (f.get("title") or {}).get("cosine")
        if parcel == "exact":
            return ContinuityOutput(
                decision="continuation",
                rationale="Same parcel and the earlier item reached a terminal status.",
                drivers=["parcel", "committee_progression"],
                non_drivers=[f"title cosine {cosine}, boilerplate"],
                confidence=0.9,
            )
        return ContinuityOutput(
            decision="new_issue",
            rationale="Adjacent lots on the same block are different properties.",
            drivers=["parcel"],
            non_drivers=[f"title cosine {cosine}, boilerplate"],
            confidence=0.85,
        )

    if output_model is RelevanceOutput:
        exact = '"parcel_match": "exact"' in text
        return RelevanceOutput(
            relevant=exact,
            reason="It is on the parcel you watch." if exact else "It is nearby but not your property.",
            confidence=0.9 if exact else 0.8,
        )

    if output_model is ActionOutput:
        return ActionOutput(
            headline="offline stub headline",
            what_changed="offline stub change",
            why_it_matters="offline stub.",
            draft_comment="offline stub comment",
            sources_cited=[],
        )

    raise AssertionError(f"unhandled output model {output_model}")


def offline_model() -> OfflineModel:
    return OfflineModel(handler, [AnalystOutput, ContinuityOutput, RelevanceOutput, ActionOutput])
