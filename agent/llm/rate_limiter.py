# Token-bucket rate limiter with concurrency control for LLM API calls
from __future__ import annotations

import asyncio
import logging
import time

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
  """Async token-bucket rate limiter with concurrency semaphore.

  Limits requests to LLM_RATE_LIMIT_RPM per minute AND
  LLM_MAX_CONCURRENT simultaneous requests.
  """

  def __init__(self) -> None:
    settings = get_settings()
    self._rpm = settings.LLM_RATE_LIMIT_RPM
    # Start with a small burst allowance to avoid flooding the API
    self._tokens = float(min(10, self._rpm))
    self._max_tokens = float(self._rpm)
    self._refill_rate = self._rpm / 60.0  # tokens per second
    self._last_refill = time.monotonic()
    self._lock = asyncio.Lock()
    self._semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENT)

  def _refill(self) -> None:
    """Add tokens based on elapsed time since last refill."""
    now = time.monotonic()
    elapsed = now - self._last_refill
    self._tokens = min(
      self._max_tokens,
      self._tokens + elapsed * self._refill_rate,
    )
    self._last_refill = now

  async def acquire(self) -> None:
    """Wait for both a concurrency slot and a rate-limit token."""
    await self._semaphore.acquire()

    async with self._lock:
      self._refill()
      if self._tokens >= 1.0:
        self._tokens -= 1.0
        return

      # Calculate wait time for one token
      deficit = 1.0 - self._tokens
      wait_time = deficit / self._refill_rate
      logger.info(
        "Rate limit: waiting %.2fs for next token (rpm=%d)",
        wait_time, self._rpm,
      )

    # Sleep outside the lock so other coroutines can proceed
    await asyncio.sleep(wait_time)

    async with self._lock:
      self._refill()
      self._tokens = max(0.0, self._tokens - 1.0)

  def release(self) -> None:
    """Release the concurrency slot after the LLM call completes."""
    self._semaphore.release()


# Singleton instance
rate_limiter = TokenBucketRateLimiter()
