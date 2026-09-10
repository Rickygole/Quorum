from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Callable, TypeVar

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
    def __init__(self, handler: Callable[[type, list], Any]):
        self._handler = handler
        self._config: dict[str, Any] = {"model_id": "offline"}
        self.calls: list[tuple[type, list]] = []

    def get_config(self) -> Any:
        return self._config

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncGenerator:
        raise NotImplementedError("OfflineModel supports structured_output only")

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
