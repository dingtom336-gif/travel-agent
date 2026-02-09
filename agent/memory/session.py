# Short-term session memory (in-memory dict, no Redis dependency)
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)


class SessionMemory:
  """Per-session short-term memory storing conversation history and agent traces.

  Uses plain dicts keyed by session_id.
  Automatically truncates messages to the most recent N turns.
  Evicts stale sessions (TTL) and enforces max session count (LRU).
  All mutating and reading methods are async with lock protection
  for safe concurrent access.
  """

  def __init__(self) -> None:
    self._store: dict[str, list[dict[str, Any]]] = {}
    self._traces: dict[str, list[dict[str, Any]]] = {}
    self._timestamps: dict[str, float] = {}
    self._lock = asyncio.Lock()

  @property
  def _max_turns(self) -> int:
    return get_settings().MAX_SESSION_TURNS

  # --- message API ---

  async def get_history(self, session_id: str) -> list[dict[str, Any]]:
    """Return conversation history for a session."""
    async with self._lock:
      self._touch(session_id)
      return list(self._store.get(session_id, []))

  async def add_message(
    self,
    session_id: str,
    role: str,
    content: str,
  ) -> None:
    """Append a message and truncate if exceeding window."""
    async with self._lock:
      if session_id not in self._store:
        self._store[session_id] = []
      self._store[session_id].append({"role": role, "content": content})
      self._touch(session_id)
      self._truncate(session_id)
      self._evict_stale_sessions()

  # --- trace API ---

  async def add_trace(self, session_id: str, trace: dict[str, Any]) -> None:
    """Append an agent execution trace for the session."""
    async with self._lock:
      if session_id not in self._traces:
        self._traces[session_id] = []
      self._traces[session_id].append(trace)
      self._touch(session_id)
      self._truncate_traces(session_id)

  async def get_traces(self, session_id: str) -> list[dict[str, Any]]:
    """Return all agent traces for a session."""
    async with self._lock:
      self._touch(session_id)
      return list(self._traces.get(session_id, []))

  # --- session management ---

  def list_sessions(self) -> list[str]:
    """Return all session IDs that have history."""
    return list(self._store.keys())

  async def clear(self, session_id: str) -> None:
    """Clear all history and traces for a session."""
    async with self._lock:
      self._store.pop(session_id, None)
      self._traces.pop(session_id, None)
      self._timestamps.pop(session_id, None)

  def exists(self, session_id: str) -> bool:
    """Check if a session exists."""
    return session_id in self._store

  # --- internal ---

  def _touch(self, session_id: str) -> None:
    """Update last-access timestamp for a session."""
    if session_id in self._store or session_id in self._traces:
      self._timestamps[session_id] = time.monotonic()

  def _truncate(self, session_id: str) -> None:
    """Keep only the latest MAX_SESSION_TURNS turns (pairs)."""
    history = self._store.get(session_id, [])
    max_messages = self._max_turns * 2  # user + assistant per turn
    if len(history) > max_messages:
      self._store[session_id] = history[-max_messages:]

  def _truncate_traces(self, session_id: str) -> None:
    """Keep only the latest TRACE_MAX_PER_SESSION traces."""
    traces = self._traces.get(session_id, [])
    max_traces = get_settings().TRACE_MAX_PER_SESSION
    if len(traces) > max_traces:
      self._traces[session_id] = traces[-max_traces:]

  def _evict_stale_sessions(self) -> None:
    """Remove expired sessions and LRU-evict if over max count.

    Called inside the lock from add_message.
    """
    settings = get_settings()
    now = time.monotonic()
    ttl = settings.SESSION_TTL_SECONDS
    max_count = settings.SESSION_MAX_COUNT

    # Phase 1: evict sessions older than TTL
    expired = [
      sid for sid, ts in self._timestamps.items()
      if (now - ts) > ttl
    ]
    for sid in expired:
      self._remove_session(sid)

    if expired:
      logger.info("Evicted %d expired sessions (TTL=%ds)", len(expired), ttl)

    # Phase 2: LRU evict if still over max count
    if len(self._store) > max_count:
      sorted_sessions = sorted(
        self._timestamps.items(), key=lambda x: x[1],
      )
      to_evict = len(self._store) - max_count
      for sid, _ in sorted_sessions[:to_evict]:
        self._remove_session(sid)
      logger.info(
        "LRU-evicted %d sessions (max=%d)", to_evict, max_count,
      )

  def _remove_session(self, session_id: str) -> None:
    """Remove all data for a session (no lock, caller holds lock)."""
    self._store.pop(session_id, None)
    self._traces.pop(session_id, None)
    self._timestamps.pop(session_id, None)

  def get_stale_session_ids(self) -> list[str]:
    """Return session IDs that have exceeded TTL (for cross-module cleanup).

    This is a sync method meant to be called by other memory modules
    inside their own locks.
    """
    now = time.monotonic()
    ttl = get_settings().SESSION_TTL_SECONDS
    return [
      sid for sid, ts in self._timestamps.items()
      if (now - ts) > ttl
    ]


# Singleton instance
session_memory = SessionMemory()
