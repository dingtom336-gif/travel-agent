# Short-term session memory (in-memory dict, no Redis dependency)
from __future__ import annotations

import asyncio
from typing import Any

from agent.config.settings import get_settings


class SessionMemory:
  """Per-session short-term memory storing conversation history and agent traces.

  Uses plain dicts keyed by session_id.
  Automatically truncates messages to the most recent N turns.
  All mutating and reading methods are async with lock protection
  for safe concurrent access.
  """

  def __init__(self) -> None:
    self._store: dict[str, list[dict[str, Any]]] = {}
    self._traces: dict[str, list[dict[str, Any]]] = {}
    self._lock = asyncio.Lock()

  @property
  def _max_turns(self) -> int:
    return get_settings().MAX_SESSION_TURNS

  # --- message API ---

  async def get_history(self, session_id: str) -> list[dict[str, Any]]:
    """Return conversation history for a session."""
    async with self._lock:
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
      self._truncate(session_id)

  # --- trace API ---

  async def add_trace(self, session_id: str, trace: dict[str, Any]) -> None:
    """Append an agent execution trace for the session."""
    async with self._lock:
      if session_id not in self._traces:
        self._traces[session_id] = []
      self._traces[session_id].append(trace)

  async def get_traces(self, session_id: str) -> list[dict[str, Any]]:
    """Return all agent traces for a session."""
    async with self._lock:
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

  def exists(self, session_id: str) -> bool:
    """Check if a session exists."""
    return session_id in self._store

  # --- internal ---

  def _truncate(self, session_id: str) -> None:
    """Keep only the latest MAX_SESSION_TURNS turns (pairs)."""
    history = self._store.get(session_id, [])
    max_messages = self._max_turns * 2  # user + assistant per turn
    if len(history) > max_messages:
      self._store[session_id] = history[-max_messages:]


# Singleton instance
session_memory = SessionMemory()
