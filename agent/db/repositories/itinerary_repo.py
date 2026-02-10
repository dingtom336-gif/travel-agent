# Itinerary CRUD repository
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any, Optional

from agent.db.engine import get_db_session, is_db_available

logger = logging.getLogger(__name__)

# In-memory fallback store
_memory_store: dict[str, dict[str, Any]] = {}


class ItineraryRepository:
  """Itinerary CRUD – uses DB when available, in-memory fallback."""

  async def list_by_user(
    self, user_id: str, limit: int = 50,
  ) -> list[dict[str, Any]]:
    """List itineraries for a user."""
    try:
      if is_db_available():
        return await self._db_list_by_user(user_id, limit)
    except Exception as exc:
      logger.warning("DB list_by_user failed: %s", exc)
    # Fallback to memory
    return [
      v for v in _memory_store.values()
      if v.get("user_id") == user_id
    ][:limit]

  async def get_by_id(self, itinerary_id: str) -> Optional[dict[str, Any]]:
    """Get a single itinerary with days and budget."""
    try:
      if is_db_available():
        return await self._db_get_by_id(itinerary_id)
    except Exception as exc:
      logger.warning("DB get_by_id failed: %s", exc)
    return _memory_store.get(itinerary_id)

  async def create(self, data: dict[str, Any]) -> dict[str, Any]:
    """Create a new itinerary."""
    itinerary_id = data.get("id") or str(uuid.uuid4())
    data["id"] = itinerary_id
    data.setdefault("status", "draft")
    data.setdefault("currency", "CNY")
    data.setdefault("travelers", 1)
    data.setdefault("created_at", datetime.utcnow().isoformat())

    try:
      if is_db_available():
        return await self._db_create(data)
    except Exception as exc:
      logger.warning("DB create failed: %s", exc)

    _memory_store[itinerary_id] = data
    return data

  async def update(
    self, itinerary_id: str, data: dict[str, Any],
  ) -> Optional[dict[str, Any]]:
    """Update an existing itinerary."""
    try:
      if is_db_available():
        return await self._db_update(itinerary_id, data)
    except Exception as exc:
      logger.warning("DB update failed: %s", exc)

    if itinerary_id not in _memory_store:
      return None
    _memory_store[itinerary_id].update(data)
    return _memory_store[itinerary_id]

  async def delete(self, itinerary_id: str) -> bool:
    """Delete an itinerary."""
    try:
      if is_db_available():
        return await self._db_delete(itinerary_id)
    except Exception as exc:
      logger.warning("DB delete failed: %s", exc)

    return _memory_store.pop(itinerary_id, None) is not None

  # ------------------------------------------------------------------ #
  # DB implementations
  # ------------------------------------------------------------------ #

  async def _db_list_by_user(
    self, user_id: str, limit: int,
  ) -> list[dict[str, Any]]:
    from sqlalchemy import select
    from agent.db.models import Itinerary

    async with get_db_session() as session:
      stmt = (
        select(Itinerary)
        .where(Itinerary.session_id == user_id)
        .order_by(Itinerary.created_at.desc())
        .limit(limit)
      )
      result = await session.execute(stmt)
      rows = result.scalars().all()
      return [self._row_to_dict(r) for r in rows]

  async def _db_get_by_id(self, itinerary_id: str) -> Optional[dict[str, Any]]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from agent.db.models import Itinerary

    async with get_db_session() as session:
      stmt = (
        select(Itinerary)
        .options(
          selectinload(Itinerary.days),
          selectinload(Itinerary.budget_items),
        )
        .where(Itinerary.id == uuid.UUID(itinerary_id))
      )
      result = await session.execute(stmt)
      row = result.scalar_one_or_none()
      if not row:
        return None
      data = self._row_to_dict(row)
      data["days"] = [
        {
          "day": d.day_number, "date": str(d.date) if d.date else None,
          "title": d.title or f"Day {d.day_number}",
          "items": d.items or [],
        }
        for d in row.days
      ]
      data["budget_items"] = [
        {
          "category": b.category, "name": b.name,
          "amount": float(b.amount), "currency": b.currency,
          "day": b.day, "note": b.note,
        }
        for b in row.budget_items
      ]
      return data

  async def _db_create(self, data: dict[str, Any]) -> dict[str, Any]:
    from agent.db.models import BudgetItem, Itinerary, ItineraryDay

    async with get_db_session() as session:
      itinerary = Itinerary(
        id=uuid.UUID(data["id"]),
        session_id=data.get("session_id"),
        title=data.get("title", "Untitled Trip"),
        destination=data.get("destination", ""),
        start_date=_parse_date(data.get("start_date")),
        end_date=_parse_date(data.get("end_date")),
        travelers=data.get("travelers", 1),
        total_budget=data.get("total_budget"),
        currency=data.get("currency", "CNY"),
        status=data.get("status", "draft"),
      )
      session.add(itinerary)

      for day_data in data.get("days", []):
        day = ItineraryDay(
          itinerary_id=itinerary.id,
          day_number=day_data.get("day", 1),
          date=_parse_date(day_data.get("date")),
          title=day_data.get("title"),
          items=day_data.get("items", []),
        )
        session.add(day)

      for bi_data in data.get("budget_items", []):
        bi = BudgetItem(
          itinerary_id=itinerary.id,
          category=bi_data.get("category", "other"),
          name=bi_data.get("name", ""),
          amount=bi_data.get("amount", 0),
          currency=bi_data.get("currency", "CNY"),
          day=bi_data.get("day"),
          note=bi_data.get("note"),
        )
        session.add(bi)

      await session.flush()
      return data

  async def _db_update(
    self, itinerary_id: str, data: dict[str, Any],
  ) -> Optional[dict[str, Any]]:
    from sqlalchemy import select
    from agent.db.models import Itinerary

    async with get_db_session() as session:
      stmt = select(Itinerary).where(
        Itinerary.id == uuid.UUID(itinerary_id),
      )
      result = await session.execute(stmt)
      row = result.scalar_one_or_none()
      if not row:
        return None

      for field in (
        "title", "destination", "travelers",
        "total_budget", "currency", "status",
      ):
        if field in data:
          setattr(row, field, data[field])

      if "start_date" in data:
        row.start_date = _parse_date(data["start_date"])
      if "end_date" in data:
        row.end_date = _parse_date(data["end_date"])

      await session.flush()
      return self._row_to_dict(row)

  async def _db_delete(self, itinerary_id: str) -> bool:
    from sqlalchemy import select
    from agent.db.models import Itinerary

    async with get_db_session() as session:
      stmt = select(Itinerary).where(
        Itinerary.id == uuid.UUID(itinerary_id),
      )
      result = await session.execute(stmt)
      row = result.scalar_one_or_none()
      if not row:
        return False
      await session.delete(row)
      return True

  @staticmethod
  def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
      "id": str(row.id),
      "session_id": row.session_id,
      "title": row.title,
      "destination": row.destination,
      "start_date": str(row.start_date) if row.start_date else None,
      "end_date": str(row.end_date) if row.end_date else None,
      "travelers": row.travelers,
      "total_budget": float(row.total_budget) if row.total_budget else None,
      "currency": row.currency,
      "status": row.status,
      "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _parse_date(val: Any) -> Optional[date]:
  """Parse date string to date object."""
  if val is None:
    return None
  if isinstance(val, date):
    return val
  try:
    return date.fromisoformat(str(val)[:10])
  except (ValueError, TypeError):
    return None
