# Knowledge Agent – visa / tips / culture specialist with RAG retrieval
from __future__ import annotations

import time
from typing import Any

from agent.memory.knowledge import knowledge_base
from agent.models import AgentName, AgentResult, AgentTask, TaskStatus
from agent.teams.base import BaseAgent


class KnowledgeAgent(BaseAgent):
  name = AgentName.KNOWLEDGE
  description = "Provides visa info, travel tips, cultural advice using knowledge base."

  async def execute(self, task: AgentTask, context: dict[str, Any]) -> AgentResult:
    try:
      start = time.time()

      # Extract destination and query from task params / goal
      destination = task.params.get("destination", "")
      query = task.goal
      category = task.params.get("category", None)

      # --- Step 1: Retrieve relevant knowledge from the knowledge base ---
      kb_results = []

      # Check if the task is specifically about visa info
      if any(kw in query for kw in ["签证", "visa", "入境", "出入境"]):
        visa_results = knowledge_base.get_visa_info(destination or query)
        kb_results.extend(visa_results)

      # Check for cultural queries
      if any(kw in query for kw in ["文化", "礼仪", "禁忌", "习俗"]):
        culture_results = knowledge_base.get_culture_info(destination or query)
        kb_results.extend(culture_results)

      # Check for food queries
      if any(kw in query for kw in ["美食", "小吃", "餐厅", "食物", "吃"]):
        food_results = knowledge_base.get_food_info(destination or query)
        kb_results.extend(food_results)

      # General search as fallback or supplement
      general_results = knowledge_base.search(
        query=query,
        destination=destination or None,
        category=category,
        top_k=5,
      )
      kb_results.extend(general_results)

      # Deduplicate by title
      seen_titles: set = set()
      unique_results = []
      for r in kb_results:
        if r["title"] not in seen_titles:
          seen_titles.add(r["title"])
          unique_results.append(r)

      # --- Step 2: Format knowledge context ---
      kb_context = knowledge_base.format_results(unique_results, max_entries=5)

      # --- Step 3: Enhance with Claude if available ---
      system_prompt = (
        "You are the Knowledge Agent for TravelMind. "
        "You provide visa info, cultural advice, travel tips, and safety info.\n\n"
        "Use the following knowledge base results as your primary source. "
        "Supplement with your own knowledge only when the KB does not cover the topic.\n"
        "Always respond in the same language as the user query.\n"
        "Format your response clearly with sections and bullet points."
      )

      user_message = (
        f"User query: {query}\n"
        f"Destination: {destination or 'not specified'}\n\n"
        f"--- Knowledge Base Results ---\n{kb_context}\n\n"
        f"Please synthesize the above information into a helpful, "
        f"well-structured response for the traveler."
      )

      response = await self._call_claude(system_prompt, user_message)

      return self._make_result(
        task,
        summary=f"Knowledge lookup for {task.goal} ({len(unique_results)} KB hits)",
        data={
          "response": response,
          "kb_hits": len(unique_results),
          "kb_titles": [r["title"] for r in unique_results[:5]],
        },
        start_time=start,
      )

    except Exception as exc:
      return self._make_result(
        task, summary="Knowledge lookup failed",
        status=TaskStatus.FAILED, error=str(exc),
      )
