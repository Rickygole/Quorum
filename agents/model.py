from __future__ import annotations

import json
import os
from typing import Any, AsyncGenerator, Callable, Iterable, TypeVar

from pydantic import BaseModel
from strands.models import Model

T = TypeVar("T")

DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
FAST_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def bedrock(model_id: str | None = None, temperature: float = 0.2) -> Model:
    from strands.models import BedrockModel

    return BedrockModel(
        model_id=model_id or os.environ.get("QUORUM_MODEL_ID", DEFAULT_MODEL_ID),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        temperature=temperature,
    )


class OfflineModel(Model):
    def __init__(self, handler: Callable[[type, list], Any], output_models: Iterable[type[BaseModel]] = ()):
        self._handler = handler
        self._by_name = {m.__name__: m for m in output_models}
        self._config: dict[str, Any] = {"model_id": "offline"}
        self.calls: list[tuple[type, list]] = []

    def get_config(self) -> Any:
        return self._config

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncGenerator:
        tool_spec = (tool_specs or [None])[0]
        if not tool_spec or tool_spec["name"] not in self._by_name:
            raise NotImplementedError("OfflineModel only supports a single registered structured output tool")

        output_model = self._by_name[tool_spec["name"]]
        self.calls.append((output_model, messages))
        result = self._handler(output_model, messages)
        tool_use_id = f"offline-{len(self.calls)}"

        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"contentBlockIndex": 0, "start": {"toolUse": {
            "toolUseId": tool_use_id, "name": tool_spec["name"],
        }}}}
        yield {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"toolUse": {
            "input": json.dumps(result.model_dump(mode="json")),
        }}}}
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {"metadata": {
            "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
            "metrics": {"latencyMs": 0},
        }}

    async def structured_output(self, output_model: type[T], prompt: list, system_prompt: str | None = None, **kwargs) -> AsyncGenerator[dict[str, Any], None]:
        self.calls.append((output_model, prompt))
        yield {"output": self._handler(output_model, prompt)}


def is_offline() -> bool:
    return os.environ.get("QUORUM_OFFLINE") == "1"


def usage_of(result) -> dict:
    m = getattr(result, "metrics", None)
    usage = getattr(m, "accumulated_usage", None) if m else None
    if not usage:
        return {}
    get = (lambda k: usage.get(k)) if isinstance(usage, dict) else (lambda k: getattr(usage, k, None))
    return {
        "input_tokens": get("inputTokens") or get("input_tokens"),
        "output_tokens": get("outputTokens") or get("output_tokens"),
        "total_tokens": get("totalTokens") or get("total_tokens"),
    }


def run_structured(agent, prompt: str, stateless: bool = True):
    if stateless:
        agent.messages = []
    before = getattr(agent, "_quorum_usage_total", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    result = agent(prompt)
    after = usage_of(result)
    delta = {k: (after.get(k) or 0) - (before.get(k) or 0) for k in ("input_tokens", "output_tokens", "total_tokens")}
    agent._quorum_usage_total = after
    return result.structured_output, delta
