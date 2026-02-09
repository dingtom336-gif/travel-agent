# Scoring rules & Evaluator tests – pure rule-based, no LLM dependency
from __future__ import annotations

import pytest

from agent.simulator.scoring_rules import (
    score_coherence,
    score_completeness,
    score_intent_understanding,
    score_personalization,
    score_response_quality,
    score_tool_usage,
)
from agent.simulator.evaluator import (
    DimensionScore,
    EvaluationDimension,
    EvaluationReport,
    Evaluator,
)


# ---------------------------------------------------------------------------
# Helpers: reusable message / trace fixtures
# ---------------------------------------------------------------------------

def _msgs(*pairs):
    """Build a message list from (role, content) pairs."""
    return [{"role": r, "content": c} for r, c in pairs]


RICH_MESSAGES = _msgs(
    ("user", "我想去东京玩5天，2个人，预算1万元，3月出发"),
    ("assistant",
     "## 东京5日行程规划\n\n"
     "为您推荐以下行程：\n"
     "- 机票：北京到东京直飞航班\n"
     "- 酒店：新宿希尔顿酒店\n"
     "- 景点：浅草寺、涩谷、秋叶原\n"
     "- 预算：总计约9800元\n"
     "根据您的偏好，推荐给您经济实惠的方案"),
)

FULL_TRACES = [
    {"agent": "transport", "status": "success"},
    {"agent": "hotel", "status": "success"},
    {"agent": "poi", "status": "success"},
    {"agent": "itinerary", "status": "success"},
    {"agent": "budget", "status": "success"},
    {"agent": "weather", "status": "success"},
    {"agent": "knowledge", "status": "success"},
]


# ===========================================================================
# score_intent_understanding
# ===========================================================================

class TestIntentUnderstanding:
    def test_all_params_identified(self):
        """Score 5 when destination, date, travelers, and budget are all found."""
        msgs = _msgs(
            ("user", "我想去东京，3月出发，2个人，预算1万元"),
            ("assistant", "收到，目的地东京"),
        )
        score, reason, details = score_intent_understanding(msgs, [])
        assert score == 5
        assert details["destination_identified"] is True
        assert details["date_identified"] is True
        assert details["travelers_identified"] is True
        assert details["budget_identified"] is True

    def test_no_params_identified(self):
        """Score 1 when none of the key params are found."""
        msgs = _msgs(
            ("user", "hello"),
            ("assistant", "welcome"),
        )
        score, reason, details = score_intent_understanding(msgs, [])
        assert score == 1

    def test_partial_params(self):
        """Score reflects the number of params found."""
        msgs = _msgs(
            ("user", "我想去日本旅游"),
            ("assistant", "好的"),
        )
        score, _, details = score_intent_understanding(msgs, [])
        assert details["destination_identified"] is True
        assert score >= 2

    def test_empty_messages(self):
        """Empty messages list yields score 1."""
        score, _, _ = score_intent_understanding([], [])
        assert score == 1


# ===========================================================================
# score_tool_usage
# ===========================================================================

class TestToolUsage:
    def test_no_traces(self):
        """No traces gives a neutral score of 3."""
        score, reason, details = score_tool_usage([], [])
        assert score == 3
        assert details["traces_available"] is False

    def test_full_coverage_all_success(self):
        """All expected agents used and successful gives high score."""
        score, _, details = score_tool_usage([], FULL_TRACES)
        assert score >= 4
        assert details["simple_mode"] is False
        assert details["coverage"] == 7

    def test_simple_mode(self):
        """Orchestrator-only traces trigger simple mode logic."""
        traces = [
            {"agent": "orchestrator", "status": "success"},
            {"agent": "orchestrator", "status": "success"},
        ]
        score, reason, details = score_tool_usage([], traces)
        assert details["simple_mode"] is True
        assert score == 4

    def test_simple_mode_with_failure(self):
        """Simple mode with a failure scores 3."""
        traces = [
            {"agent": "orchestrator", "status": "success"},
            {"agent": "orchestrator", "status": "FAILED"},
        ]
        score, _, details = score_tool_usage([], traces)
        assert details["simple_mode"] is True
        assert score == 3

    def test_partial_coverage(self):
        """Only a subset of expected agents used."""
        traces = [
            {"agent": "transport", "status": "success"},
            {"agent": "hotel", "status": "success"},
        ]
        score, _, details = score_tool_usage([], traces)
        assert details["coverage"] == 2
        assert 1 <= score <= 5

    def test_all_failed(self):
        """All calls failed gives low score."""
        traces = [
            {"agent": "transport", "status": "FAILED"},
            {"agent": "hotel", "status": "FAILED"},
            {"agent": "poi", "status": "FAILED"},
        ]
        score, _, details = score_tool_usage([], traces)
        assert score <= 2


# ===========================================================================
# score_response_quality
# ===========================================================================

class TestResponseQuality:
    def test_no_assistant_messages(self):
        """No assistant messages yields score 1."""
        msgs = _msgs(("user", "hello"))
        score, _, _ = score_response_quality(msgs)
        assert score == 1

    def test_high_quality_response(self):
        """Structured, relevant, error-free response with good length."""
        # Build a response long enough to hit both length thresholds (>=200 chars)
        msgs = _msgs(
            ("user", "我想去东京玩5天"),
            ("assistant",
             "## 东京5日行程\n\n"
             "- Day 1: 浅草寺、上野公园\n"
             "- Day 2: 涩谷、原宿、明治神宫\n"
             "- Day 3: 秋叶原、东京塔\n"
             "- Day 4: �的�的仓、横滨中华街\n"
             "- Day 5: 银座购物、成田机场\n\n"
             "推荐酒店：新宿希尔顿，交通便利。东京的景点非常丰富，"
             "建议购买东京地铁周游券，可以节省大量交通费用。"),
        )
        score, _, details = score_response_quality(msgs)
        assert score >= 3
        assert details["has_structured_content"] is True
        assert details["has_error_messages"] is False

    def test_short_response(self):
        """Very short response gets fewer quality points."""
        msgs = _msgs(
            ("user", "你好"),
            ("assistant", "好"),
        )
        score, _, details = score_response_quality(msgs)
        assert score <= 3
        assert details["avg_response_length"] < 100

    def test_error_in_response(self):
        """Response containing [ERROR] loses a point."""
        msgs = _msgs(
            ("user", "请推荐酒店"),
            ("assistant", "[ERROR] 服务暂时不可用" + "x" * 200),
        )
        score, _, details = score_response_quality(msgs)
        assert details["has_error_messages"] is True

    def test_empty_messages(self):
        """Empty messages yields score 1."""
        score, _, _ = score_response_quality([])
        assert score == 1


# ===========================================================================
# score_personalization
# ===========================================================================

class TestPersonalization:
    def test_personalized_response(self):
        """Response with preference keywords and personal tone scores high."""
        score, _, details = score_personalization(RICH_MESSAGES, [])
        assert details["references_preferences"] is True
        assert details["personal_tone"] is True
        assert score >= 3

    def test_no_personalization(self):
        """Generic response with no personalization cues scores 1."""
        msgs = _msgs(
            ("user", "hello"),
            ("assistant", "This is a generic travel plan."),
        )
        score, _, details = score_personalization(msgs, [])
        assert score == 1
        assert details["references_preferences"] is False

    def test_profile_in_traces(self):
        """Profile data in traces adds a point."""
        msgs = _msgs(
            ("user", "推荐酒店"),
            ("assistant", "为您推荐希尔顿"),
        )
        traces = [{"agent": "hotel", "profile": {"budget": "luxury"}}]
        score, _, details = score_personalization(msgs, traces)
        assert details["profile_data_loaded"] is True

    def test_empty_messages(self):
        """Empty messages yields score 1."""
        score, _, _ = score_personalization([], [])
        assert score == 1


# ===========================================================================
# score_completeness
# ===========================================================================

class TestCompleteness:
    def test_full_coverage(self):
        """Response covering all 4 categories scores 5."""
        score, reason, details = score_completeness(RICH_MESSAGES, [])
        coverage = details["coverage"]
        assert coverage["transport"] is True
        assert coverage["accommodation"] is True
        assert coverage["attractions"] is True
        assert coverage["budget"] is True
        assert score == 5

    def test_no_coverage(self):
        """Response with no travel categories scores 1."""
        msgs = _msgs(
            ("user", "你好"),
            ("assistant", "欢迎使用"),
        )
        score, _, details = score_completeness(msgs, [])
        assert score <= 2

    def test_partial_coverage(self):
        """Response mentioning only transport and hotel."""
        msgs = _msgs(
            ("user", "帮我规划行程"),
            ("assistant", "推荐直飞航班和酒店住宿"),
        )
        score, _, details = score_completeness(msgs, [])
        coverage = details["coverage"]
        assert coverage["transport"] is True
        assert coverage["accommodation"] is True
        assert score >= 2

    def test_traces_contribute(self):
        """Agent traces also contribute to completeness detection."""
        msgs = _msgs(("user", "规划行程"), ("assistant", "好的"))
        traces = [{"agent": "transport", "data": "机票信息"}]
        score, _, details = score_completeness(msgs, traces)
        assert details["coverage"]["transport"] is True

    def test_empty_messages(self):
        """Empty messages yields score 1."""
        score, _, _ = score_completeness([], [])
        assert score == 1


# ===========================================================================
# score_coherence
# ===========================================================================

class TestCoherence:
    def test_single_turn(self):
        """Single-turn conversation gets score 4 (not fully applicable)."""
        msgs = _msgs(
            ("user", "你好"),
            ("assistant", "欢迎"),
        )
        score, reason, details = score_coherence(msgs)
        assert score == 4
        assert details["turns"] == 1

    def test_no_assistant_messages(self):
        """No assistant messages returns 4 (single-turn path)."""
        msgs = _msgs(("user", "hello"))
        score, _, details = score_coherence(msgs)
        assert score == 4

    def test_multi_turn_coherent(self):
        """Multi-turn conversation with consistent destination scores reasonably."""
        msgs = _msgs(
            ("user", "我想去东京旅游"),
            ("assistant", "东京是很好的选择，我来为您推荐东京的行程"),
            ("user", "东京有什么好玩的景点"),
            ("assistant", "东京有浅草寺、涩谷等著名景点，东京塔也值得一看"),
        )
        score, _, details = score_coherence(msgs)
        assert score >= 1
        assert "东京" in details["destinations_mentioned"]
        # Only one destination mentioned — destination consistency check passes
        assert len(details["destinations_mentioned"]) <= 2

    def test_multi_turn_inconsistent_destinations(self):
        """Many different destinations may reduce coherence score."""
        msgs = _msgs(
            ("user", "去东京"),
            ("assistant", "推荐东京行程"),
            ("user", "换成大阪吧"),
            ("assistant", "大阪也不错"),
            ("user", "还是去曼谷"),
            ("assistant", "推荐曼谷、新加坡、巴厘岛、马尔代夫、首尔"),
        )
        score, _, details = score_coherence(msgs)
        # Many destinations => coherence may drop
        assert len(details["destinations_mentioned"]) > 2

    def test_empty_messages(self):
        """Empty messages yields the single-turn default."""
        score, _, _ = score_coherence([])
        assert score == 4


# ===========================================================================
# Evaluator integration
# ===========================================================================

class TestEvaluator:
    def setup_method(self):
        self.evaluator = Evaluator()

    def test_evaluate_conversation_returns_report(self):
        """evaluate_conversation produces an EvaluationReport with 6 dimensions."""
        report = self.evaluator.evaluate_conversation(RICH_MESSAGES, FULL_TRACES)
        assert isinstance(report, EvaluationReport)
        assert len(report.scores) == 6
        assert 1.0 <= report.total_score <= 5.0

    def test_evaluate_single_turn(self):
        """evaluate_single_turn wraps a single exchange into a report."""
        report = self.evaluator.evaluate_single_turn(
            "我想去东京",
            "## 东京推荐\n为您推荐东京5日游，包含机票、酒店和景点" + "x" * 200,
        )
        assert isinstance(report, EvaluationReport)
        assert len(report.scores) == 6

    def test_suggestions_for_low_scores(self):
        """Low-scoring conversation generates suggestions."""
        msgs = _msgs(("user", "hi"), ("assistant", "ok"))
        report = self.evaluator.evaluate_conversation(msgs, [])
        assert len(report.suggestions) > 0

    def test_generate_report_empty(self):
        """Empty evaluations list returns a no-data dict."""
        result = self.evaluator.generate_report([])
        assert result["count"] == 0

    def test_generate_report_aggregation(self):
        """Aggregated report computes averages across multiple evaluations."""
        r1 = self.evaluator.evaluate_conversation(RICH_MESSAGES, FULL_TRACES)
        r2 = self.evaluator.evaluate_single_turn(
            "去三亚3天", "推荐三亚行程，酒店住宿和景点门票"
        )
        result = self.evaluator.generate_report([r1, r2])
        assert result["count"] == 2
        assert "average_total_score" in result
        assert "dimension_averages" in result
        assert "best_dimension" in result
        assert "worst_dimension" in result

    def test_report_best_worst_dimensions(self):
        """EvaluationReport provides max and min dimension accessors."""
        report = self.evaluator.evaluate_conversation(RICH_MESSAGES, FULL_TRACES)
        assert report.max_dimension is not None
        assert report.min_dimension is not None
        assert report.max_dimension.score >= report.min_dimension.score

    def test_dimension_score_to_dict(self):
        """DimensionScore.to_dict serializes correctly."""
        ds = DimensionScore(
            dimension=EvaluationDimension.COHERENCE,
            score=4,
            reason="Good coherence",
            details={"turns": 3},
        )
        d = ds.to_dict()
        assert d["dimension"] == "coherence"
        assert d["score"] == 4
        assert d["label"] == "Multi-turn Coherence"

    def test_score_clamped_1_to_5(self):
        """DimensionScore clamps score to 1-5 range."""
        ds_low = DimensionScore(EvaluationDimension.COHERENCE, -1, "too low")
        ds_high = DimensionScore(EvaluationDimension.COHERENCE, 10, "too high")
        assert ds_low.score == 1
        assert ds_high.score == 5

    def test_report_to_dict(self):
        """EvaluationReport.to_dict serializes the full report."""
        report = self.evaluator.evaluate_conversation(RICH_MESSAGES, FULL_TRACES)
        d = report.to_dict()
        assert "total_score" in d
        assert "dimension_scores" in d
        assert "suggestions" in d
        assert len(d["dimension_scores"]) == 6
