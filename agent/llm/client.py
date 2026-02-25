# Unified LLM client – OpenAI-compatible API (DeepSeek / OpenAI / etc.)
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from collections.abc import AsyncGenerator
from typing import Any, Optional, Tuple

import httpx
from openai import AsyncOpenAI

from agent.config.settings import get_settings
from agent.llm.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Module-level client cache
_client: Optional[AsyncOpenAI] = None

MAX_RETRIES = 2
RETRY_DELAY = 0.5  # seconds


def _get_client() -> Optional[AsyncOpenAI]:
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


# --- LRU response cache ---

# Entry: (response_str, timestamp)
_cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
_cache_lock = asyncio.Lock()


def _cache_key(
  system: str,
  messages: list[dict[str, str]],
  model: Optional[str],
  max_tokens: int,
  temperature: float,
) -> str:
  """Compute a deterministic cache key from request parameters."""
  payload = json.dumps(
    {"s": system, "m": messages, "model": model,
     "mt": max_tokens, "t": temperature},
    sort_keys=True, ensure_ascii=False,
  )
  return hashlib.sha256(payload.encode()).hexdigest()


async def _cache_get(key: str) -> Optional[str]:
  """Return cached response if key exists and not expired."""
  settings = get_settings()
  async with _cache_lock:
    if key not in _cache:
      return None
    response, ts = _cache[key]
    if (time.monotonic() - ts) > settings.LLM_CACHE_TTL:
      _cache.pop(key, None)
      return None
    # Move to end (most recently used)
    _cache.move_to_end(key)
    return response


async def _cache_put(key: str, response: str) -> None:
  """Store response in cache, evicting oldest if over size limit."""
  settings = get_settings()
  async with _cache_lock:
    if key in _cache:
      _cache.move_to_end(key)
      _cache[key] = (response, time.monotonic())
      return
    _cache[key] = (response, time.monotonic())
    while len(_cache) > settings.LLM_CACHE_SIZE:
      _cache.popitem(last=False)


async def llm_chat(
  *,
  system: str,
  messages: list[dict[str, str]],
  max_tokens: int = 2048,
  temperature: float = 0.7,
  model: Optional[str] = None,
) -> Optional[str]:
  """Send a chat completion request with retry, caching, and rate limiting.

  Returns the assistant message content, or None if no API key is set.
  Raises on API errors so callers can handle fallback.
  """
  client = _get_client()
  if client is None:
    return None

  settings = get_settings()
  resolved_model = model or settings.DEEPSEEK_MODEL

  # Check cache first
  key = _cache_key(system, messages, resolved_model, max_tokens, temperature)
  cached = await _cache_get(key)
  if cached is not None:
    logger.debug("LLM cache hit (key=%s...)", key[:8])
    return cached

  full_messages: list[dict[str, Any]] = [
    {"role": "system", "content": system},
  ]
  full_messages.extend(messages)

  for attempt in range(MAX_RETRIES + 1):
    try:
      await rate_limiter.acquire()
      response = await client.chat.completions.create(
        model=resolved_model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
      )
      result = response.choices[0].message.content or ""
      await _cache_put(key, result)
      return result
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
  model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
  """Stream chat completion, yielding content chunks.

  Yields empty string once if no API key is set.
  Not cached (streaming responses are consumed incrementally).
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

  chunk_timeout = settings.LLM_STREAM_CHUNK_TIMEOUT

  for attempt in range(MAX_RETRIES + 1):
    try:
      await rate_limiter.acquire()
      stream = await client.chat.completions.create(
        model=model or settings.DEEPSEEK_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=full_messages,
        stream=True,
      )
      # Per-chunk timeout: if no chunk arrives within chunk_timeout, end stream
      ait = stream.__aiter__()
      while True:
        try:
          chunk = await asyncio.wait_for(
            ait.__anext__(), timeout=chunk_timeout,
          )
        except StopAsyncIteration:
          break
        except asyncio.TimeoutError:
          logger.warning(
            "LLM stream chunk timeout (%.0fs), ending stream",
            chunk_timeout,
          )
          break
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
