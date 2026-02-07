# Short-term session memory (in-memory dict, no Redis dependency)
from __future__ import annotations

from typing import Any

from agent.config.settings import get_settings


class SessionMemory:
  """Per-session short-term memory storing conversation history.

  Uses a plain dict keyed by session_id.
  Automatically truncates to the most recent N turns.
  """

  def __init__(self) -> None:
    self._store: dict[str, list[dict[str, Any]]] = {}

  @property
  def _max_turns(self) -> int:
    return get_settings().MAX_SESSION_TURNS

  # --- public API ---

  def get_history(self, session_id: str) -> list[dict[str, Any]]:
    """Return conversation history for a session."""
    return list(self._store.get(session_id, []))

  def add_message(
    self,
    session_id: str,
    role: str,
    content: str,
  ) -> None:
    """Append a message and truncate if exceeding window."""
    if session_id not in self._store:
      self._store[session_id] = []
    self._store[session_id].append({"role": role, "content": content})
    self._truncate(session_id)

  def clear(self, session_id: str) -> None:
    """Clear all history for a session."""
    self._store.pop(session_id, None)

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
