# Budget Agent – cost estimation and budget management specialist
from __future__ import annotations

import time
from typing import Any

from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent

SYSTEM_PROMPT = """You are the Budget Agent of TravelMind.
Your job is to estimate costs, manage budgets, and provide money-saving advice.

Given the user's travel parameters AND real budget/currency data, provide:
1. Budget breakdown by category (transport, accommodation, food, etc.).
2. Cost-saving tips specific to the destination.
3. Currency exchange advice if traveling internationally.

Respond in the same language as the user's message.
Keep the answer concise and structured (use markdown)."""


class BudgetAgent(BaseAgent):
  name = AgentName.BUDGET
  description = "Estimates costs and manages travel budget."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()

      # Extract parameters
      params = task.params or {}
      total_budget = params.get("budget") or params.get("total_budget", 0)
      trip_days = params.get("days") or params.get("duration_days", 5)
      destination = params.get("destination", "")
      travelers = params.get("travelers", 1)
      preference = params.get("preference", "balanced")
      currency_from = params.get("currency_from")
      currency_to = params.get("currency_to")

      # Try to parse budget as a number
      if isinstance(total_budget, str):
        try:
          total_budget = float(total_budget.replace("万", "0000").replace(",", ""))
        except ValueError:
          total_budget = 0

      tool_data = {}

      # Call budget allocator
      if total_budget > 0 and trip_days > 0:
        try:
          budget_result = await self.call_tool(
            "allocate_budget",
            total_budget=total_budget,
            trip_days=trip_days,
            preferences=preference,
            destination=destination,
            travelers=travelers,
          )
          tool_data["budget_allocation"] = budget_result
        except Exception:
          pass

      # Call currency converter if needed
      if currency_from and currency_to:
        try:
          amount = params.get("amount", total_budget or 10000)
          currency_result = await self.call_tool(
            "convert_currency",
            amount=amount,
            from_currency=currency_from,
            to_currency=currency_to,
          )
          tool_data["currency"] = currency_result
        except Exception:
          pass

      # Build prompt with tool results
      prompt = self._build_prompt(task, context, tool_data)
      response = await self._call_claude(SYSTEM_PROMPT, prompt)

      return self._make_result(
        task,
        summary=f"Budget analysis for {task.goal}",
        data={"response": response, "tool_data": tool_data},
        start_time=start,
      )
    except Exception as exc:
      return self._make_result(
        task, summary="Budget analysis failed",
        status=TaskStatus.FAILED, error=str(exc),
      )

