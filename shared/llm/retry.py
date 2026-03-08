"""Retry decorator for LLM calls: backoff on rate limit, no retry on validation error."""

import asyncio
from functools import wraps

from shared.llm.exceptions import LLMRateLimitError, LLMTimeoutError, LLMValidationError

_RETRYABLE = (LLMRateLimitError, LLMTimeoutError)


def with_retry(max_attempts: int = 3, backoff: float = 2.0):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except LLMValidationError:
                    raise
                except _RETRYABLE as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(backoff ** attempt)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
