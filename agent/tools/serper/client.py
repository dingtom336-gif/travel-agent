# Async HTTP client for Google Serper API
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://google.serper.dev"
_TIMEOUT = 10.0


def _get_api_key() -> str | None:
  settings = get_settings()
  key = getattr(settings, "SERPER_API_KEY", "") or ""
  return key if key else None


async def search(
  query: str,
  gl: str = "cn",
  hl: str = "zh-cn",
  num: int = 10,
) -> Dict[str, Any]:
  """Google search via Serper API.

  Args:
    query: Search query string
    gl: Country code (default "cn")
    hl: Language code (default "zh-cn")
    num: Number of results

  Returns:
    Raw Serper response dict
  """
  api_key = _get_api_key()
  if not api_key:
    return {"error": "SERPER_API_KEY not configured"}

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.post(
        f"{_BASE_URL}/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": gl, "hl": hl, "num": num},
      )
      resp.raise_for_status()
      return resp.json()
  except Exception as exc:
    logger.warning("Serper search failed: %s", exc)
    return {"error": str(exc)}


async def search_places(
  query: str,
  gl: str = "cn",
  hl: str = "zh-cn",
) -> Dict[str, Any]:
  """Google Places search via Serper API."""
  api_key = _get_api_key()
  if not api_key:
    return {"error": "SERPER_API_KEY not configured"}

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.post(
        f"{_BASE_URL}/places",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": gl, "hl": hl},
      )
      resp.raise_for_status()
      return resp.json()
  except Exception as exc:
    logger.warning("Serper places failed: %s", exc)
    return {"error": str(exc)}


async def search_news(
  query: str,
  gl: str = "cn",
  hl: str = "zh-cn",
  num: int = 5,
) -> Dict[str, Any]:
  """Google News search via Serper API."""
  api_key = _get_api_key()
  if not api_key:
    return {"error": "SERPER_API_KEY not configured"}

  try:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
      resp = await client.post(
        f"{_BASE_URL}/news",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": gl, "hl": hl, "num": num},
      )
      resp.raise_for_status()
      return resp.json()
  except Exception as exc:
    logger.warning("Serper news failed: %s", exc)
    return {"error": str(exc)}
