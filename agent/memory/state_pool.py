# Global state pool – maintains extracted travel parameters per session
from __future__ import annotations

import logging
from typing import Any

from agent.models import SessionState

logger = logging.getLogger(__name__)


class StatePool:
  """Manages a SessionState object per session.

  The state pool stores slot values extracted from the conversation
  (destination, dates, budget, etc.) so that downstream agents
  can access shared context without re-parsing.
  """

  def __init__(self) -> None:
    self._pool: dict[str, SessionState] = {}

  def get(self, session_id: str) -> SessionState:
    """Get or create a SessionState for the session."""
    if session_id not in self._pool:
      self._pool[session_id] = SessionState()
    return self._pool[session_id]

  def update(self, session_id: str, **kwargs: Any) -> SessionState:
    """Update specific slots in the session state."""
    state = self.get(session_id)
    for key, value in kwargs.items():
      if value is not None and hasattr(state, key):
        old_value = getattr(state, key)
        if old_value is not None and old_value != value:
          logger.info(
            "State '%s' overwritten: '%s' -> '%s' (session=%s)",
            key, old_value, value, session_id[:8],
          )
        setattr(state, key, value)
    return state

  def update_from_dict(self, session_id: str, data: dict[str, Any]) -> SessionState:
    """Bulk update from a dictionary (e.g. extracted by Claude)."""
    return self.update(session_id, **data)

  def clear(self, session_id: str) -> None:
    """Reset state for a session."""
    self._pool.pop(session_id, None)

  def to_prompt_context(self, session_id: str) -> str:
    """Serialize current state as a readable string for prompts."""
    state = self.get(session_id)
    parts: list[str] = []
    if state.destination:
      parts.append(f"Destination: {state.destination}")
    if state.origin:
      parts.append(f"Origin: {state.origin}")
    if state.start_date:
      parts.append(f"Start date: {state.start_date}")
    if state.end_date:
      parts.append(f"End date: {state.end_date}")
    if state.duration_days:
      parts.append(f"Duration: {state.duration_days} days")
    if state.travelers:
      parts.append(f"Travelers: {state.travelers}")
    if state.budget:
      parts.append(f"Budget: {state.budget}")
    if state.preferences:
      parts.append(f"Preferences: {state.preferences}")
    if state.constraints:
      parts.append(f"Constraints: {', '.join(state.constraints)}")
    return "\n".join(parts) if parts else "No travel parameters extracted yet."


# Singleton instance
state_pool = StatePool()
