# Reflection engine tests – zero LLM token cost (all mocked)
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from agent.models import AgentName, AgentResult, SessionState, TaskStatus
from agent.orchestrator.reflector import (
  ConsistencyChecker,
  PreflightValidator,
  ReflectionResult,
  identify_affected_agents,
)


class TestPreflightValidator:
    """Layer 1: Rule-based validation tests."""

    def setup_method(self):
        self.validator = PreflightValidator()

    def test_catches_destination_mismatch(self):
        """Detect when agents use a variant of the destination name."""
        state = SessionState(destination="塞尔维亚")
        # Two agents return responses with the typo "塞尔维他"
        results = {
            "t1": AgentResult(
                task_id="t1",
                agent=AgentName.POI,
                status=TaskStatus.SUCCESS,
                data={"response": "塞尔维他有很多景点，塞尔维他博物馆值得一看"},
            ),
            "t2": AgentResult(
                task_id="t2",
                agent=AgentName.HOTEL,
                status=TaskStatus.SUCCESS,
                data={"response": "塞尔维他中心广场附近有多家酒店"},
            ),
        }
        issues = self.validator.validate(results, state)
        # Should catch the variant "塞尔维他" appearing in 2+ agents
        dest_issues = [i for i in issues if i.field == "destination"]
        assert len(dest_issues) > 0, "Should detect destination name mismatch"
        assert "塞尔维他" in dest_issues[0].message

    def test_passes_clean_results(self):
        """No false positives when agents use the correct destination."""
        state = SessionState(destination="塞尔维亚")
        results = {
            "t1": AgentResult(
                task_id="t1",
                agent=AgentName.POI,
                status=TaskStatus.SUCCESS,
                data={"response": "塞尔维亚有很多景点，贝尔格莱德老城值得一看"},
            ),
            "t2": AgentResult(
                task_id="t2",
                agent=AgentName.HOTEL,
                status=TaskStatus.SUCCESS,
                data={"response": "塞尔维亚首都贝尔格莱德有多家酒店"},
            ),
        }
        issues = self.validator.validate(results, state)
        dest_issues = [i for i in issues if i.field == "destination"]
        assert len(dest_issues) == 0, "Should not flag correct destination usage"

    def test_detects_mass_agent_failure(self):
        """Flag when more than half of agents fail."""
        state = SessionState(destination="东京")
        results = {
            "t1": AgentResult(
                task_id="t1", agent=AgentName.POI,
                status=TaskStatus.FAILED, error="timeout",
            ),
            "t2": AgentResult(
                task_id="t2", agent=AgentName.HOTEL,
                status=TaskStatus.FAILED, error="timeout",
            ),
            "t3": AgentResult(
                task_id="t3", agent=AgentName.WEATHER,
                status=TaskStatus.SUCCESS,
                data={"response": "东京天气晴朗"},
            ),
        }
        issues = self.validator.validate(results, state)
        failure_issues = [i for i in issues if i.field == "agent_failure"]
        assert len(failure_issues) > 0, "Should detect >50% agent failure rate"


class TestConsistencyChecker:
    """Layer 2: LLM consistency check tests (mocked)."""

    def setup_method(self):
        self.checker = ConsistencyChecker()

    @pytest.mark.asyncio
    async def test_corrects_destination_typo(self):
        """LLM checker detects and corrects a destination typo."""
        mock_response = json.dumps({
            "passed": False,
            "issues": [{"field": "destination", "problem": "User typed 塞尔维他 but meant 塞尔维亚"}],
            "state_corrections": {"destination": "塞尔维亚"},
        })

        with patch("agent.orchestrator.reflector.llm_chat", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await self.checker.check(
                user_message="我想去塞尔维他玩五天",
                results={
                    "t1": AgentResult(
                        task_id="t1", agent=AgentName.POI,
                        status=TaskStatus.SUCCESS,
                        data={"response": "塞尔维他景点推荐"},
                    ),
                },
                state_ctx="Destination: 塞尔维他",
            )

        assert not result.passed
        assert result.state_corrections.get("destination") == "塞尔维亚"

    @pytest.mark.asyncio
    async def test_passes_when_no_issues(self):
        """LLM checker passes when everything is consistent."""
        mock_response = json.dumps({
            "passed": True,
            "issues": [],
            "state_corrections": {},
        })

        with patch("agent.orchestrator.reflector.llm_chat", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await self.checker.check(
                user_message="我想去东京玩五天",
                results={},
                state_ctx="Destination: 东京",
            )

        assert result.passed
        assert not result.state_corrections


class TestIdentifyAffectedAgents:
    """Test agent re-run selection based on state corrections."""

    def test_destination_change_affects_correct_agents(self):
        """Changing destination should re-run transport, hotel, poi, weather, knowledge."""
        reflection = ReflectionResult(
            passed=False,
            state_corrections={"destination": "塞尔维亚"},
        )
        results = {
            "t1": AgentResult(
                task_id="t1", agent=AgentName.POI, status=TaskStatus.SUCCESS,
            ),
            "t2": AgentResult(
                task_id="t2", agent=AgentName.HOTEL, status=TaskStatus.SUCCESS,
            ),
            "t3": AgentResult(
                task_id="t3", agent=AgentName.BUDGET, status=TaskStatus.SUCCESS,
            ),
        }
        to_rerun = identify_affected_agents(reflection, results)
        rerun_names = {name for name, _ in to_rerun}
        # POI and hotel should be re-run (they depend on destination)
        assert "poi" in rerun_names
        assert "hotel" in rerun_names
        # Budget does not depend on destination
        assert "budget" not in rerun_names

    def test_skips_failed_agents(self):
        """Don't re-run agents that already failed."""
        reflection = ReflectionResult(
            passed=False,
            state_corrections={"destination": "塞尔维亚"},
        )
        results = {
            "t1": AgentResult(
                task_id="t1", agent=AgentName.POI, status=TaskStatus.FAILED,
                error="timeout",
            ),
        }
        to_rerun = identify_affected_agents(reflection, results)
        assert len(to_rerun) == 0, "Should not re-run already-failed agents"
