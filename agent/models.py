# Pydantic data models for TravelMind Agent service
# NOTE: Do NOT use `from __future__ import annotations` here.
# Pydantic needs runtime access to type annotations for validation.
# Use typing generics (List, Dict, etc.) for Python 3.9 compatibility.

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentName(str, Enum):
  """Available agent names in the system."""
  ORCHESTRATOR = "orchestrator"
  TRANSPORT = "transport"
  HOTEL = "hotel"
  POI = "poi"
  ITINERARY = "itinerary"
  BUDGET = "budget"
  KNOWLEDGE = "knowledge"
  WEATHER = "weather"
  CUSTOMER_SERVICE = "customer_service"


class TaskStatus(str, Enum):
  """Status of an agent task."""
  PENDING = "pending"
  RUNNING = "running"
  SUCCESS = "success"
  FAILED = "failed"
  SKIPPED = "skipped"


class SSEEventType(str, Enum):
  """Server-Sent Event types for streaming."""
  THINKING = "thinking"
  AGENT_START = "agent_start"
  AGENT_RESULT = "agent_result"
  TEXT = "text"
  UI_COMPONENT = "ui_component"
  ERROR = "error"
  DONE = "done"


# --- Request / Response ---

class ChatRequest(BaseModel):
  """Chat request from the client."""
  session_id: Optional[str] = None
  message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
  """Non-streaming chat response (for fallback)."""
  session_id: str
  message: str
  agent_trace: Optional[List[Dict[str, Any]]] = None


# --- Agent Task & Result ---

class AgentTask(BaseModel):
  """A sub-task dispatched to a specialist agent."""
  task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
  agent: AgentName
  goal: str
  params: Dict[str, Any] = Field(default_factory=dict)
  depends_on: List[str] = Field(default_factory=list)
  status: TaskStatus = TaskStatus.PENDING
  reuse_previous: bool = False


class AgentResult(BaseModel):
  """Result returned by a specialist agent."""
  task_id: str
  agent: AgentName
  status: TaskStatus = TaskStatus.SUCCESS
  summary: str = ""
  data: Dict[str, Any] = Field(default_factory=dict)
  error: Optional[str] = None
  duration_ms: int = 0


# --- Session State ---

class SessionState(BaseModel):
  """Global state pool for a session – tracks extracted travel params."""
  destination: Optional[str] = None
  origin: Optional[str] = None
  start_date: Optional[str] = None
  end_date: Optional[str] = None
  duration_days: Optional[int] = None
  travelers: Optional[int] = None
  budget: Optional[str] = None
  preferences: Dict[str, Any] = Field(default_factory=dict)
  constraints: List[str] = Field(default_factory=list)
  extra: Dict[str, Any] = Field(default_factory=dict)


# --- SSE Message ---

class SSEMessage(BaseModel):
  """A single SSE event payload."""
  event: SSEEventType
  data: Dict[str, Any] = Field(default_factory=dict)

  def format(self) -> dict:
    """Return dict for sse-starlette EventSourceResponse."""
    import json
    return {"event": self.event.value, "data": json.dumps(self.data, ensure_ascii=False)}
