# Async database engine and session management
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_db_available = False


async def init_db() -> bool:
  """Initialize database engine. Returns True if DB is available."""
  global _engine, _session_factory, _db_available
  settings = get_settings()

  if not settings.DATABASE_URL:
    logger.info("DATABASE_URL not set, using in-memory storage")
    return False

  try:
    from sqlalchemy.ext.asyncio import (
      AsyncSession,
      async_sessionmaker,
      create_async_engine,
    )

    _engine = create_async_engine(
      settings.DATABASE_URL,
      echo=settings.DATABASE_ECHO,
      pool_size=settings.DATABASE_POOL_SIZE,
      max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )

    # Test connection
    async with _engine.begin() as conn:
      await conn.execute(
        __import__("sqlalchemy").text("SELECT 1")
      )

    _session_factory = async_sessionmaker(
      _engine, class_=AsyncSession, expire_on_commit=False,
    )
    _db_available = True
    logger.info("Database connected: %s", settings.DATABASE_URL.split("@")[-1])
    return True
  except Exception as exc:
    logger.warning("Database unavailable, falling back to in-memory: %s", exc)
    _db_available = False
    return False


async def close_db() -> None:
  """Dispose of the database engine."""
  global _engine, _db_available
  if _engine:
    await _engine.dispose()
    _engine = None
    _db_available = False
    logger.info("Database connection closed")


def is_db_available() -> bool:
  """Check if database is connected."""
  return _db_available


@asynccontextmanager
async def get_db_session() -> AsyncGenerator:
  """Yield an async database session."""
  if not _session_factory:
    raise RuntimeError("Database not initialized. Call init_db() first.")
  session = _session_factory()
  try:
    yield session
    await session.commit()
  except Exception:
    await session.rollback()
    raise
  finally:
    await session.close()
