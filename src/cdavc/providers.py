"""Provider abstractions and standard-library-backed adapters."""

from __future__ import annotations

import json
import inspect
import socket
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from urllib.error import URLError
from urllib.request import Request, urlopen


Message = Mapping[str, Any]


@dataclass(frozen=True)
class ProviderCompletion:
    """Completion text with usage when the local provider reports it.

    The existing provider API returns a string.  This small value object is an
    additive metadata API used by the benchmark runner; ``complete`` continues
    to return only ``text`` for existing callers.
    """

    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    model: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def input_tokens(self) -> int | None:
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int | None:
        return self.completion_tokens

    @property
    def token_in(self) -> int | None:
        return self.prompt_tokens

    @property
    def token_out(self) -> int | None:
        return self.completion_tokens


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

    def __init__(self, responses: Iterable[str | ProviderCompletion | Mapping[str, Any]], *, available: bool = True) -> None:
        self._responses = iter(responses)
        self.available = available

    def complete(self, messages: Iterable[Message]) -> str:
        return self.complete_with_metadata(messages).text

    def complete_with_metadata(
        self,
        messages: Iterable[Message],
        *,
        seed: int | None = None,
    ) -> ProviderCompletion:
        del messages, seed
        if not self.available:
            raise ProviderUnavailableError("mock provider is unavailable")
        try:
            response = next(self._responses)
        except StopIteration as exc:
            raise ProviderUnavailableError("mock provider has no scripted response") from exc
        if isinstance(response, ProviderCompletion):
            return response
        if isinstance(response, str):
            return ProviderCompletion(response)
        if isinstance(response, Mapping):
            text = response.get("text", response.get("content"))
            usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else response
            if isinstance(text, str):
                return ProviderCompletion(
                    text,
                    _usage_int(usage, "prompt_tokens", "input_tokens", "token_in"),
                    _usage_int(usage, "completion_tokens", "output_tokens", "token_out"),
                    response.get("model") if isinstance(response.get("model"), str) else None,
                )
        raise ValueError("mock provider response must be text, metadata, or ProviderCompletion")

    def complete_with_usage(
        self,
        messages: Iterable[Message],
        *,
        seed: int | None = None,
    ) -> ProviderCompletion:
        """Backward-compatible spelling for callers that request usage."""

        return self.complete_with_metadata(messages, seed=seed)


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
        timeout: float = 30.0,
        max_tokens: int | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("provider timeout must be greater than zero")
        if max_tokens is not None and max_tokens <= 0:
            raise ValueError("max_tokens must be positive when set")
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self._opener = opener
        self.timeout = timeout
        self.max_tokens = max_tokens

    @property
    def available(self) -> bool:
        return bool(self.endpoint and self.model)

    def complete(self, messages: Iterable[Message]) -> str:
        return self.complete_with_metadata(messages).text

    def complete_with_metadata(
        self,
        messages: Iterable[Message],
        *,
        seed: int | None = None,
    ) -> ProviderCompletion:
        if not self.available:
            raise ProviderUnavailableError("OpenAI-compatible provider is unavailable")

        request_payload: dict[str, Any] = {"model": self.model, "messages": list(messages)}
        if seed is not None:
            request_payload["seed"] = seed
        if self.max_tokens is not None:
            request_payload["max_tokens"] = self.max_tokens
        payload = json.dumps(request_payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            try:
                opener_parameters = inspect.signature(self._opener).parameters.values()
            except (TypeError, ValueError):
                opener_parameters = ()
            accepts_timeout = any(
                parameter.name == "timeout"
                or parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in opener_parameters
            )
            if accepts_timeout:
                response_context = self._opener(request, timeout=self.timeout)
            else:
                response_context = self._opener(request)
            with response_context as response:
                raw = response.read()
        except (OSError, URLError, TimeoutError, socket.timeout) as exc:
            raise ProviderUnavailableError(f"provider request failed: {exc}") from exc

        try:
            body = json.loads(raw.decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid OpenAI-compatible response") from exc
        if not isinstance(content, str):
            raise ValueError("invalid OpenAI-compatible response content")
        usage = body.get("usage")
        if not isinstance(usage, Mapping):
            usage = {}
        return ProviderCompletion(
            content,
            prompt_tokens=_usage_int(usage, "prompt_tokens", "input_tokens"),
            completion_tokens=_usage_int(usage, "completion_tokens", "output_tokens"),
            model=body.get("model") if isinstance(body.get("model"), str) else self.model,
            metadata={"usage": dict(usage)} if usage else {},
        )

    def complete_with_usage(
        self,
        messages: Iterable[Message],
        *,
        seed: int | None = None,
    ) -> ProviderCompletion:
        """Backward-compatible spelling for callers that request usage."""

        return self.complete_with_metadata(messages, seed=seed)


def _usage_int(usage: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None
