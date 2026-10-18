"""Provider abstractions and standard-library-backed adapters."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol, runtime_checkable
from urllib.request import Request, urlopen


Message = Mapping[str, Any]


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot produce a completion."""


@runtime_checkable
class Provider(Protocol):
    """Minimal interface implemented by completion providers."""

    @property
    def available(self) -> bool:
        ...

    def complete(self, messages: Iterable[Message]) -> str:
        ...


class MockProvider:
    """Deterministic provider that consumes a scripted response per call."""

    def __init__(self, responses: Iterable[str], *, available: bool = True) -> None:
        self._responses = iter(responses)
        self.available = available

    def complete(self, messages: Iterable[Message]) -> str:
        if not self.available:
            raise ProviderUnavailableError("mock provider is unavailable")
        try:
            return next(self._responses)
        except StopIteration as exc:
            raise ProviderUnavailableError("mock provider has no scripted response") from exc


class OpenAICompatibleProvider:
    """Adapter for the OpenAI chat-completions JSON protocol.

    ``opener`` is injectable so callers can test request construction without
    making a network request. It must accept a urllib ``Request`` and return a
    response object supporting ``read`` and the context-manager protocol.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        opener: Callable[[Request], Any] = urlopen,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self._opener = opener

    @property
    def available(self) -> bool:
        return bool(self.endpoint and self.model)

    def complete(self, messages: Iterable[Message]) -> str:
        if not self.available:
            raise ProviderUnavailableError("OpenAI-compatible provider is unavailable")

        payload = json.dumps(
            {"model": self.model, "messages": list(messages)}
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(self.endpoint, data=payload, headers=headers, method="POST")
        with self._opener(request) as response:
            raw = response.read()

        try:
            body = json.loads(raw.decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid OpenAI-compatible response") from exc
        if not isinstance(content, str):
            raise ValueError("invalid OpenAI-compatible response content")
        return content
