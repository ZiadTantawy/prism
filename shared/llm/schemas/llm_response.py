from dataclasses import dataclass
from typing import Literal

@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: Literal["stop", "length", "error"] = "stop"