# Model router – decides whether to use quick reply or full ReAct loop
# v0.7.0: Replaced LLM classification with local intent classifier (< 1ms)
from __future__ import annotations

import logging
from typing import Any

from agent.orchestrator.intent_classifier import intent_classifier

logger = logging.getLogger(__name__)


async def classify_complexity(
  user_message: str,
  conversation_history: list[dict[str, Any]] | None = None,
  has_travel_context: bool = False,
) -> str:
  """Return 'simple' or 'complex' for the given message.

  Uses local intent classifier for instant classification (< 1ms).
  No LLM calls – eliminates the ~20s Router latency.
  """
  label, confidence = intent_classifier.classify(
    user_message, has_travel_context=has_travel_context,
  )
  return label
