# User profile repository
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from agent.db.engine import get_db_session, is_db_available
from agent.memory.profile import profile_manager

logger = logging.getLogger(__name__)


class ProfileRepository:
  """User profile CRUD – DB primary, in-memory ProfileManager as fallback."""

  async def get_profile(self, user_id: str) -> dict[str, Any]:
    """Get user profile with preferences."""
    try:
      if is_db_available():
        result = await self._db_get_profile(user_id)
        if result:
          return result
    except Exception as exc:
      logger.warning("DB get_profile failed: %s", exc)

    # Fallback to in-memory ProfileManager
    profile = await profile_manager.get_profile(user_id)
    return {
      "user_id": user_id,
      "name": "",
      "email": None,
      "member_level": "standard",
      "total_trips": 0,
      "total_destinations": 0,
      "preferences": {
        "travel_style": profile.travel_style,
        "budget_preference": profile.budget_preference,
        "accommodation_pref": profile.accommodation_pref,
        "transport_pref": profile.transport_pref,
        "dietary_restrictions": profile.dietary_restrictions,
      },
      "visited_destinations": profile.visited_destinations,
      "favorite_brands": profile.favorite_brands,
    }

  async def update_preferences(
    self, user_id: str, prefs: dict[str, Any],
  ) -> dict[str, Any]:
    """Update user preferences."""
    try:
      if is_db_available():
        result = await self._db_update_prefs(user_id, prefs)
        if result:
          return result
    except Exception as exc:
      logger.warning("DB update_preferences failed: %s", exc)

    # Fallback to in-memory
    updates: dict[str, Any] = {}
    if "travel_style" in prefs:
      updates["travel_style"] = prefs["travel_style"]
    if "budget_preference" in prefs:
      updates["budget_preference"] = prefs["budget_preference"]
    if "accommodation_pref" in prefs:
      updates["accommodation_pref"] = prefs["accommodation_pref"]
    if "transport_pref" in prefs:
      updates["transport_pref"] = prefs["transport_pref"]
    if "dietary_restrictions" in prefs:
      updates["dietary_restrictions"] = prefs["dietary_restrictions"]
    if updates:
      await profile_manager.update_profile(user_id, updates)

    return await self.get_profile(user_id)

  # ------------------------------------------------------------------ #
  # DB implementations
  # ------------------------------------------------------------------ #

  async def _db_get_profile(
    self, user_id: str,
  ) -> Optional[dict[str, Any]]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from agent.db.models import User

    async with get_db_session() as session:
      stmt = (
        select(User)
        .options(selectinload(User.profile))
        .where(User.user_id == user_id)
      )
      result = await session.execute(stmt)
      user = result.scalar_one_or_none()
      if not user:
        return None

      profile = user.profile
      return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "member_level": user.member_level,
        "total_trips": user.total_trips,
        "total_destinations": user.total_destinations,
        "join_date": user.join_date.isoformat() if user.join_date else None,
        "preferences": {
          "travel_style": profile.travel_style if profile else [],
          "budget_preference": profile.budget_preference if profile else None,
          "accommodation_pref": profile.accommodation_pref if profile else None,
          "transport_pref": profile.transport_pref if profile else None,
          "dietary_restrictions": profile.dietary_restrictions if profile else [],
        },
        "visited_destinations": profile.visited_destinations if profile else [],
        "favorite_brands": profile.favorite_brands if profile else [],
      }

  async def _db_update_prefs(
    self, user_id: str, prefs: dict[str, Any],
  ) -> Optional[dict[str, Any]]:
    from sqlalchemy import select
    from agent.db.models import User, UserProfile

    async with get_db_session() as session:
      stmt = select(User).where(User.user_id == user_id)
      result = await session.execute(stmt)
      user = result.scalar_one_or_none()

      if not user:
        # Auto-create user
        user = User(user_id=user_id, name=prefs.get("name", ""))
        session.add(user)
        await session.flush()

      # Get or create profile
      stmt2 = select(UserProfile).where(UserProfile.user_id == user.id)
      result2 = await session.execute(stmt2)
      profile = result2.scalar_one_or_none()

      if not profile:
        profile = UserProfile(user_id=user.id)
        session.add(profile)

      # Update fields
      for field in (
        "travel_style", "budget_preference", "accommodation_pref",
        "transport_pref", "dietary_restrictions",
        "visited_destinations", "favorite_brands",
      ):
        if field in prefs:
          setattr(profile, field, prefs[field])

      await session.flush()

    return await self._db_get_profile(user_id)
