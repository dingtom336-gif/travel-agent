# Search handler – direct tool query for flights/hotels/POIs
# Bypasses mega-LLM pipeline, calls tools directly and formats results
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent.config.settings import get_settings
from agent.llm import llm_chat_stream
from agent.memory.session import session_memory
from agent.memory.state_pool import state_pool
from agent.models import SSEEventType, SSEMessage

logger = logging.getLogger(__name__)

_SEARCH_FALLBACK_SYSTEM = """\
你是 TravelMind，一位专业的旅行助手。
用户正在查询旅行信息，但提供的信息不够完整，无法直接搜索。

请根据用户的原始消息：
1. 尽可能回答用户的问题（如果你能从消息中推断出答案）。
2. 如果确实需要更多信息才能搜索，用友好自然的语气追问，给出具体示例帮助用户补充。
3. 不要使用固定模板，根据具体场景灵活回应。
4. 一次最多追问 1-2 个关键信息，不要变成审讯。
"""


def _detect_search_type(message: str) -> str:
  """Detect what the user wants to search: flights, hotels, or pois."""
  msg = message.lower()
  if any(k in msg for k in ("航班", "机票", "飞", "飞机")):
    return "flights"
  if any(k in msg for k in ("酒店", "住宿", "宾馆", "民宿", "住哪")):
    return "hotels"
  if any(k in msg for k in ("景点", "门票", "好玩", "旅游", "玩什么", "去哪玩")):
    return "pois"
  return "flights"  # default


def _extract_date(message: str) -> Optional[str]:
  """Extract date from message, return YYYY-MM-DD or None."""
  # Explicit date: 4月1号, 4.1, 04-01
  m = re.search(r"(\d{1,2})[月.](\d{1,2})[日号]?", message)
  if m:
    month, day = int(m.group(1)), int(m.group(2))
    year = datetime.now().year
    try:
      d = datetime(year, month, day)
      if d < datetime.now():
        d = d.replace(year=year + 1)
      return d.strftime("%Y-%m-%d")
    except ValueError:
      pass
  # "明天", "后天"
  if "明天" in message:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
  if "后天" in message:
    return (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
  return None


def _format_flights(results: List[Dict[str, Any]], origin: str, dest: str) -> str:
  """Format flight results as markdown."""
  if not results:
    return f"未找到 {origin}→{dest} 的航班信息。"
  lines = [f"### {origin} → {dest} 航班查询结果\n"]
  lines.append("| 航班 | 航司 | 出发 | 到达 | 时长 | 价格 |")
  lines.append("|------|------|------|------|------|------|")
  for f in results:
    dep_airport = f.get("departure_airport", "")
    arr_airport = f.get("arrival_airport", "")
    dep_info = f.get("departure_time", "")
    if dep_airport:
      dep_info = f'{dep_info} {dep_airport}'
    arr_info = f.get("arrival_time", "")
    if arr_airport:
      arr_info = f'{arr_info} {arr_airport}'
    price_str = f'¥{f["price"]}' if f.get("price") else "-"
    lines.append(
      f'| {f.get("flight_number", "")} '
      f'| {f.get("airline", "")} '
      f'| {dep_info} '
      f'| {arr_info} '
      f'| {f.get("duration_display", "")} '
      f'| {price_str} |'
    )
  source = results[0].get("source", "")
  if source == "flyai":
    lines.append("\n> 数据来源：飞猪实时查询")
  return "\n".join(lines)


def _format_hotels(results: List[Dict[str, Any]], city: str) -> str:
  """Format hotel results as markdown."""
  if not results:
    return f"未找到 {city} 的酒店信息。"
  lines = [f"### {city} 酒店查询结果\n"]
  for h in results:
    stars = "★" * h.get("stars", 3)
    price = f'¥{h["price_per_night"]}/晚' if h.get("price_per_night") else ""
    name = h.get("name", "")
    area = h.get("area", "")
    lines.append(f"**{name}** {stars} {price}")
    if area:
      lines.append(f"  📍 {area}")
    if h.get("image_url"):
      lines.append(f"  ![]({h['image_url']})")
    if h.get("booking_url"):
      lines.append(f"  [查看详情]({h['booking_url']})")
    lines.append("")
  source = results[0].get("source", "") if results else ""
  if source == "flyai":
    lines.append("> 数据来源：飞猪实时查询")
  return "\n".join(lines)


def _format_pois(results: List[Dict[str, Any]], city: str) -> str:
  """Format POI results as markdown."""
  if not results:
    return f"未找到 {city} 的景点信息。"
  lines = [f"### {city} 热门景点\n"]
  for p in results:
    name = p.get("name", "")
    price = f'门票¥{p["price"]}' if p.get("price") else "免费"
    lines.append(f"**{name}** — {price}")
    if p.get("ticket_name"):
      lines.append(f"  🎫 {p['ticket_name']}")
    if p.get("image_url"):
      lines.append(f"  ![]({p['image_url']})")
    if p.get("booking_url"):
      lines.append(f"  [立即预订]({p['booking_url']})")
    lines.append("")
  source = results[0].get("source", "") if results else ""
  if source == "flyai":
    lines.append("> 数据来源：飞猪实时查询")
  return "\n".join(lines)


async def handle_search(
  session_id: str,
  message: str,
  history: list[dict[str, Any]],
  state_ctx: str,
) -> AsyncGenerator[dict, None]:
  """Handle direct search queries: call tool, format, stream results."""
  t0 = time.time()
  search_type = _detect_search_type(message)
  state = await state_pool.get(session_id)

  origin = getattr(state, "origin", None) if state else None
  dest = getattr(state, "destination", None) if state else None
  start_date = getattr(state, "start_date", None) if state else None
  travelers = getattr(state, "travelers", None) or 1

  # Extract date from message if not in state
  if not start_date:
    start_date = _extract_date(message)

  # Emit agent_start
  yield SSEMessage(
    event=SSEEventType.AGENT_START,
    data={"agent": "search", "status": f"正在搜索{search_type}..."},
  ).format()

  # Determine whether we need LLM fallback due to missing params
  needs_llm_fallback = False
  result_text = ""
  try:
    if search_type == "flights":
      if not origin or not dest:
        needs_llm_fallback = True
      else:
        from agent.tools.mcp.flight_search import search_flights
        r = await search_flights(
          departure=origin, arrival=dest,
          date=start_date or "", passengers=travelers, max_results=5,
        )
        result_text = _format_flights(r.get("results", []), origin, dest)

    elif search_type == "hotels":
      city = dest or origin
      if not city:
        needs_llm_fallback = True
      else:
        from agent.tools.mcp.hotel_search import search_hotels
        checkin = start_date or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        checkout = (datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")
        r = await search_hotels(city=city, checkin=checkin, checkout=checkout, guests=travelers, max_results=5)
        result_text = _format_hotels(r.get("results", []), city)

    elif search_type == "pois":
      city = dest or origin
      if not city:
        needs_llm_fallback = True
      else:
        from agent.tools.mcp.poi_search import search_pois
        r = await search_pois(city=city, limit=8)
        result_text = _format_pois(r.get("results", []), city)

  except Exception as exc:
    logger.warning("search_handler error: %s", exc)
    result_text = "搜索时出错，请稍后重试。"

  duration_ms = int((time.time() - t0) * 1000)

  # LLM fallback: stream a context-aware response instead of hardcoded text
  if needs_llm_fallback:
    settings = get_settings()
    llm_messages: list[dict[str, str]] = []
    for msg in history[-6:]:
      role = msg.get("role", "user")
      content = msg.get("content", "")
      if role in ("user", "assistant"):
        llm_messages.append({"role": role, "content": content[:500]})
    llm_messages.append({"role": "user", "content": message})

    full_response = ""
    try:
      async for chunk in llm_chat_stream(
        system=_SEARCH_FALLBACK_SYSTEM,
        messages=llm_messages,
        max_tokens=512,
        model=settings.PRIMARY_MODEL,
      ):
        if chunk:
          full_response += chunk
          yield SSEMessage(
            event=SSEEventType.TEXT,
            data={"content": chunk},
          ).format()
    except Exception as llm_exc:
      logger.warning("search_handler LLM fallback error: %s", llm_exc)

    if not full_response.strip():
      full_response = "搜索时出错，请稍后重试。"
      yield SSEMessage(
        event=SSEEventType.TEXT,
        data={"content": full_response},
      ).format()

    await session_memory.add_message(session_id, "assistant", full_response)
    yield SSEMessage(
      event=SSEEventType.DONE,
      data={"session_id": session_id},
    ).format()
    logger.info(
      "TIMING stage=search_llm_fallback type=%s duration_ms=%d session=%s",
      search_type, duration_ms, session_id,
    )
    return

  # Stream result as text
  yield SSEMessage(
    event=SSEEventType.TEXT,
    data={"content": result_text},
  ).format()

  # Save to session
  await session_memory.add_message(session_id, "assistant", result_text)

  yield SSEMessage(
    event=SSEEventType.DONE,
    data={"session_id": session_id},
  ).format()

  logger.info(
    "TIMING stage=search type=%s duration_ms=%d session=%s",
    search_type, duration_ms, session_id,
  )
