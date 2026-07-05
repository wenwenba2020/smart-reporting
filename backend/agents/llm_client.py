"""Shared LLM client — supports OpenRouter and SiliconFlow via OpenAI-compatible SDK."""
from openai import OpenAI

from backend.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Return a singleton OpenAI client. Uses OpenRouter by default, falls back to SiliconFlow."""
    global _client
    if _client is None:
        provider = getattr(settings, 'LLM_API_PROVIDER', 'openrouter')
        if provider == 'siliconflow' or (settings.SILICONFLOW_API_KEY and not settings.OPENROUTER_API_KEY):
            _client = OpenAI(
                api_key=settings.SILICONFLOW_API_KEY,
                base_url="https://api.siliconflow.cn/v1",
            )
        else:
            _client = OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
    return _client


class EmptyLLMResponse(RuntimeError):
    """Raised when an LLM returns a structurally-OK response with empty content."""


def chat(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: dict | None = None,
    extra_body: dict | None = None,
) -> str:
    """Send a chat completion and return the assistant's text response.

    extra_body: passthrough (e.g. {"enable_thinking": False} for Qwen3).
    Raises EmptyLLMResponse when both content and reasoning_content are empty —
    lets callers fail fast and retry rather than silently returning "".
    """
    client = get_client()
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": settings.LLM_TIMEOUT_SECONDS,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if extra_body:
        kwargs["extra_body"] = extra_body

    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message

    # Handle thinking models (Qwen3 etc.) where content may be in reasoning_content
    content = msg.content or ""
    if not content:
        rc = getattr(msg, "reasoning_content", None)
        if rc:
            content = rc

    if not content or not content.strip():
        finish = getattr(resp.choices[0], "finish_reason", "unknown")
        raise EmptyLLMResponse(
            f"LLM {model} returned empty content (finish_reason={finish})"
        )

    return content
