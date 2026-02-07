# User Simulator – generates virtual user personas and conversations
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class UserPersona:
  """A virtual user persona for simulation testing."""

  name: str
  description: str
  style: str
  initial_messages: List[str]
  follow_up_patterns: List[str]
  preferences: Dict[str, Any]


# ---------------------------------------------------------------------------
# Pre-defined personas
# ---------------------------------------------------------------------------

HESITANT_PERSONA = UserPersona(
  name="hesitant",
  description="Indecisive user who keeps changing requirements",
  style=(
    "Speaks tentatively, uses hedging words like 'maybe', 'not sure', "
    "'or maybe'. Frequently changes mind mid-conversation. Asks for "
    "multiple alternatives before deciding."
  ),
  initial_messages=[
    "我想出去玩，但是还没想好去哪里，你能帮我推荐一下吗？",
    "嗯...我在考虑去日本或者泰国，但又觉得国内也不错，怎么选呢？",
    "春节想出去旅游，不过又怕人多，有什么好建议吗？",
    "我和朋友商量了很久，还是决定不了去哪，预算大概1万左右吧，也可能多一点",
  ],
  follow_up_patterns=[
    "嗯...其实我又想了想，能不能换成{destination}看看？",
    "刚才说的方案不错，但是我觉得价格有点贵，有没有便宜一点的？",
    "等等，我朋友说{destination}更好玩，能重新推荐一下吗？",
    "这个酒店看起来还行，不过我又想住民宿了，有推荐吗？",
    "算了，还是按你最开始推荐的来吧，不过时间能不能改成{duration}天？",
    "我再想想...对了，能不能把行程安排得松一点？我不想太赶",
  ],
  preferences={
    "decision_style": "indecisive",
    "flexibility": "high",
    "info_need": "multiple_options",
  },
)

PRICE_SENSITIVE_PERSONA = UserPersona(
  name="price_sensitive",
  description="Extremely price-conscious user who always wants to save money",
  style=(
    "Constantly asks about prices, compares costs, looks for discounts. "
    "Questions every expense. Prefers budget options over comfort."
  ),
  initial_messages=[
    "我想去三亚玩3天，预算控制在2000以内，越便宜越好",
    "最近机票什么时候最便宜？我想找个性价比高的目的地",
    "有没有那种特价机票加酒店的套餐？我预算有限",
    "去日本5天最低需要多少钱？我看网上说有人3000就搞定了",
    "国庆想出去玩但不想花太多钱，有什么省钱攻略吗？",
  ],
  follow_up_patterns=[
    "这个价格太贵了！有没有更便宜的选择？",
    "能不能找个更划算的酒店？我不需要太好的，干净就行",
    "机票能不能再便宜点？红眼航班也可以接受",
    "门票要{price}块？有没有免费的景点推荐？",
    "吃饭方面有没有便宜又好吃的推荐？不用去高档餐厅",
    "总价能控制在{budget}以内吗？超出预算了",
  ],
  preferences={
    "budget_priority": "lowest",
    "accommodation": "budget",
    "transport": "cheapest",
    "dining": "street_food",
  },
)

VAGUE_PERSONA = UserPersona(
  name="vague",
  description="User with unclear requirements and incomplete information",
  style=(
    "Gives minimal details, vague descriptions. Does not specify dates, "
    "budget, or number of travelers unless asked directly."
  ),
  initial_messages=[
    "我想出去玩",
    "帮我安排个旅行",
    "想去个暖和的地方待几天",
    "有什么好玩的地方推荐吗",
    "想带家人出去转转",
  ],
  follow_up_patterns=[
    "都行，你推荐就好",
    "随便，我没什么特别要求",
    "嗯...大概{duration}天吧，也不一定",
    "预算的话...看情况吧",
    "人数啊，可能两三个人？还没定",
    "什么时候去都行，最近有空就去",
  ],
  preferences={
    "specificity": "low",
    "delegation": "high",
    "flexibility": "very_high",
  },
)

LUXURY_PERSONA = UserPersona(
  name="luxury",
  description="High-end user who demands premium experiences",
  style=(
    "Expects five-star service, luxury hotels, first-class flights. "
    "Emphasizes quality over price. Interested in exclusive experiences."
  ),
  initial_messages=[
    "我想去马尔代夫住水上别墅，要最好的那种，预算不是问题",
    "计划去欧洲两周，全程五星级酒店和商务舱，帮我安排一下",
    "我想体验一下日本顶级温泉旅馆，要那种一泊二食的",
    "想带太太去巴黎过结婚纪念日，要最浪漫的安排",
  ],
  follow_up_patterns=[
    "这个酒店评分太低了，有没有更高端的选择？",
    "我不坐经济舱，帮我看看商务舱或头等舱",
    "有没有私人导游服务？我不想跟团",
    "餐厅要米其林级别的，最好能提前预约",
    "能不能安排一些独特的体验？比如私人游艇、直升机之类的",
    "酒店要有行政酒廊和spa，房间至少要{size}平米以上",
  ],
  preferences={
    "accommodation": "five_star_luxury",
    "transport": "business_or_first",
    "dining": "michelin",
    "experience": "exclusive_premium",
    "budget_priority": "quality_first",
  },
)

FAMILY_PERSONA = UserPersona(
  name="family",
  description="Parent traveling with children, focused on safety and convenience",
  style=(
    "Mentions kids frequently, concerned about safety, asks about "
    "child-friendly options. Needs convenience and family facilities."
  ),
  initial_messages=[
    "想带两个孩子（3岁和7岁）去三亚玩5天，有什么适合亲子的行程吗？",
    "暑假想带小朋友去日本迪士尼，顺便玩几天，求推荐亲子酒店",
    "国庆带娃去哪玩比较好？孩子比较小，不想太折腾",
    "春节全家出游，爸妈加两个孩子，要方便推婴儿车的地方",
    "想找个有儿童乐园和泳池的度假酒店，最好是全包的那种",
  ],
  follow_up_patterns=[
    "这个景点适合小朋友吗？会不会太累？",
    "酒店有儿童设施吗？比如儿童泳池、游乐区什么的",
    "坐飞机的话，孩子的票怎么算？能选靠前的座位吗？",
    "行程能不能安排得松一点？小朋友中午需要午休",
    "有没有适合{age}岁孩子玩的地方？",
    "餐厅有儿童餐吗？我家孩子比较挑食",
  ],
  preferences={
    "child_friendly": True,
    "safety_priority": "high",
    "pace": "relaxed",
    "accommodation": "family_suite",
    "facilities": ["kids_pool", "playground", "babysitting"],
    "transport": "convenient_direct",
  },
)

# All personas in a lookup map
ALL_PERSONAS: Dict[str, UserPersona] = {
  "hesitant": HESITANT_PERSONA,
  "price_sensitive": PRICE_SENSITIVE_PERSONA,
  "vague": VAGUE_PERSONA,
  "luxury": LUXURY_PERSONA,
  "family": FAMILY_PERSONA,
}


class UserSimulator:
  """Generates simulated user conversations based on personas."""

  def __init__(self) -> None:
    self._personas = ALL_PERSONAS

  def list_personas(self) -> List[Dict[str, Any]]:
    """List all available personas with their info."""
    result: List[Dict[str, Any]] = []
    for key, persona in self._personas.items():
      result.append({
        "name": persona.name,
        "description": persona.description,
        "style": persona.style,
        "preferences": persona.preferences,
        "initial_message_count": len(persona.initial_messages),
        "follow_up_count": len(persona.follow_up_patterns),
      })
    return result

  def get_persona(self, name: str) -> UserPersona:
    """Get a persona by name.

    Raises:
      KeyError: if persona name is not found
    """
    if name not in self._personas:
      raise KeyError(
        f"Persona '{name}' not found. "
        f"Available: {list(self._personas.keys())}"
      )
    return self._personas[name]

  def get_random_persona(self) -> UserPersona:
    """Return a randomly selected persona."""
    return random.choice(list(self._personas.values()))

  def generate_conversation(
    self,
    persona: UserPersona,
    turns: int = 5,
  ) -> List[Dict[str, str]]:
    """Generate a simulated conversation sequence for a given persona.

    Each turn consists of a user message. The first message is chosen from
    the persona's initial_messages, and subsequent messages from
    follow_up_patterns with template variables filled in.

    Args:
      persona: The user persona to simulate
      turns: Number of user messages to generate (1-20)

    Returns:
      List of message dicts with 'role' and 'content' keys
    """
    turns = max(1, min(turns, 20))
    messages: List[Dict[str, str]] = []

    # First message: random initial message
    first_msg = random.choice(persona.initial_messages)
    messages.append({"role": "user", "content": first_msg})

    # Template variable pool for follow-up patterns
    template_vars = {
      "destination": random.choice([
        "日本", "泰国", "三亚", "大阪", "北京", "成都",
        "巴厘岛", "新加坡", "首尔", "普吉岛",
      ]),
      "duration": random.choice(["3", "5", "7", "10"]),
      "budget": random.choice([
        "5000", "8000", "1万", "2万", "3万",
      ]),
      "price": random.choice(["50", "100", "200", "300"]),
      "age": random.choice(["3", "5", "7", "10"]),
      "size": random.choice(["40", "50", "60", "80"]),
    }

    # Subsequent messages: sample from follow-up patterns
    used_patterns: List[int] = []
    for _ in range(turns - 1):
      # Pick an unused follow-up pattern if possible
      available_indices = [
        i for i in range(len(persona.follow_up_patterns))
        if i not in used_patterns
      ]
      if not available_indices:
        # Reset if all patterns have been used
        used_patterns = []
        available_indices = list(range(len(persona.follow_up_patterns)))

      idx = random.choice(available_indices)
      used_patterns.append(idx)

      pattern = persona.follow_up_patterns[idx]
      # Fill template variables
      try:
        content = pattern.format(**template_vars)
      except KeyError:
        content = pattern

      messages.append({"role": "user", "content": content})

    return messages
