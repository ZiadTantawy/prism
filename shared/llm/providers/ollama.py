"""Ollama provider using the official ollama-python library.
Ref: https://github.com/ollama/ollama-python
"""

from __future__ import annotations

import asyncio

from ollama import AsyncClient
from ollama import ResponseError

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


def _map_error(e: ResponseError) -> LLMError:
    code = getattr(e, "status_code", None) or 500
    if code == 429:
        return LLMRateLimitError(str(e))
    if code in (400, 422):
        return LLMValidationError(str(e))
    return LLMError(str(e))


class Ollama(BaseLLMClient):
    """Ollama chat API via the official ollama-python AsyncClient."""

    def __init__(
        self,
        model: str,
        *,
        host: str | None = None,
        timeout: float | None = None,
    ):
        super().__init__(model)
        self._host = host or settings.OLLAMA_BASE_URL
        self._timeout = timeout
        self._client: AsyncClient | None = None

    def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = AsyncClient(host=self._host, timeout=self._timeout)
        return self._client

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system:
            system_text = request.system
            if self._supports_thinking():
                system_text = f"{'/think' if request.thinking else '/no_think'} {system_text}"
            messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    def _supports_thinking(self) -> bool:
        """Only models with native thinking support use /think and /no_think tags."""
        return any(tag in self.model.lower() for tag in ("qwen3", "qwq", "deepseek-r1"))

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        try:
            response = await client.chat(
                model=self.model,
                messages=self._build_messages(request),
                stream=False,
                options={
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            )
        except ResponseError as e:
            raise _map_error(e) from e
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                raise LLMTimeoutError(str(e)) from e
            raise LLMError(str(e)) from e

        content = (response.message.content or "") if response.message else ""
        reason = getattr(response, "done_reason", None) or "stop"
        input_tokens = getattr(response, "prompt_eval_count", None) or 0
        output_tokens = getattr(response, "eval_count", None) or 0
        model_name = getattr(response, "model", None) or self.model

        return LLMResponse(
            content=content,
            model=model_name,
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
