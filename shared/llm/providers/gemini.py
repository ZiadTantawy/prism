from __future__ import annotations

from google import genai
from google.genai import errors
from google.genai.types import GenerateContentConfig, HttpOptions

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
from shared.logger import get_logger

logger = get_logger(__name__)


def _normalize_gemini_base_url(url: str) -> str:
    """Strip trailing slash and /v1beta (or /v1, /v1alpha) so the SDK can append
    api_version once. The SDK builds URL as base_url + '/' + api_version + '/' + path.
    If we pass base_url with /v1beta we get .../v1beta/v1beta/models/... and the API fails.
    """
    u = url.rstrip("/")
    for suffix in ("/v1beta", "/v1alpha", "/v1"):
        if u.endswith(suffix):
            return u[: -len(suffix)]
    return u


def _finish_reason(reason: str | None) -> str:
    if reason == "MAX_TOKENS":
        return "length"
    return "stop"


def _map_error(e: errors.APIError | Exception) -> LLMError:
    """Map SDK APIError (has .code) or generic Exception to LLMError subtypes."""
    status = getattr(e, "code", None) or getattr(e, "status_code", None)
    if status == 429:
        return LLMRateLimitError(str(e))
    if status in (400, 422):
        return LLMValidationError(str(e))
    return LLMError(str(e))


def _is_timeout(e: Exception) -> bool:
    return (
        "timeout" in str(e).lower()
        or "timed out" in str(e).lower()
        or "Timeout" in type(e).__name__
    )


class Gemini(BaseLLMClient):
    """Google Gemini via the official google-genai SDK (async via client.aio)."""

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        timeout: float = 120.0,
    ):
        super().__init__(model)
        gemini_key = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else ""
        self._api_key = api_key or gemini_key
        self._timeout_ms = int(timeout * 1000)
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            base_url = _normalize_gemini_base_url(settings.GEMINI_BASE_URL)
            http_options = HttpOptions(base_url=base_url, timeout=self._timeout_ms)
            logger.debug("Gemini client: base_url=%s timeout_ms=%s", base_url, self._timeout_ms)
            self._client = genai.Client(api_key=self._api_key, http_options=http_options)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise LLMValidationError("GEMINI_API_KEY is required")

        client = self._get_client()
        logger.info(
            "Gemini generate: model=%s prompt_len=%s temperature=%s max_tokens=%s has_system=%s thinking=%s",
            self.model,
            len(request.prompt),
            request.temperature,
            request.max_tokens,
            bool(request.system),
            request.thinking,
        )

        config_kw: dict = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }
        if request.system:
            config_kw["system_instruction"] = request.system
        if request.thinking:
            # Gemini 3 Flash supports thinking_config natively
            config_kw["thinking_config"] = {"thinking_budget": 8000}

        config = GenerateContentConfig(**config_kw)

        try:
            # client.aio is an attribute exposing async methods, not a context manager
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=request.prompt,
                config=config,
            )
        except errors.APIError as e:
            logger.warning(
                "Gemini APIError: type=%s code=%s message=%s",
                type(e).__name__,
                getattr(e, "code", None),
                str(e),
                exc_info=True,
            )
            if _is_timeout(e):
                raise LLMTimeoutError(str(e)) from e
            raise _map_error(e) from e
        except Exception as e:
            logger.warning(
                "Gemini request failed: type=%s message=%s",
                type(e).__name__,
                str(e),
                exc_info=True,
            )
            if _is_timeout(e):
                raise LLMTimeoutError(str(e)) from e
            raise _map_error(e) from e

        content = (getattr(response, "text", None) or "").strip()
        finish_reason = "stop"
        if response.candidates:
            c = response.candidates[0]
            finish_reason = _finish_reason(str(c.finish_reason) if c.finish_reason else None)

        input_tokens = 0
        output_tokens = 0
        if response.usage_metadata:
            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = (
                response.usage_metadata.candidates_token_count
                or response.usage_metadata.total_token_count
                or 0
            )

        logger.debug(
            "Gemini response: content_len=%s finish_reason=%s input_tokens=%s output_tokens=%s",
            len(content),
            finish_reason,
            input_tokens,
            output_tokens,
        )

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
        )

    async def close(self) -> None:
        self._client = None