# Long-term user profile memory – in-memory store with DB migration interface
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
  """User preference profile accumulated across sessions."""

  travel_style: List[str] = field(default_factory=list)
  # e.g. ["adventure", "relaxation", "culture", "foodie"]

  budget_preference: Optional[str] = None
  # e.g. "budget", "moderate", "luxury"

  accommodation_pref: Optional[str] = None
  # e.g. "hotel", "hostel", "minsu" (民宿), "resort"

  transport_pref: Optional[str] = None
  # e.g. "direct_flight", "economy", "time_priority", "train"

  dietary_restrictions: List[str] = field(default_factory=list)
  # e.g. ["vegetarian", "halal", "no_spicy"]

  visited_destinations: List[str] = field(default_factory=list)
  # e.g. ["日本", "泰国", "巴厘岛"]

  favorite_brands: List[str] = field(default_factory=list)
  # e.g. ["希尔顿", "全日空", "星巴克"]

  history_summary: str = ""
  # Free-text summary of past travel behaviour


# --- Preference signal patterns ---
# Each tuple: (regex_pattern, field_name, extracted_value_or_None)
# When value is None the matched group(1) is used.

_STYLE_SIGNALS: List[tuple] = [
  (r"(冒险|探险|刺激)", "travel_style", "adventure"),
  (r"(休闲|放松|度假|躺平)", "travel_style", "relaxation"),
  (r"(文艺|文化|历史|博物馆)", "travel_style", "culture"),
  (r"(美食|吃货|觅食|小吃)", "travel_style", "foodie"),
  (r"(亲子|带[娃孩]|儿童)", "travel_style", "family"),
  (r"(浪漫|蜜月|情侣)", "travel_style", "romantic"),
  (r"(购物|买买买|扫货)", "travel_style", "shopping"),
  (r"(摄影|拍照|网红打卡)", "travel_style", "photography"),
]

_BUDGET_SIGNALS: List[tuple] = [
  (r"(预算有限|省钱|穷游|便宜|经济)", "budget_preference", "budget"),
  (r"(舒适|中等|适中)", "budget_preference", "moderate"),
  (r"(奢华|豪华|高端|不差钱|五星)", "budget_preference", "luxury"),
]

_ACCOMMODATION_SIGNALS: List[tuple] = [
  (r"(民宿|airbnb|当地特色)", "accommodation_pref", "minsu"),
  (r"(酒店|宾馆|星级)", "accommodation_pref", "hotel"),
  (r"(青旅|背包|hostel)", "accommodation_pref", "hostel"),
  (r"(度假村|resort|别墅)", "accommodation_pref", "resort"),
]

_TRANSPORT_SIGNALS: List[tuple] = [
  (r"(直飞|不要转机|不中转)", "transport_pref", "direct_flight"),
  (r"(经济舱|便宜机票)", "transport_pref", "economy"),
  (r"(高铁|火车|铁路)", "transport_pref", "train"),
  (r"(自驾|租车|开车)", "transport_pref", "self_drive"),
]

_DIETARY_SIGNALS: List[tuple] = [
  (r"(素食|吃素|vegetarian)", "dietary_restrictions", "vegetarian"),
  (r"(清真|halal|穆斯林)", "dietary_restrictions", "halal"),
  (r"(不吃辣|不能吃辣)", "dietary_restrictions", "no_spicy"),
  (r"(海鲜过敏|不吃海鲜)", "dietary_restrictions", "no_seafood"),
  (r"(乳糖不耐|不喝牛奶)", "dietary_restrictions", "lactose_free"),
]

_BRAND_SIGNALS: List[tuple] = [
  (r"(希尔顿|Hilton)", "favorite_brands", "希尔顿"),
  (r"(万豪|Marriott)", "favorite_brands", "万豪"),
  (r"(全日空|ANA)", "favorite_brands", "全日空"),
  (r"(国航|Air China)", "favorite_brands", "国航"),
  (r"(南航|China Southern)", "favorite_brands", "南航"),
  (r"(东航|China Eastern)", "favorite_brands", "东航"),
  (r"(亚航|AirAsia)", "favorite_brands", "亚航"),
  (r"(香格里拉|Shangri-La)", "favorite_brands", "香格里拉"),
]

_DESTINATION_KEYWORDS: List[str] = [
  "日本", "东京", "大阪", "京都", "北海道", "冲绳", "奈良", "名古屋",
  "泰国", "曼谷", "清迈", "普吉岛", "芭提雅",
  "韩国", "首尔", "釜山", "济州岛",
  "新加坡", "马来西亚", "吉隆坡", "槟城",
  "越南", "河内", "胡志明", "岘港",
  "巴厘岛", "印尼",
  "北京", "上海", "广州", "深圳", "成都", "三亚", "丽江", "西安",
  "杭州", "重庆", "厦门", "桂林", "张家界", "西藏", "新疆",
  "美国", "纽约", "洛杉矶", "旧金山",
  "欧洲", "巴黎", "伦敦", "罗马", "巴塞罗那",
  "澳洲", "悉尼", "墨尔本",
]


class ProfileManager:
  """Manages user profiles in memory.

  Interface is designed for easy migration to a database backend.
  Swap the internal dict with a DB adapter to persist across restarts.
  """

  def __init__(self) -> None:
    self._profiles: Dict[str, UserProfile] = {}

  # --- public API ---

  def get_profile(self, user_id: str) -> UserProfile:
    """Return profile for user_id, creating a blank one if absent."""
    if user_id not in self._profiles:
      self._profiles[user_id] = UserProfile()
    return self._profiles[user_id]

  def update_profile(
    self,
    user_id: str,
    updates: Dict[str, Any],
  ) -> UserProfile:
    """Merge updates into the user profile.

    For list fields the new values are **appended** (deduplicated).
    For scalar fields the new value **overwrites**.
    """
    profile = self.get_profile(user_id)

    for key, value in updates.items():
      if value is None or not hasattr(profile, key):
        continue

      current = getattr(profile, key)
      if isinstance(current, list) and isinstance(value, list):
        # Append and deduplicate preserving order
        merged = list(current)
        for item in value:
          if item not in merged:
            merged.append(item)
        setattr(profile, key, merged)
      elif isinstance(current, list) and isinstance(value, str):
        if value not in current:
          current.append(value)
      else:
        setattr(profile, key, value)

    return profile

  def learn_from_session(
    self,
    user_id: str,
    session_messages: List[Dict[str, Any]],
    state_pool_context: Optional[str] = None,
  ) -> UserProfile:
    """Analyse session messages and auto-learn preference signals.

    Scans user messages for keyword patterns indicating travel style,
    budget preference, accommodation preference, etc. and updates the
    profile accordingly.
    """
    try:
      profile = self.get_profile(user_id)

      # Concatenate all user messages
      user_text = " ".join(
        msg.get("content", "")
        for msg in session_messages
        if msg.get("role") == "user"
      )

      if not user_text.strip():
        return profile

      updates: Dict[str, Any] = {}

      # Detect style signals
      for pattern, field_name, value in _STYLE_SIGNALS:
        if re.search(pattern, user_text):
          updates.setdefault(field_name, [])
          if isinstance(updates[field_name], list):
            if value not in updates[field_name]:
              updates[field_name].append(value)
          else:
            updates[field_name] = value

      # Detect budget signals (scalar – last match wins)
      for pattern, field_name, value in _BUDGET_SIGNALS:
        if re.search(pattern, user_text):
          updates[field_name] = value

      # Detect accommodation signals
      for pattern, field_name, value in _ACCOMMODATION_SIGNALS:
        if re.search(pattern, user_text):
          updates[field_name] = value

      # Detect transport signals
      for pattern, field_name, value in _TRANSPORT_SIGNALS:
        if re.search(pattern, user_text):
          updates[field_name] = value

      # Detect dietary restrictions
      for pattern, field_name, value in _DIETARY_SIGNALS:
        if re.search(pattern, user_text):
          updates.setdefault(field_name, [])
          if isinstance(updates[field_name], list):
            if value not in updates[field_name]:
              updates[field_name].append(value)

      # Detect brand preferences
      for pattern, field_name, value in _BRAND_SIGNALS:
        if re.search(pattern, user_text):
          updates.setdefault(field_name, [])
          if isinstance(updates[field_name], list):
            if value not in updates[field_name]:
              updates[field_name].append(value)

      # Detect visited destinations from state_pool context
      for dest in _DESTINATION_KEYWORDS:
        if dest in user_text:
          updates.setdefault("visited_destinations", [])
          if dest not in updates["visited_destinations"]:
            updates["visited_destinations"].append(dest)

      if updates:
        self.update_profile(user_id, updates)
        logger.info(
          "Learned preferences for user %s: %s",
          user_id, list(updates.keys()),
        )

      return profile

    except Exception as exc:
      logger.warning("learn_from_session failed: %s", exc)
      return self.get_profile(user_id)

  def get_personalization_context(self, user_id: str) -> str:
    """Generate a human-readable context string for Agent prompts.

    Returns an empty string when the profile is blank so callers
    can safely inject it without noise.
    """
    try:
      profile = self.get_profile(user_id)
      parts: List[str] = []

      if profile.travel_style:
        style_map = {
          "adventure": "冒险探索",
          "relaxation": "休闲度假",
          "culture": "文化历史",
          "foodie": "美食体验",
          "family": "亲子出游",
          "romantic": "浪漫之旅",
          "shopping": "购物之旅",
          "photography": "摄影打卡",
        }
        styles = [style_map.get(s, s) for s in profile.travel_style]
        parts.append(f"出行风格偏好：{', '.join(styles)}")

      if profile.budget_preference:
        budget_map = {
          "budget": "经济实惠型",
          "moderate": "舒适型",
          "luxury": "奢华型",
        }
        parts.append(
          f"预算偏好：{budget_map.get(profile.budget_preference, profile.budget_preference)}"
        )

      if profile.accommodation_pref:
        acc_map = {
          "minsu": "民宿/特色住宿",
          "hotel": "酒店/宾馆",
          "hostel": "青年旅舍",
          "resort": "度假村",
        }
        parts.append(
          f"住宿偏好：{acc_map.get(profile.accommodation_pref, profile.accommodation_pref)}"
        )

      if profile.transport_pref:
        tp_map = {
          "direct_flight": "直飞优先",
          "economy": "经济舱优先",
          "train": "火车/高铁",
          "self_drive": "自驾游",
        }
        parts.append(
          f"交通偏好：{tp_map.get(profile.transport_pref, profile.transport_pref)}"
        )

      if profile.dietary_restrictions:
        diet_map = {
          "vegetarian": "素食",
          "halal": "清真",
          "no_spicy": "不吃辣",
          "no_seafood": "不吃海鲜",
          "lactose_free": "乳糖不耐受",
        }
        diets = [diet_map.get(d, d) for d in profile.dietary_restrictions]
        parts.append(f"饮食限制：{', '.join(diets)}")

      if profile.visited_destinations:
        parts.append(f"去过的地方：{', '.join(profile.visited_destinations)}")

      if profile.favorite_brands:
        parts.append(f"偏好品牌：{', '.join(profile.favorite_brands)}")

      if profile.history_summary:
        parts.append(f"历史备注：{profile.history_summary}")

      return "\n".join(parts) if parts else ""

    except Exception as exc:
      logger.warning("get_personalization_context failed: %s", exc)
      return ""

  def delete_profile(self, user_id: str) -> None:
    """Remove a user profile entirely."""
    self._profiles.pop(user_id, None)


# Singleton instance
profile_manager = ProfileManager()
