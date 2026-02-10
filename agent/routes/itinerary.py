# Itinerary CRUD API routes
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent.db.repositories.itinerary_repo import ItineraryRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["itineraries"])

_repo = ItineraryRepository()


# --- Request models ---

class ItineraryCreateRequest(BaseModel):
  """Request body for creating an itinerary."""
  title: str = Field(..., min_length=1, max_length=200)
  destination: str = Field(..., min_length=1, max_length=200)
  start_date: Optional[str] = None
  end_date: Optional[str] = None
  travelers: int = Field(default=1, ge=1)
  total_budget: Optional[float] = None
  currency: str = "CNY"
  session_id: Optional[str] = None
  days: Optional[List[Dict[str, Any]]] = None
  budget_items: Optional[List[Dict[str, Any]]] = None


class ItineraryUpdateRequest(BaseModel):
  """Request body for updating an itinerary."""
  title: Optional[str] = None
  destination: Optional[str] = None
  start_date: Optional[str] = None
  end_date: Optional[str] = None
  travelers: Optional[int] = None
  total_budget: Optional[float] = None
  currency: Optional[str] = None
  status: Optional[str] = None
  days: Optional[List[Dict[str, Any]]] = None
  budget_items: Optional[List[Dict[str, Any]]] = None


# --- Endpoints ---

@router.get("/itineraries")
async def list_itineraries(user_id: str = "default"):
  """List itineraries for a user."""
  try:
    items = await _repo.list_by_user(user_id)
    return {"itineraries": items, "total": len(items)}
  except Exception as exc:
    logger.exception("List itineraries error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@router.get("/itineraries/{itinerary_id}")
async def get_itinerary(itinerary_id: str):
  """Get a single itinerary with full details."""
  try:
    item = await _repo.get_by_id(itinerary_id)
    if not item:
      return JSONResponse(
        status_code=404,
        content={"error": f"Itinerary '{itinerary_id}' not found"},
      )
    return item
  except Exception as exc:
    logger.exception("Get itinerary error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@router.post("/itineraries")
async def create_itinerary(request: ItineraryCreateRequest):
  """Create a new itinerary."""
  try:
    data = request.model_dump(exclude_none=True)
    result = await _repo.create(data)
    return result
  except Exception as exc:
    logger.exception("Create itinerary error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@router.put("/itineraries/{itinerary_id}")
async def update_itinerary(itinerary_id: str, request: ItineraryUpdateRequest):
  """Update an existing itinerary."""
  try:
    data = request.model_dump(exclude_none=True)
    if not data:
      return JSONResponse(
        status_code=400, content={"error": "No fields to update"},
      )
    result = await _repo.update(itinerary_id, data)
    if not result:
      return JSONResponse(
        status_code=404,
        content={"error": f"Itinerary '{itinerary_id}' not found"},
      )
    return result
  except Exception as exc:
    logger.exception("Update itinerary error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@router.delete("/itineraries/{itinerary_id}")
async def delete_itinerary(itinerary_id: str):
  """Delete an itinerary."""
  try:
    deleted = await _repo.delete(itinerary_id)
    if not deleted:
      return JSONResponse(
        status_code=404,
        content={"error": f"Itinerary '{itinerary_id}' not found"},
      )
    return {"deleted": True, "id": itinerary_id}
  except Exception as exc:
    logger.exception("Delete itinerary error")
    return JSONResponse(status_code=500, content={"error": str(exc)})
