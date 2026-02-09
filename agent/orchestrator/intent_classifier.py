# Lightweight local intent classifier – < 1ms inference, no LLM calls
from __future__ import annotations

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Destination list reused from state_extractor
KNOWN_DESTINATIONS = {
    "日本", "东京", "大阪", "京都", "泰国", "曼谷", "韩国", "首尔",
    "新加坡", "马来西亚", "北京", "上海", "广州", "深圳", "成都",
    "三亚", "丽江", "西安", "杭州", "重庆", "香港", "澳门", "台北",
    "越南", "河内", "印尼", "巴厘岛", "菲律宾", "柬埔寨",
    "法国", "巴黎", "英国", "伦敦", "德国", "意大利", "罗马",
    "西班牙", "巴塞罗那", "美国", "纽约", "洛杉矶", "澳大利亚",
    "悉尼", "新西兰", "土耳其", "伊斯坦布尔", "埃及", "迪拜",
    "塞尔维亚", "贝尔格莱德", "希腊", "瑞士", "冰岛", "挪威",
    "清迈", "普吉", "奈良", "北海道", "冲绳", "济州岛",
    "马尔代夫", "斯里兰卡", "尼泊尔", "缅甸", "老挝",
}

GREETING_WORDS = {
    "你好", "hello", "hi", "hey", "嗨", "谢谢", "thanks", "thank you",
    "再见", "bye", "好的", "ok", "嗯", "哦", "行", "可以",
    "感谢", "不客气", "没事", "好", "是的", "对",
}

TRAVEL_KEYWORDS = {
    "旅行", "旅游", "规划", "攻略", "机票", "酒店", "行程",
    "景点", "推荐", "签证", "预算", "天气", "美食", "购物",
    "plan", "trip", "travel", "flight", "hotel", "itinerary",
    "自由行", "跟团", "民宿", "交通", "高铁", "火车", "地铁",
    "打车", "租车", "门票", "出行", "游玩", "度假",
}

QUESTION_WORDS = {"怎么", "哪里", "多少", "什么时候", "几天", "几个人", "推荐", "如何", "哪个"}

# Compiled regex for number patterns (X天, X万, X人, etc.)
_NUMBER_PATTERN = re.compile(r'\d+[天日万元块人个月岁]')


class IntentClassifier:
    """Lightweight local intent classifier using feature scoring. < 1ms."""

    # Tunable weights – treat as a "prompt" for the scoring model
    WEIGHTS = {
        "has_travel_context": 0.6,    # Strong complex signal
        "greeting_match": -0.8,       # Strong simple signal
        "travel_keyword_hit": 0.3,    # Per keyword hit
        "location_match": 0.5,        # Destination mentioned
        "number_pattern": 0.3,        # Dates/budget/travelers
        "long_message": 0.2,          # > 20 chars
        "question_words": 0.15,       # Per question word
    }
    THRESHOLD = 0.3  # score >= threshold → complex

    def classify(
        self,
        message: str,
        has_travel_context: bool = False,
    ) -> Tuple[str, float]:
        """Classify message as 'simple' or 'complex'.

        Returns (label, confidence) where confidence is 0-1.
        """
        score = 0.0
        msg = message.strip()
        msg_lower = msg.lower()

        # Feature 1: Existing travel context → strong complex signal
        if has_travel_context:
            score += self.WEIGHTS["has_travel_context"]

        # Feature 2: Greeting match → strong simple signal
        # Only treat as greeting if it's a known greeting word
        # Short non-greeting words with context are likely follow-ups, not greetings
        is_known_greeting = msg_lower in GREETING_WORDS
        if is_known_greeting:
            score += self.WEIGHTS["greeting_match"]

        # Feature 3: Travel keywords
        kw_count = sum(1 for kw in TRAVEL_KEYWORDS if kw in msg_lower)
        score += kw_count * self.WEIGHTS["travel_keyword_hit"]

        # Feature 4: Location match
        if any(loc in msg for loc in KNOWN_DESTINATIONS):
            score += self.WEIGHTS["location_match"]

        # Feature 5: Number patterns (X天, X万, X人, X月X日)
        if _NUMBER_PATTERN.search(msg):
            score += self.WEIGHTS["number_pattern"]

        # Feature 6: Message length
        if len(msg) > 20:
            score += self.WEIGHTS["long_message"]

        # Feature 7: Question words
        qw_count = sum(1 for qw in QUESTION_WORDS if qw in msg)
        score += qw_count * self.WEIGHTS["question_words"]

        # Classify
        label = "complex" if score >= self.THRESHOLD else "simple"
        confidence = min(abs(score - self.THRESHOLD) / 1.0, 1.0)

        logger.info(
            "IntentClassifier: label=%s score=%.2f confidence=%.2f msg=%s",
            label, score, confidence, msg[:50],
        )
        return label, confidence


# Singleton
intent_classifier = IntentClassifier()
