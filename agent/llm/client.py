# Unified LLM client – OpenAI-compatible API (DeepSeek / OpenAI / etc.)
from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

# Module-level client cache
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI | None:
  """Lazily create and cache an AsyncOpenAI client."""
  global _client
  if _client is not None:
    return _client
  settings = get_settings()
  if not settings.DEEPSEEK_API_KEY:
    return None
  _client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
  )
  return _client


async def llm_chat(
  *,
  system: str,
  messages: list[dict[str, str]],
  max_tokens: int = 4096,
  temperature: float = 0.7,
) -> str | None:
  """Send a chat completion request to the configured LLM provider.

  Returns the assistant message content, or None if no API key is set.
  Raises on API errors so callers can handle fallback.
  """
  client = _get_client()
  if client is None:
    return None

  settings = get_settings()

  # Build messages list with system prompt
  full_messages: list[dict[str, Any]] = [
    {"role": "system", "content": system},
  ]
  full_messages.extend(messages)

  response = await client.chat.completions.create(
    model=settings.DEEPSEEK_MODEL,
    max_tokens=max_tokens,
    temperature=temperature,
    messages=full_messages,
  )
  choice = response.choices[0]
  return choice.message.content or ""
