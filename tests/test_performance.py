# Performance gate tests – block slow code from shipping
from __future__ import annotations

import asyncio
import time

import pytest

from agent.orchestrator.intent_classifier import intent_classifier


class TestIntentClassifierPerformance:
  """Performance thresholds for the local intent classifier."""

  def test_latency_under_10ms(self):
    """Intent classifier must complete in < 10ms per call."""
    start = time.time()
    iterations = 100
    for _ in range(iterations):
      intent_classifier.classify("帮我规划3天东京旅行", has_travel_context=False)
    elapsed_per_call = (time.time() - start) / iterations
    assert elapsed_per_call < 0.01, (
      f"Intent classifier too slow: {elapsed_per_call*1000:.1f}ms (max 10ms)"
    )

  def test_accuracy_simple_messages(self):
    """Simple messages must be classified as 'simple'."""
    simple_cases = [
      ("你好", False),
      ("谢谢", False),
      ("ok", False),
      ("好的", False),
      ("嗯", False),
      ("hi", False),
      ("hello", False),
      ("再见", False),
    ]
    for msg, ctx in simple_cases:
      label, _ = intent_classifier.classify(msg, has_travel_context=ctx)
      assert label == "simple", f"Expected 'simple' for '{msg}' (ctx={ctx}), got '{label}'"

  def test_accuracy_complex_messages(self):
    """Complex travel messages must be classified as 'complex'."""
    complex_cases = [
      ("帮我规划3天东京旅行", False),
      ("5天泰国曼谷+清迈深度游", False),
      ("预算1万去日本", False),
      ("推荐一些东京的景点", False),
      ("从上海出发去大阪的机票", False),
    ]
    for msg, ctx in complex_cases:
      label, _ = intent_classifier.classify(msg, has_travel_context=ctx)
      assert label == "complex", f"Expected 'complex' for '{msg}' (ctx={ctx}), got '{label}'"

  def test_context_dependent_classification(self):
    """Short messages with travel context should be 'complex'."""
    # With travel context, even short messages are follow-ups
    label, _ = intent_classifier.classify("明天", has_travel_context=True)
    assert label == "complex", "Expected 'complex' for '明天' with travel context"

    # Without context, non-greeting short messages default based on features
    # "明天" is not a greeting word, has no travel keywords → score near 0 → simple
    label, _ = intent_classifier.classify("你好", has_travel_context=False)
    assert label == "simple", "Expected 'simple' for '你好' without travel context"


class TestFirstEventLatency:
  """Verify first SSE event arrives quickly."""

  @pytest.mark.asyncio
  async def test_simple_message_first_event_under_200ms(self):
    """Simple message must yield first SSE event in < 200ms."""
    from agent.orchestrator.agent import orchestrator

    start = time.time()
    first_event = None
    async for event in orchestrator.handle_message("perf-test-simple", "你好"):
      first_event = event
      break  # Only measure time to first event
    elapsed_ms = (time.time() - start) * 1000
    assert first_event is not None, "No SSE event received"
    assert elapsed_ms < 200, f"First event too slow: {elapsed_ms:.0f}ms (max 200ms)"

  @pytest.mark.asyncio
  async def test_complex_message_first_event_under_200ms(self):
    """Complex message must yield first SSE event in < 200ms."""
    from agent.orchestrator.agent import orchestrator

    start = time.time()
    first_event = None
    async for event in orchestrator.handle_message("perf-test-complex", "帮我规划3天东京旅行"):
      first_event = event
      break
    elapsed_ms = (time.time() - start) * 1000
    assert first_event is not None, "No SSE event received"
    assert elapsed_ms < 200, f"First event too slow: {elapsed_ms:.0f}ms (max 200ms)"
