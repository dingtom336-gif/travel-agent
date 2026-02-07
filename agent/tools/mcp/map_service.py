# Map / route planning MCP tool - mock implementation
# Provides distance calculation and route optimization
from __future__ import annotations

import asyncio
import math
import random
from typing import Any, Dict, List, Optional


# Known distances between cities (km) and typical travel times (hours)
_CITY_DISTANCES: Dict[str, Dict[str, Any]] = {
  "北京-上海": {"distance_km": 1213, "flight_h": 2.5, "train_h": 4.5, "drive_h": 12},
  "北京-广州": {"distance_km": 1889, "flight_h": 3.5, "train_h": 8, "drive_h": 20},
  "北京-成都": {"distance_km": 1516, "flight_h": 3.0, "train_h": 7.5, "drive_h": 18},
  "上海-广州": {"distance_km": 1213, "flight_h": 2.5, "train_h": 6.5, "drive_h": 14},
  "上海-杭州": {"distance_km": 175, "flight_h": None, "train_h": 1.0, "drive_h": 2.5},
  "东京-大阪": {"distance_km": 515, "flight_h": 1.2, "train_h": 2.5, "drive_h": 5.5},
  "东京-京都": {"distance_km": 476, "flight_h": 1.2, "train_h": 2.25, "drive_h": 5.0},
  "大阪-京都": {"distance_km": 47, "flight_h": None, "train_h": 0.5, "drive_h": 1.0},
  "大阪-奈良": {"distance_km": 35, "flight_h": None, "train_h": 0.5, "drive_h": 0.75},
  "曼谷-清迈": {"distance_km": 696, "flight_h": 1.2, "train_h": 12, "drive_h": 8},
  "曼谷-芭提雅": {"distance_km": 147, "flight_h": None, "train_h": 3, "drive_h": 2},
  "首尔-釜山": {"distance_km": 325, "flight_h": 1.0, "train_h": 2.5, "drive_h": 4},
}

# Transport mode configs
_TRANSPORT_MODES = {
  "walking": {"speed_kmh": 4.5, "cost_per_km": 0},
  "taxi": {"speed_kmh": 30, "cost_per_km": 3.5},
  "bus": {"speed_kmh": 25, "cost_per_km": 0.5},
  "metro": {"speed_kmh": 35, "cost_per_km": 0.3},
  "driving": {"speed_kmh": 60, "cost_per_km": 1.2},
  "train": {"speed_kmh": 250, "cost_per_km": 0.5},
  "flight": {"speed_kmh": 800, "cost_per_km": 0.8},
}


def _lookup_distance(origin: str, destination: str) -> Optional[Dict[str, Any]]:
  """Lookup known distance between two cities."""
  key1 = f"{origin}-{destination}"
  key2 = f"{destination}-{origin}"
  return _CITY_DISTANCES.get(key1) or _CITY_DISTANCES.get(key2)


def _estimate_distance(origin: str, destination: str) -> float:
  """Estimate distance when not in lookup table (km)."""
  # Use a reasonable random distance based on whether they sound
  # like cities within the same country or international
  return round(random.uniform(10, 500), 1)


async def get_distance(
  origin: str,
  destination: str,
  mode: str = "driving",
) -> Dict[str, Any]:
  """Calculate distance and travel time between two locations.

  Args:
    origin: Starting location name
    destination: Ending location name
    mode: Transport mode: walking / taxi / bus / metro / driving / train / flight

  Returns:
    Dict with distance, estimated time, and cost
  """
  try:
    await asyncio.sleep(random.uniform(0.05, 0.15))

    known = _lookup_distance(origin, destination)

    if known:
      distance_km = known["distance_km"]
      # Use pre-calculated travel time if available
      mode_time_key = f"{mode}_h"
      if mode_time_key in known and known[mode_time_key] is not None:
        duration_h = known[mode_time_key]
      else:
        mode_config = _TRANSPORT_MODES.get(mode, _TRANSPORT_MODES["driving"])
        duration_h = round(distance_km / mode_config["speed_kmh"], 1)
    else:
      distance_km = _estimate_distance(origin, destination)
      mode_config = _TRANSPORT_MODES.get(mode, _TRANSPORT_MODES["driving"])
      duration_h = round(distance_km / mode_config["speed_kmh"], 1)

    # Add some randomness for realism
    duration_h = round(duration_h * random.uniform(0.9, 1.1), 1)

    mode_config = _TRANSPORT_MODES.get(mode, _TRANSPORT_MODES["driving"])
    estimated_cost = round(distance_km * mode_config["cost_per_km"], 0)

    # Format duration display
    hours = int(duration_h)
    minutes = int((duration_h - hours) * 60)
    if hours > 0:
      duration_display = f"{hours}h{minutes}m"
    else:
      duration_display = f"{minutes}min"

    return {
      "success": True,
      "origin": origin,
      "destination": destination,
      "mode": mode,
      "distance_km": distance_km,
      "duration_hours": duration_h,
      "duration_display": duration_display,
      "estimated_cost": int(estimated_cost),
      "currency": "CNY",
      "route_summary": f"从{origin}到{destination}，{mode}约{duration_display}",
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "origin": origin,
      "destination": destination,
    }


async def plan_route(
  waypoints: List[str],
  mode: str = "driving",
  optimize: bool = True,
) -> Dict[str, Any]:
  """Plan an optimal route through multiple waypoints.

  Args:
    waypoints: List of location names to visit (in order or to be optimized)
    mode: Transport mode for the route
    optimize: Whether to optimize the order of waypoints (default True)

  Returns:
    Dict with optimized route, total distance, time, and per-segment details
  """
  try:
    await asyncio.sleep(random.uniform(0.1, 0.3))

    if len(waypoints) < 2:
      return {
        "success": False,
        "error": "At least 2 waypoints are required",
        "waypoints": waypoints,
      }

    # If optimizing, try a simple nearest-neighbor heuristic
    if optimize and len(waypoints) > 2:
      waypoints = _optimize_order(waypoints)

    segments = []
    total_distance = 0
    total_duration = 0
    total_cost = 0

    for i in range(len(waypoints) - 1):
      segment_result = await get_distance(waypoints[i], waypoints[i + 1], mode)
      if segment_result.get("success"):
        segment = {
          "from": waypoints[i],
          "to": waypoints[i + 1],
          "distance_km": segment_result["distance_km"],
          "duration_hours": segment_result["duration_hours"],
          "duration_display": segment_result["duration_display"],
          "estimated_cost": segment_result["estimated_cost"],
        }
        total_distance += segment_result["distance_km"]
        total_duration += segment_result["duration_hours"]
        total_cost += segment_result["estimated_cost"]
      else:
        segment = {
          "from": waypoints[i],
          "to": waypoints[i + 1],
          "error": "Failed to calculate distance",
        }
      segments.append(segment)

    # Format total duration
    t_hours = int(total_duration)
    t_minutes = int((total_duration - t_hours) * 60)
    total_display = f"{t_hours}h{t_minutes}m" if t_hours > 0 else f"{t_minutes}min"

    return {
      "success": True,
      "waypoints": waypoints,
      "mode": mode,
      "optimized": optimize,
      "segments": segments,
      "total_distance_km": round(total_distance, 1),
      "total_duration_hours": round(total_duration, 1),
      "total_duration_display": total_display,
      "total_estimated_cost": int(total_cost),
      "currency": "CNY",
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "waypoints": waypoints,
    }


def _optimize_order(waypoints: List[str]) -> List[str]:
  """Simple nearest-neighbor optimization for waypoint ordering.

  Keeps first and last waypoints fixed (start and end),
  optimizes the middle waypoints.
  """
  if len(waypoints) <= 3:
    return waypoints

  start = waypoints[0]
  end = waypoints[-1]
  middle = list(waypoints[1:-1])

  # Shuffle middle points for "optimization" (mock)
  # In real implementation, this would use actual distances
  random.shuffle(middle)

  return [start] + middle + [end]
