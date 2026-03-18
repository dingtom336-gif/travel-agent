# Section parser for Theater Mode – splits streaming LLM output into agent sections.
from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncGenerator
from typing import Optional

from agent.models import AgentName, SSEEventType, TaskStatus

# Regex for section markers: <!-- SECTION:name -->
_SECTION_RE = re.compile(r"<!--\s*SECTION:(\w+)\s*-->")

# Map section names to AgentName enum values
_SECTION_TO_AGENT: dict[str, AgentName] = {
  "knowledge": AgentName.KNOWLEDGE,
  "weather": AgentName.WEATHER,
  "transport": AgentName.TRANSPORT,
  "hotel": AgentName.HOTEL,
  "poi": AgentName.POI,
  "itinerary": AgentName.ITINERARY,
  "budget": AgentName.BUDGET,
}


class StreamBuffer:
  """Dual-purpose buffer: real-time streaming via asyncio.Queue + full text after finish."""

  def __init__(self) -> None:
    self._chunks: list[str] = []
    self._queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
    self._done = asyncio.Event()

  async def write(self, chunk: str) -> None:
    """Append chunk and enqueue for stream consumers."""
    self._chunks.append(chunk)
    await self._queue.put(chunk)

  async def stream(self) -> AsyncGenerator[str, None]:
    """Yield chunks in real-time. Ends when finish() is called and queue is drained."""
    import logging as _log
    _logger = _log.getLogger(__name__)
    chunk_count = 0
    while True:
      # Check if done and queue is empty
      if self._done.is_set() and self._queue.empty():
        _logger.info("STREAMBUFFER exiting: done=%s empty=%s chunks=%d", self._done.is_set(), self._queue.empty(), chunk_count)
        break
      try:
        chunk = await asyncio.wait_for(self._queue.get(), timeout=0.5)
        if chunk is None:
          # Sentinel received
          _logger.info("STREAMBUFFER sentinel received after %d chunks", chunk_count)
          break
        chunk_count += 1
        yield chunk
      except asyncio.TimeoutError:
        # Re-check done flag on timeout
        if self._done.is_set() and self._queue.empty():
          _logger.info("STREAMBUFFER timeout exit: done=%s empty=%s chunks=%d", self._done.is_set(), self._queue.empty(), chunk_count)
          break
        continue

  def finish(self) -> None:
    """Signal that no more chunks will arrive."""
    self._done.set()
    # Put sentinel to unblock any waiting consumer
    self._queue.put_nowait(None)

  @property
  def full_text(self) -> str:
    """Join all received chunks into complete text."""
    return "".join(self._chunks)


class SectionDetector:
  """Stateful detector for <!-- SECTION:xxx --> markers that may span chunk boundaries."""

  def __init__(self) -> None:
    self._partial: str = ""

  def detect(self, chunk: str) -> Optional[str]:
    """Check chunk (with carry-over partial) for a section marker.

    Returns section name if found, None otherwise.
    Maintains partial buffer for markers split across chunks.
    """
    text = self._partial + chunk

    m = _SECTION_RE.search(text)
    if m:
      self._partial = ""
      return m.group(1).lower()

    # Keep tail that could be start of a partial marker (<!-- SECTION:...)
    # The longest possible incomplete marker prefix is ~20 chars
    tail_len = min(len(text), 25)
    tail = text[-tail_len:]
    # Check if tail contains a potential partial marker start
    if "<" in tail or "!" in tail or "-" in tail:
      self._partial = tail
    else:
      self._partial = ""

    return None


def detect_section(chunk: str, _detector: list[SectionDetector] | None = None) -> Optional[str]:
  """Module-level convenience – detect section in a single chunk.

  For cross-chunk detection, use SectionDetector instance directly.
  """
  m = _SECTION_RE.search(chunk)
  if m:
    return m.group(1).lower()
  return None


def parse_section_names(full_text: str) -> list[str]:
  """Extract all section names from complete text, in order of appearance."""
  return [m.group(1).lower() for m in _SECTION_RE.finditer(full_text)]


def make_agent_result(section_name: str, content: str) -> dict:
  """Convert a section's content into an AgentResult-compatible SSE dict.

  Returns a dict matching the AGENT_RESULT SSE event format used by
  the existing frontend (see react_loop.py yield patterns).
  """
  agent = _SECTION_TO_AGENT.get(section_name, AgentName.KNOWLEDGE)
  # Strip section markers from content
  clean = _SECTION_RE.sub("", content).strip()

  return {
    "event": SSEEventType.AGENT_RESULT.value,
    "data": {
      "agent": agent.value,
      "status": TaskStatus.SUCCESS.value,
      "summary": clean[:120] if clean else "",
      "data": {"content": clean, "section": section_name},
    },
  }
