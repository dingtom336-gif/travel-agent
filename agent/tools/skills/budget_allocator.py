# Budget allocator skill - smart budget distribution for trips
# Allocates total budget across categories based on trip parameters
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional


# Default allocation ratios by travel style
_STYLE_RATIOS: Dict[str, Dict[str, float]] = {
  "balanced": {
    "transport": 0.25,
    "accommodation": 0.30,
    "food": 0.20,
    "attractions": 0.15,
    "shopping": 0.05,
    "miscellaneous": 0.05,
  },
  "budget": {
    "transport": 0.30,
    "accommodation": 0.20,
    "food": 0.20,
    "attractions": 0.15,
    "shopping": 0.05,
    "miscellaneous": 0.10,
  },
  "comfort": {
    "transport": 0.25,
    "accommodation": 0.35,
    "food": 0.20,
    "attractions": 0.10,
    "shopping": 0.05,
    "miscellaneous": 0.05,
  },
  "luxury": {
    "transport": 0.20,
    "accommodation": 0.40,
    "food": 0.20,
    "attractions": 0.10,
    "shopping": 0.05,
    "miscellaneous": 0.05,
  },
  "adventure": {
    "transport": 0.20,
    "accommodation": 0.20,
    "food": 0.15,
    "attractions": 0.30,
    "shopping": 0.05,
    "miscellaneous": 0.10,
  },
  "shopping_focused": {
    "transport": 0.25,
    "accommodation": 0.25,
    "food": 0.15,
    "attractions": 0.05,
    "shopping": 0.25,
    "miscellaneous": 0.05,
  },
}

# Category display names
_CATEGORY_DISPLAY = {
  "transport": {"zh": "交通", "icon": "plane"},
  "accommodation": {"zh": "住宿", "icon": "hotel"},
  "food": {"zh": "餐饮", "icon": "utensils"},
  "attractions": {"zh": "门票/活动", "icon": "ticket"},
  "shopping": {"zh": "购物", "icon": "shopping-bag"},
  "miscellaneous": {"zh": "其他", "icon": "ellipsis"},
}

# Daily spending estimates by destination tier (CNY)
_DAILY_ESTIMATES: Dict[str, Dict[str, Dict[str, int]]] = {
  "tier1_international": {
    # e.g. Tokyo, Paris, London, Singapore
    "budget": {"food": 200, "transport_local": 80, "attractions": 100},
    "comfort": {"food": 400, "transport_local": 150, "attractions": 200},
    "luxury": {"food": 800, "transport_local": 300, "attractions": 350},
  },
  "tier2_international": {
    # e.g. Bangkok, Bali, Hanoi
    "budget": {"food": 100, "transport_local": 40, "attractions": 50},
    "comfort": {"food": 200, "transport_local": 80, "attractions": 100},
    "luxury": {"food": 500, "transport_local": 200, "attractions": 200},
  },
  "tier1_domestic": {
    # e.g. Beijing, Shanghai, Guangzhou
    "budget": {"food": 100, "transport_local": 50, "attractions": 60},
    "comfort": {"food": 250, "transport_local": 100, "attractions": 120},
    "luxury": {"food": 500, "transport_local": 200, "attractions": 200},
  },
  "tier2_domestic": {
    # e.g. Chengdu, Hangzhou, Xi'an
    "budget": {"food": 80, "transport_local": 30, "attractions": 40},
    "comfort": {"food": 180, "transport_local": 60, "attractions": 80},
    "luxury": {"food": 400, "transport_local": 150, "attractions": 150},
  },
}


def _classify_destination(destination: Optional[str]) -> str:
  """Classify destination into a spending tier."""
  if not destination:
    return "tier1_domestic"

  tier1_intl = {"东京", "大阪", "京都", "巴黎", "伦敦", "纽约", "新加坡", "悉尼", "首尔"}
  tier2_intl = {"曼谷", "清迈", "芭提雅", "河内", "胡志明", "巴厘岛", "吉隆坡", "马尼拉"}
  tier1_dom = {"北京", "上海", "广州", "深圳", "杭州", "南京", "苏州"}

  if destination in tier1_intl:
    return "tier1_international"
  elif destination in tier2_intl:
    return "tier2_international"
  elif destination in tier1_dom:
    return "tier1_domestic"
  else:
    return "tier2_domestic"


async def allocate_budget(
  total_budget: float,
  trip_days: int,
  preferences: Optional[str] = "balanced",
  destination: Optional[str] = None,
  travelers: int = 1,
) -> Dict[str, Any]:
  """Allocate travel budget across categories.

  Args:
    total_budget: Total budget in CNY
    trip_days: Number of trip days
    preferences: Travel style: "balanced"/"budget"/"comfort"/"luxury"/"adventure"/"shopping_focused"
    destination: Destination city (for cost estimation)
    travelers: Number of travelers

  Returns:
    Dict with budget allocation, daily breakdown, and tips
  """
  try:
    await asyncio.sleep(0.05)

    style = preferences if preferences in _STYLE_RATIOS else "balanced"
    ratios = _STYLE_RATIOS[style]
    dest_tier = _classify_destination(destination)

    # Map style to spending level for daily estimates
    if style in ("luxury",):
      spend_level = "luxury"
    elif style in ("budget",):
      spend_level = "budget"
    else:
      spend_level = "comfort"

    daily_ref = _DAILY_ESTIMATES.get(dest_tier, _DAILY_ESTIMATES["tier1_domestic"]).get(
      spend_level, _DAILY_ESTIMATES["tier1_domestic"]["comfort"]
    )

    # Allocate budget by category
    allocations: List[Dict[str, Any]] = []
    per_person_budget = total_budget / max(travelers, 1)
    budget_remaining = total_budget

    for category, ratio in ratios.items():
      amount = round(total_budget * ratio, 0)
      cat_info = _CATEGORY_DISPLAY.get(category, {"zh": category, "icon": "circle"})
      per_person = round(amount / max(travelers, 1), 0)
      per_day = round(amount / max(trip_days, 1), 0)
      per_person_per_day = round(per_person / max(trip_days, 1), 0)

      allocations.append({
        "category": category,
        "category_display": cat_info["zh"],
        "icon": cat_info["icon"],
        "amount": int(amount),
        "percentage": round(ratio * 100, 1),
        "per_person": int(per_person),
        "per_day": int(per_day),
        "per_person_per_day": int(per_person_per_day),
        "currency": "CNY",
      })

    # Daily breakdown estimate
    daily_budget = round(total_budget / max(trip_days, 1), 0)
    daily_per_person = round(daily_budget / max(travelers, 1), 0)

    # Budget tips
    tips = _generate_tips(total_budget, trip_days, travelers, style, dest_tier)

    # Feasibility check
    estimated_min = _estimate_minimum_cost(trip_days, travelers, dest_tier)
    is_feasible = total_budget >= estimated_min
    feasibility_note = (
      "预算充裕，可以享受舒适的旅行体验" if total_budget > estimated_min * 1.5
      else "预算合理，注意控制消费即可" if is_feasible
      else f"预算偏紧，建议至少准备¥{int(estimated_min)}或缩短行程天数"
    )

    return {
      "success": True,
      "query": {
        "total_budget": total_budget,
        "trip_days": trip_days,
        "preferences": style,
        "destination": destination,
        "travelers": travelers,
      },
      "allocations": allocations,
      "summary": {
        "total_budget": int(total_budget),
        "daily_budget": int(daily_budget),
        "daily_per_person": int(daily_per_person),
        "per_person_budget": int(per_person_budget),
        "currency": "CNY",
      },
      "feasibility": {
        "is_feasible": is_feasible,
        "estimated_minimum": int(estimated_min),
        "note": feasibility_note,
      },
      "tips": tips,
    }
  except Exception as exc:
    return {
      "success": False,
      "error": str(exc),
      "allocations": [],
    }


def _estimate_minimum_cost(days: int, travelers: int, tier: str) -> float:
  """Estimate minimum viable budget for a trip."""
  daily_min = {
    "tier1_international": 600,
    "tier2_international": 300,
    "tier1_domestic": 400,
    "tier2_domestic": 250,
  }
  base_daily = daily_min.get(tier, 400)
  # Transport base cost (round trip)
  transport_base = {
    "tier1_international": 3000,
    "tier2_international": 2000,
    "tier1_domestic": 800,
    "tier2_domestic": 500,
  }
  transport = transport_base.get(tier, 1000) * travelers
  return transport + base_daily * days * travelers


def _generate_tips(
  budget: float,
  days: int,
  travelers: int,
  style: str,
  tier: str,
) -> List[str]:
  """Generate budget-specific tips."""
  tips = []

  if style == "budget":
    tips.extend([
      "选择经济型连锁酒店或青旅，可节省30-50%住宿费用",
      "提前2-4周购买机票通常能拿到较低价格",
      "午餐选择当地便餐/便利店，晚餐再安排正式餐厅",
      "利用城市一日通票节省市内交通费用",
    ])
  elif style == "luxury":
    tips.extend([
      "提前预订高端酒店行政楼层，享受行政酒廊和增值服务",
      "考虑商务舱/头等舱的里程积累计划",
      "预订米其林餐厅建议提前2周以上",
    ])
  else:
    tips.extend([
      "合理安排行程密度，避免在门票和交通上重复花费",
      "关注旅游套票和组合优惠",
      "准备一定比例的应急资金（建议10%）",
    ])

  if travelers > 2:
    tips.append(f"多人出行可考虑包车或家庭套票，{travelers}人分摊更划算")

  if "international" in tier:
    tips.append("建议提前兑换少量当地货币，大额消费用信用卡更优惠")

  return tips
