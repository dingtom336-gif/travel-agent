# Unified LLM client – OpenAI-compatible API (DeepSeek / OpenAI / etc.)
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from openai import AsyncOpenAI

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

# Module-level client cache
_client: AsyncOpenAI | None = None

MAX_RETRIES = 1
RETRY_DELAY = 1.0  # seconds


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
    timeout=httpx.Timeout(settings.LLM_TIMEOUT, connect=5.0),
  )
  return _client


async def llm_chat(
  *,
  system: str,
  messages: list[dict[str, str]],
  max_tokens: int = 2048,
  temperature: float = 0.7,
) -> str | None:
  """Send a chat completion request with retry.

  Returns the assistant message content, or None if no API key is set.
  Raises on API errors so callers can handle fallback.
  """
  client = _get_client()
  if client is None:
    return None

  settings = get_settings()

  full_messages: list[dict[str, Any]] = [
    {"role": "system", "content": system},
  ]
  full_messages.extend(messages)

  for attempt in range(MAX_RETRIES + 1):
    try:
      response = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
      )
      return response.choices[0].message.content or ""
    except Exception as exc:
      if attempt < MAX_RETRIES:
        delay = RETRY_DELAY * (2 ** attempt)
        logger.warning(
          "LLM call attempt %d failed: %s, retrying in %.1fs",
          attempt + 1, exc, delay,
        )
        await asyncio.sleep(delay)
      else:
        raise


async def llm_chat_stream(
  *,
  system: str,
  messages: list[dict[str, str]],
  max_tokens: int = 2048,
  temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
  """Stream chat completion, yielding content chunks.

  Yields empty string once if no API key is set.
  """
  client = _get_client()
  if client is None:
    yield ""
    return

  settings = get_settings()

  full_messages: list[dict[str, Any]] = [
    {"role": "system", "content": system},
  ]
  full_messages.extend(messages)

  for attempt in range(MAX_RETRIES + 1):
    try:
      stream = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
        stream=True,
      )
      async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
          yield delta
      return  # success, exit retry loop
    except Exception as exc:
      if attempt < MAX_RETRIES:
        delay = RETRY_DELAY * (2 ** attempt)
        logger.warning(
          "LLM stream attempt %d failed: %s, retrying in %.1fs",
          attempt + 1, exc, delay,
        )
        await asyncio.sleep(delay)
      else:
        raise
