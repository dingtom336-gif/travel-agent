# FlyAI CLI wrapper - calls flyai.cjs via subprocess for real travel data
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.config.settings import get_settings

logger = logging.getLogger(__name__)

# Resolve flyai.cjs path relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_FLYAI_SCRIPT = _PROJECT_ROOT / ".agents" / "skills" / "flyai" / "scripts" / "flyai.cjs"

_TIMEOUT_SECONDS = 15


async def _run_flyai(args: List[str]) -> Optional[Dict[str, Any]]:
  """Run flyai.cjs with given args, return parsed JSON or None on failure."""
  if not _FLYAI_SCRIPT.exists():
    logger.warning("flyai.cjs not found at %s", _FLYAI_SCRIPT)
    return None

  settings = get_settings()
  app_key = settings.FLYAI_APP_KEY
  if not app_key:
    logger.debug("FLYAI_APP_KEY not set, skipping flyai search")
    return None

  env = os.environ.copy()
  env["FLYAI_APP_KEY"] = app_key
  if settings.FLYAI_PROXY:
    env["HTTPS_PROXY"] = settings.FLYAI_PROXY
    env["HTTP_PROXY"] = settings.FLYAI_PROXY

  cmd = ["node", str(_FLYAI_SCRIPT)] + args
  try:
    proc = await asyncio.create_subprocess_exec(
      *cmd,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
      env=env,
    )
    stdout, stderr = await asyncio.wait_for(
      proc.communicate(), timeout=_TIMEOUT_SECONDS
    )

    if proc.returncode != 0:
      logger.debug("flyai exited %d: %s", proc.returncode, stderr.decode()[:200])
      return None

    data = json.loads(stdout.decode())
    if data.get("status") != 0:
      logger.debug("flyai API error: %s", data.get("message", "unknown"))
      return None

    return data
  except asyncio.TimeoutError:
    logger.debug("flyai timed out after %ds", _TIMEOUT_SECONDS)
    return None
  except (json.JSONDecodeError, OSError) as exc:
    logger.debug("flyai call failed: %s", exc)
    return None


async def search_flights_flyai(
  origin: str,
  destination: str,
  dep_date: str,
  sort_type: int = 3,
) -> Optional[List[Dict[str, Any]]]:
  """Search flights via FlyAI. Returns raw itemList or None."""
  args = [
    "search-flight",
    "--origin", origin,
    "--destination", destination,
    "--dep-date", dep_date,
    "--sort-type", str(sort_type),
  ]
  data = await _run_flyai(args)
  if data:
    return data.get("data", {}).get("itemList", [])
  return None


async def search_hotels_flyai(
  dest_name: str,
  check_in: str,
  check_out: str,
  poi_name: Optional[str] = None,
  hotel_stars: Optional[str] = None,
  max_price: Optional[int] = None,
  sort: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
  """Search hotels via FlyAI. Returns raw itemList or None."""
  args = ["search-hotels", "--dest-name", dest_name]
  if check_in:
    args += ["--check-in-date", check_in]
  if check_out:
    args += ["--check-out-date", check_out]
  if poi_name:
    args += ["--poi-name", poi_name]
  if hotel_stars:
    args += ["--hotel-stars", hotel_stars]
  if max_price:
    args += ["--max-price", str(max_price)]
  if sort:
    args += ["--sort", sort]

  data = await _run_flyai(args)
  if data:
    return data.get("data", {}).get("itemList", [])
  return None


async def search_pois_flyai(
  city_name: str,
  keyword: Optional[str] = None,
  category: Optional[str] = None,
  poi_level: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
  """Search POIs/attractions via FlyAI. Returns raw itemList or None."""
  args = ["search-poi", "--city-name", city_name]
  if keyword:
    args += ["--keyword", keyword]
  if category:
    args += ["--category", category]
  if poi_level:
    args += ["--poi-level", str(poi_level)]

  data = await _run_flyai(args)
  if data:
    return data.get("data", {}).get("itemList", [])
  return None
