from dataclasses import dataclass


@dataclass
class LLMRequest:
    prompt: str
    system: str | None = None
    temperature: float = 0.1
    max_tokens: int = 8000
    thinking: bool = False  # Provider-specific: Ollama prepends /think tags, Gemini uses thinking_config