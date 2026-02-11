# POI search MCP tool - Amap (primary) + Serper (fallback) + mock
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from agent.tools.amap.client import search_poi as amap_search_poi

logger = logging.getLogger(__name__)

# Category → Amap keyword mapping
_CATEGORY_TO_AMAP: Dict[str, str] = {
  "scenic": "风景名胜",
  "restaurant": "餐饮服务",
  "shopping": "购物服务",
  "activity": "体育休闲服务",
  "museum": "博物馆",
  "park": "公园广场",
}


# Supported categories
CATEGORIES = ["scenic", "restaurant", "shopping", "activity", "museum", "park"]

# City-specific POI data pools
_POI_POOLS: Dict[str, List[Dict[str, Any]]] = {
  "东京": [
    {"name": "浅草寺", "name_en": "Senso-ji Temple", "category": "scenic", "rating": 4.6, "price": 0, "hours": "06:00-17:00", "desc": "东京最古老的寺庙，雷门大灯笼是东京标志性景点", "coordinates": {"lat": 35.7148, "lng": 139.7967}},
    {"name": "东京塔", "name_en": "Tokyo Tower", "category": "scenic", "rating": 4.5, "price": 150, "hours": "09:00-23:00", "desc": "333米高的红白相间铁塔，俯瞰东京全景", "coordinates": {"lat": 35.6586, "lng": 139.7454}},
    {"name": "东京晴空塔", "name_en": "Tokyo Skytree", "category": "scenic", "rating": 4.7, "price": 210, "hours": "10:00-21:00", "desc": "634米的世界最高自立式广播塔，观景台视野极佳", "coordinates": {"lat": 35.7101, "lng": 139.8107}},
    {"name": "明治神宫", "name_en": "Meiji Jingu", "category": "scenic", "rating": 4.6, "price": 0, "hours": "日出-日落", "desc": "东京最大的神社，被70万棵树木环绕的城市绿洲", "coordinates": {"lat": 35.6764, "lng": 139.6993}},
    {"name": "筑地场外市场", "name_en": "Tsukiji Outer Market", "category": "restaurant", "rating": 4.5, "price": 0, "hours": "05:00-14:00", "desc": "海鲜天堂，汇集超过400家店铺和餐厅", "coordinates": {"lat": 35.6654, "lng": 139.7707}},
    {"name": "一兰拉面(涩谷本店)", "name_en": "Ichiran Ramen Shibuya", "category": "restaurant", "rating": 4.4, "price": 80, "hours": "10:00-06:00", "desc": "天然猪骨汤底拉面，可定制辣度和浓度", "coordinates": {"lat": 35.6596, "lng": 139.6988}},
    {"name": "银座三越百货", "name_en": "Mitsukoshi Ginza", "category": "shopping", "rating": 4.3, "price": 0, "hours": "10:00-20:00", "desc": "银座地标百货，汇集顶级品牌与精选商品", "coordinates": {"lat": 35.6712, "lng": 139.7660}},
    {"name": "秋叶原电器街", "name_en": "Akihabara Electric Town", "category": "shopping", "rating": 4.4, "price": 0, "hours": "10:00-21:00", "desc": "电子产品、动漫和宅文化的圣地", "coordinates": {"lat": 35.7023, "lng": 139.7745}},
    {"name": "TeamLab Borderless", "name_en": "TeamLab Borderless", "category": "activity", "rating": 4.8, "price": 230, "hours": "10:00-19:00", "desc": "沉浸式数字艺术美术馆，光影交互的梦幻体验", "coordinates": {"lat": 35.6256, "lng": 139.7838}},
    {"name": "东京国立博物馆", "name_en": "Tokyo National Museum", "category": "museum", "rating": 4.7, "price": 100, "hours": "09:30-17:00", "desc": "日本最古老最大的博物馆，藏品超11万件", "coordinates": {"lat": 35.7189, "lng": 139.7766}},
    {"name": "上野公园", "name_en": "Ueno Park", "category": "park", "rating": 4.5, "price": 0, "hours": "05:00-23:00", "desc": "东京最大的公园，春天的樱花大道闻名世界", "coordinates": {"lat": 35.7146, "lng": 139.7732}},
    {"name": "新宿御苑", "name_en": "Shinjuku Gyoen", "category": "park", "rating": 4.6, "price": 50, "hours": "09:00-16:00", "desc": "融合日式、英式、法式三种庭园风格的国家公园", "coordinates": {"lat": 35.6852, "lng": 139.7100}},
  ],
  "大阪": [
    {"name": "大阪城", "name_en": "Osaka Castle", "category": "scenic", "rating": 4.5, "price": 60, "hours": "09:00-17:00", "desc": "丰臣秀吉所建，大阪最具标志性的历史建筑", "coordinates": {"lat": 34.6873, "lng": 135.5262}},
    {"name": "道顿堀", "name_en": "Dotonbori", "category": "scenic", "rating": 4.6, "price": 0, "hours": "全天", "desc": "大阪最热闹的美食街，格力高跑步人霓虹灯标志", "coordinates": {"lat": 34.6687, "lng": 135.5013}},
    {"name": "环球影城", "name_en": "Universal Studios Japan", "category": "activity", "rating": 4.7, "price": 480, "hours": "09:00-21:00", "desc": "日本最大的电影主题乐园，哈利波特园区必去", "coordinates": {"lat": 34.6654, "lng": 135.4323}},
    {"name": "黑门市场", "name_en": "Kuromon Market", "category": "restaurant", "rating": 4.4, "price": 0, "hours": "08:00-17:00", "desc": "大阪的厨房，海鲜、水果、小吃一应俱全", "coordinates": {"lat": 34.6625, "lng": 135.5069}},
    {"name": "心斋桥筋商店街", "name_en": "Shinsaibashi-suji", "category": "shopping", "rating": 4.3, "price": 0, "hours": "10:00-21:00", "desc": "大阪最长的商店街，从平价到奢侈品应有尽有", "coordinates": {"lat": 34.6748, "lng": 135.5014}},
    {"name": "大阪海游馆", "name_en": "Osaka Aquarium", "category": "activity", "rating": 4.6, "price": 240, "hours": "10:00-20:00", "desc": "世界最大级别的水族馆，鲸鲨是镇馆之宝", "coordinates": {"lat": 34.6545, "lng": 135.4290}},
    {"name": "大阪市立美术馆", "name_en": "Osaka City Museum of Art", "category": "museum", "rating": 4.3, "price": 30, "hours": "09:30-17:00", "desc": "收藏东亚美术品超8500件的艺术殿堂", "coordinates": {"lat": 34.6517, "lng": 135.5086}},
    {"name": "天王寺公园", "name_en": "Tennoji Park", "category": "park", "rating": 4.2, "price": 0, "hours": "07:00-22:00", "desc": "大阪市内最大的公园，包含动物园和庭园", "coordinates": {"lat": 34.6497, "lng": 135.5131}},
  ],
  "北京": [
    {"name": "故宫博物院", "name_en": "The Forbidden City", "category": "museum", "rating": 4.8, "price": 60, "hours": "08:30-17:00", "desc": "世界上现存规模最大、保存最为完整的木质宫殿建筑群", "coordinates": {"lat": 39.9163, "lng": 116.3972}},
    {"name": "长城(八达岭)", "name_en": "Great Wall (Badaling)", "category": "scenic", "rating": 4.7, "price": 40, "hours": "06:30-17:00", "desc": "世界文化遗产，不到长城非好汉", "coordinates": {"lat": 40.3540, "lng": 116.0139}},
    {"name": "颐和园", "name_en": "Summer Palace", "category": "park", "rating": 4.7, "price": 30, "hours": "06:30-18:00", "desc": "中国现存规模最大的皇家园林", "coordinates": {"lat": 39.9999, "lng": 116.2755}},
    {"name": "天坛公园", "name_en": "Temple of Heaven", "category": "scenic", "rating": 4.6, "price": 15, "hours": "06:00-21:00", "desc": "明清皇帝祭天之所，祈年殿是北京城的象征", "coordinates": {"lat": 39.8822, "lng": 116.4066}},
    {"name": "南锣鼓巷", "name_en": "Nanluoguxiang", "category": "shopping", "rating": 4.2, "price": 0, "hours": "全天", "desc": "北京最古老的胡同之一，文创小店和特色美食", "coordinates": {"lat": 39.9370, "lng": 116.4030}},
    {"name": "全聚德烤鸭(前门店)", "name_en": "Quanjude Roast Duck", "category": "restaurant", "rating": 4.3, "price": 200, "hours": "11:00-21:00", "desc": "始于1864年的北京烤鸭老字号", "coordinates": {"lat": 39.8990, "lng": 116.3952}},
  ],
  "上海": [
    {"name": "外滩", "name_en": "The Bund", "category": "scenic", "rating": 4.7, "price": 0, "hours": "全天", "desc": "万国建筑博览群与陆家嘴天际线交相辉映", "coordinates": {"lat": 31.2400, "lng": 121.4900}},
    {"name": "东方明珠", "name_en": "Oriental Pearl Tower", "category": "scenic", "rating": 4.5, "price": 180, "hours": "08:00-21:30", "desc": "上海标志性建筑，360度全景观光", "coordinates": {"lat": 31.2397, "lng": 121.4998}},
    {"name": "豫园", "name_en": "Yu Garden", "category": "scenic", "rating": 4.4, "price": 40, "hours": "08:30-17:00", "desc": "明代古典园林，城隍庙小吃街就在旁边", "coordinates": {"lat": 31.2272, "lng": 121.4924}},
    {"name": "上海博物馆", "name_en": "Shanghai Museum", "category": "museum", "rating": 4.7, "price": 0, "hours": "09:00-17:00", "desc": "中国四大博物馆之一，青铜器收藏世界第一", "coordinates": {"lat": 31.2293, "lng": 121.4735}},
    {"name": "南京路步行街", "name_en": "Nanjing Road", "category": "shopping", "rating": 4.3, "price": 0, "hours": "全天", "desc": "中华第一商业街，百年老字号与国际品牌共存", "coordinates": {"lat": 31.2345, "lng": 121.4747}},
    {"name": "迪士尼乐园", "name_en": "Shanghai Disneyland", "category": "activity", "rating": 4.6, "price": 475, "hours": "08:30-20:30", "desc": "中国大陆首座迪士尼乐园，创极速光轮全球独家", "coordinates": {"lat": 31.1433, "lng": 121.6580}},
  ],
  "曼谷": [
    {"name": "大皇宫", "name_en": "Grand Palace", "category": "scenic", "rating": 4.7, "price": 50, "hours": "08:30-15:30", "desc": "泰国最神圣的庙宇，金碧辉煌的皇家建筑群", "coordinates": {"lat": 13.7500, "lng": 100.4914}},
    {"name": "卧佛寺", "name_en": "Wat Pho", "category": "scenic", "rating": 4.6, "price": 20, "hours": "08:00-18:30", "desc": "巨大的卧佛长46米，正宗泰式按摩的发源地", "coordinates": {"lat": 13.7465, "lng": 100.4930}},
    {"name": "暹罗百丽宫", "name_en": "Siam Paragon", "category": "shopping", "rating": 4.5, "price": 0, "hours": "10:00-22:00", "desc": "曼谷最高端购物中心，东南亚最大的海洋世界", "coordinates": {"lat": 13.7462, "lng": 100.5347}},
    {"name": "恰图恰周末市场", "name_en": "Chatuchak Market", "category": "shopping", "rating": 4.4, "price": 0, "hours": "09:00-18:00(周末)", "desc": "世界最大的跳蚤市场之一，超过15000个摊位", "coordinates": {"lat": 13.7999, "lng": 100.5504}},
    {"name": "建兴酒家", "name_en": "Somboon Seafood", "category": "restaurant", "rating": 4.5, "price": 60, "hours": "16:00-23:00", "desc": "曼谷最知名的咖喱蟹餐厅，超过50年历史", "coordinates": {"lat": 13.7434, "lng": 100.5401}},
    {"name": "曼谷国家博物馆", "name_en": "Bangkok National Museum", "category": "museum", "rating": 4.3, "price": 20, "hours": "09:00-16:00", "desc": "东南亚最大的博物馆，藏品涵盖泰国各历史时期", "coordinates": {"lat": 13.7572, "lng": 100.4918}},
  ],
}


def _add_common_fields(poi: Dict[str, Any], city: str) -> Dict[str, Any]:
  """Add computed fields to a POI record."""
  poi_copy = dict(poi)
  poi_copy["city"] = city
  poi_copy["popularity"] = random.randint(60, 99)
  poi_copy["recommended_duration"] = f"{random.choice([0.5, 1, 1.5, 2, 2.5, 3, 4])}h"

  # Best time to visit
  cat = poi_copy.get("category", "scenic")
  if cat in ("restaurant",):
    poi_copy["best_time"] = random.choice(["午餐时段(11:00-13:00)", "晚餐时段(17:00-20:00)"])
  elif cat in ("park",):
    poi_copy["best_time"] = random.choice(["上午", "傍晚"])
  else:
    poi_copy["best_time"] = random.choice(["上午", "下午", "全天皆宜"])

  # Tips
  tips_pool = [
    "建议提前网上预约门票",
    "周末人流较大，建议工作日前往",
    "附近交通便利，地铁可达",
    "建议穿舒适的步行鞋",
    "有中文导览服务",
    "支持电子支付",
    "适合拍照打卡",
    "建议预留充足时间游览",
  ]
  poi_copy["tips"] = random.sample(tips_pool, min(2, len(tips_pool)))
  if "coordinates" not in poi_copy:
    poi_copy["coordinates"] = {
      "lat": round(random.uniform(13.0, 55.0), 6),
      "lng": round(random.uniform(100.0, 140.0), 6),
    }
  return poi_copy


async def search_pois(
  city: str,
  category: Optional[str] = None,
  limit: int = 10,
  sort_by: str = "rating",
) -> Dict[str, Any]:
  """Search POIs. Fallback: Amap → Serper → mock.
  """
  query_meta = {"city": city, "category": category, "limit": limit, "sort_by": sort_by}

  # 1. Amap POI search (China-native, <80ms)
  try:
    keywords = _CATEGORY_TO_AMAP.get(category or "", "景点 餐厅 公园")
    raw_pois = await amap_search_poi(city, keywords=keywords, page_size=limit)
    if raw_pois:
      results = [_amap_to_poi(p, category) for p in raw_pois]
      results = _sort_pois(results, sort_by)[:limit]
      return {
        "success": True,
        "source": "amap",
        "query": query_meta,
        "results": results,
        "total_count": len(results),
        "available_categories": list(set(p.get("category", "") for p in results)),
      }
  except Exception as exc:
    logger.debug("Amap POI search failed for %s: %s", city, exc)

  # 2. Serper (may be blocked in China)
  try:
    from agent.tools.serper.client import search_places
    from agent.tools.serper.parsers import parse_poi_results
    cat_label = {"scenic": "景点", "restaurant": "餐厅", "shopping": "购物", "activity": "活动", "museum": "博物馆", "park": "公园"}.get(category or "", "景点 餐厅 购物")
    raw = await search_places(f"{city} {cat_label} 推荐")
    if "error" not in raw:
      pois = parse_poi_results(raw, city)
      if pois:
        if category:
          pois = [p for p in pois if p.get("category") == category] or pois
        pois = pois[:limit]
        return {
          "success": True,
          "source": "serper",
          "query": query_meta,
          "results": pois,
          "total_count": len(pois),
          "available_categories": list(set(p.get("category", "") for p in pois)),
        }
  except Exception:
    pass

  # 3. Mock fallback
  try:
    await asyncio.sleep(random.uniform(0.1, 0.2))
    pool = _POI_POOLS.get(city, [])
    if category and category in CATEGORIES:
      pool = [p for p in pool if p.get("category") == category]
    results = [_add_common_fields(p, city) for p in pool]
    results = _sort_pois(results, sort_by)[:limit]
    return {
      "success": True,
      "source": "mock",
      "query": query_meta,
      "results": results,
      "total_count": len(results),
      "available_categories": list(set(p.get("category", "") for p in results)),
    }
  except Exception as exc:
    return {"success": False, "error": str(exc), "query": query_meta, "results": [], "total_count": 0}


def _amap_to_poi(amap_poi: Dict[str, Any], category: Optional[str] = None) -> Dict[str, Any]:
  """Convert Amap POI result to our standard format."""
  amap_type = amap_poi.get("type", "")
  guessed_cat = category or _guess_category(amap_type)
  result: Dict[str, Any] = {
    "name": amap_poi.get("name", ""),
    "name_en": "",
    "category": guessed_cat,
    "rating": amap_poi.get("rating", 0),
    "price": int(amap_poi.get("cost", 0)),
    "hours": amap_poi.get("opentime", ""),
    "desc": amap_poi.get("address", ""),
    "city": "",
    "tips": [],
  }
  if amap_poi.get("coordinates"):
    result["coordinates"] = amap_poi["coordinates"]
  if amap_poi.get("image_url"):
    result["image_url"] = amap_poi["image_url"]
  return result


def _guess_category(amap_type: str) -> str:
  """Guess POI category from Amap type string."""
  if any(k in amap_type for k in ("餐饮", "餐厅", "小吃")):
    return "restaurant"
  if any(k in amap_type for k in ("购物", "商场", "百货")):
    return "shopping"
  if any(k in amap_type for k in ("博物馆", "展览")):
    return "museum"
  if any(k in amap_type for k in ("公园", "广场")):
    return "park"
  if any(k in amap_type for k in ("体育", "娱乐", "游乐")):
    return "activity"
  return "scenic"


def _sort_pois(pois: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
  """Sort POIs by the specified criterion."""
  if sort_by == "rating":
    pois.sort(key=lambda p: p.get("rating", 0), reverse=True)
  elif sort_by == "popularity":
    pois.sort(key=lambda p: p.get("popularity", 0), reverse=True)
  elif sort_by == "price":
    pois.sort(key=lambda p: p.get("price", 0))
  return pois


def _generate_generic_pool(city: str) -> List[Dict[str, Any]]:
  """Generate generic POI data for cities not in the predefined pool."""
  return [
    {"name": f"{city}中心广场", "name_en": f"{city} Central Square", "category": "scenic", "rating": 4.3, "price": 0, "hours": "全天", "desc": f"{city}市中心地标广场"},
    {"name": f"{city}老街", "name_en": f"{city} Old Street", "category": "shopping", "rating": 4.1, "price": 0, "hours": "09:00-22:00", "desc": f"充满当地特色的传统商业街"},
    {"name": f"{city}博物馆", "name_en": f"{city} Museum", "category": "museum", "rating": 4.4, "price": 30, "hours": "09:00-17:00", "desc": f"了解{city}历史文化的最佳去处"},
    {"name": f"{city}公园", "name_en": f"{city} Park", "category": "park", "rating": 4.2, "price": 0, "hours": "06:00-22:00", "desc": f"{city}市区最大的城市公园"},
    {"name": f"{city}美食街", "name_en": f"{city} Food Street", "category": "restaurant", "rating": 4.3, "price": 0, "hours": "10:00-23:00", "desc": f"汇聚{city}特色小吃和地方菜"},
  ]
