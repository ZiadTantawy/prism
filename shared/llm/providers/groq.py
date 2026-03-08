"""Groq provider using the official groq Python SDK (AsyncGroq).
Ref: https://github.com/groq/groq-python
"""

from __future__ import annotations

import asyncio

from groq import AsyncGroq
from groq import APIStatusError

from shared.config import settings
from shared.llm.base import BaseLLMClient
from shared.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from shared.llm.schemas.llm_request import LLMRequest
from shared.llm.schemas.llm_response import LLMResponse


def _finish_reason(reason: str | None) -> str:
    if reason == "length":
        return "length"
    return "stop"


def _map_error(e: Exception) -> LLMError:
    status = getattr(e, "status_code", None) or getattr(e, "code", None)
    if status == 429:
        return LLMRateLimitError(str(e))
    if status in (400, 422):
        return LLMValidationError(str(e))
    return LLMError(str(e))


def _normalize_groq_base_url(url: str) -> str:
    """Strip /openai/v1 from base URL; the SDK appends it, so we avoid duplication."""
    u = url.rstrip("/")
    for suffix in ("/openai/v1", "/openai/v1/"):
        if u.endswith(suffix):
            return u[: -len(suffix)].rstrip("/") or "https://api.groq.com"
    return u


class Groq(BaseLLMClient):
    """Groq chat completions via the official groq AsyncGroq client."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        super().__init__(model)
        self._api_key = api_key or (settings.GROQ_API_KEY.get_secret_value() if settings.GROQ_API_KEY else "")
        raw = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self._base_url = _normalize_groq_base_url(raw)
        self._timeout = timeout
        self._client: AsyncGroq | None = None

    def _get_client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        # request.thinking is ignored (Ollama-only feature).
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise LLMValidationError("GROQ_API_KEY is required")
        client = self._get_client()
        try:
            completion = await client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(request),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except APIStatusError as e:
            raise _map_error(e) from e
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise LLMTimeoutError(str(e)) from e
            raise LLMError(str(e)) from e

        choices = completion.choices or []
        if not choices:
            return LLMResponse(
                content="",
                model=completion.model or self.model,
                input_tokens=0,
                output_tokens=0,
                finish_reason="stop",
            )
        choice = choices[0]
        content = (choice.message.content or "") if choice.message else ""
        reason = getattr(choice, "finish_reason", None)
        usage = completion.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            content=content,
            model=completion.model or self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=_finish_reason(reason),
        )

    async def close(self) -> None:
        if self._client is not None:
            if hasattr(self._client, "aclose"):
                await self._client.aclose()
            elif hasattr(self._client, "close"):
                close_fn = self._client.close
                if asyncio.iscoroutinefunction(close_fn):
                    await close_fn()
                else:
                    close_fn()
            self._client = None
