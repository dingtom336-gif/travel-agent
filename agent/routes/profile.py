# User profile API routes
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.db.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["profile"])

_repo = ProfileRepository()


# --- Request models ---

class ProfileUpdateRequest(BaseModel):
  """Request body for updating user preferences."""
  name: Optional[str] = None
  travel_style: Optional[List[str]] = None
  budget_preference: Optional[str] = None
  accommodation_pref: Optional[str] = None
  transport_pref: Optional[str] = None
  dietary_restrictions: Optional[List[str]] = None
  visited_destinations: Optional[List[str]] = None
  favorite_brands: Optional[List[str]] = None


# --- Endpoints ---

@router.get("/profile")
async def get_profile(user_id: str = "default"):
  """Get user profile with preferences."""
  try:
    result = await _repo.get_profile(user_id)
    return result
  except Exception as exc:
    logger.exception("Get profile error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@router.put("/profile")
async def update_profile(
  request: ProfileUpdateRequest,
  user_id: str = "default",
):
  """Update user preferences."""
  try:
    data = request.model_dump(exclude_none=True)
    if not data:
      return JSONResponse(
        status_code=400, content={"error": "No fields to update"},
      )
    result = await _repo.update_preferences(user_id, data)
    return result
  except Exception as exc:
    logger.exception("Update profile error")
    return JSONResponse(status_code=500, content={"error": str(exc)})
