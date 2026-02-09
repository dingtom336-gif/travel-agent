# Customer Service Agent – after-sales / emergency specialist (stub)
from __future__ import annotations

from agent.models import AgentName
from agent.teams.base import BaseAgent


class CustomerServiceAgent(BaseAgent):
  name = AgentName.CUSTOMER_SERVICE
  description = "Handles after-sales support, complaints, and emergencies."
  _success_label = "Customer service"
  _failure_label = "Customer service failed"

  system_prompt = (
    "You are the Customer Service Agent. "
    "Handle support and emergency requests."
  )
