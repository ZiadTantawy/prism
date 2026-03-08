from __future__ import annotations

from abc import ABC, abstractmethod
from shared.llm.schemas.llm_response import LLMResponse
from shared.llm.schemas.llm_request import LLMRequest

class BaseLLMClient(ABC):
    def __init__(self, model: str):
        self.model = model
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> BaseLLMClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()