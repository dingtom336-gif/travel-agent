# Lightweight scheduler for proactive checks
# Uses asyncio tasks instead of APScheduler to avoid extra dependency
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List

logger = logging.getLogger(__name__)

# Registered periodic tasks
_tasks: Dict[str, asyncio.Task] = {}


def schedule_periodic(
  name: str,
  coro_fn: Callable[[], Coroutine[Any, Any, Any]],
  interval_seconds: int = 3600,
) -> None:
  """Schedule a coroutine to run periodically.

  Args:
    name: Unique task name
    coro_fn: Async function to call (no args)
    interval_seconds: Interval between runs (default 1 hour)
  """
  if name in _tasks and not _tasks[name].done():
    logger.debug("Task %s already scheduled", name)
    return

  async def _loop():
    while True:
      try:
        await coro_fn()
      except Exception as exc:
        logger.warning("Scheduled task %s failed: %s", name, exc)
      await asyncio.sleep(interval_seconds)

  task = asyncio.create_task(_loop())
  _tasks[name] = task
  logger.info("Scheduled periodic task: %s (every %ds)", name, interval_seconds)


def cancel_all() -> int:
  """Cancel all scheduled tasks. Returns count of cancelled tasks."""
  count = 0
  for name, task in _tasks.items():
    if not task.done():
      task.cancel()
      count += 1
      logger.info("Cancelled scheduled task: %s", name)
  _tasks.clear()
  return count


def list_tasks() -> List[str]:
  """List names of active scheduled tasks."""
  return [name for name, task in _tasks.items() if not task.done()]
