# FastAPI entry point for TravelMind Agent Service
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agent.config.settings import get_settings
from agent.models import ChatRequest
from agent.orchestrator.agent import orchestrator
from agent.simulator.env_simulator import EnvironmentSimulator
from agent.simulator.evaluator import Evaluator
from agent.simulator.user_simulator import UserSimulator

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# --- Simulator singletons ---
user_simulator = UserSimulator()
env_simulator = EnvironmentSimulator()
evaluator = Evaluator()


# --- Debug request/response models ---
# NOTE: Do NOT use `from __future__ import annotations` in Pydantic models.
# These are defined in the same file which already has the import, but
# pydantic v2 handles it correctly for BaseModel subclasses.

class SimulateRequest(BaseModel):
  """Request body for POST /api/debug/simulate."""
  persona: str = Field(..., description="Persona name, e.g. 'price_sensitive'")
  turns: int = Field(default=5, ge=1, le=20, description="Number of turns")


class EvaluateRequest(BaseModel):
  """Request body for POST /api/debug/evaluate."""
  session_id: str = Field(..., description="Session ID to evaluate")


class InjectFaultRequest(BaseModel):
  """Request body for POST /api/debug/inject-fault."""
  fault_type: str = Field(..., description="Fault type to inject")
  params: Dict[str, Any] = Field(
    default_factory=dict,
    description="Optional fault parameters",
  )


app = FastAPI(
  title=settings.APP_NAME,
  version=settings.APP_VERSION,
  description="TravelMind Agent Service – multi-agent travel planning",
)

# --- CORS ---
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.CORS_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


# --- Health check ---
@app.get("/health")
async def health_check():
  try:
    return {
      "status": "ok",
      "service": "travelmind-agent",
      "version": settings.APP_VERSION,
      "has_api_key": bool(settings.ANTHROPIC_API_KEY),
    }
  except Exception as exc:
    return JSONResponse(
      status_code=500,
      content={"status": "error", "detail": str(exc)},
    )


# --- Streaming chat endpoint ---
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
  """SSE streaming chat endpoint.

  Events:
    thinking   – agent thought process
    agent_start – sub-agent begins execution
    agent_result – sub-agent finishes
    text       – final text output
    error      – error occurred
    done       – stream finished
  """
  try:
    async def event_generator() -> AsyncGenerator[str, None]:
      try:
        async for sse_chunk in orchestrator.handle_message(
          session_id=request.session_id,
          message=request.message,
        ):
          yield sse_chunk
      except Exception as exc:
        logger.exception("Stream generator error")
        import json
        yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        yield f"event: done\ndata: {json.dumps({'session_id': request.session_id or ''})}\n\n"

    return EventSourceResponse(
      event_generator(),
      media_type="text/event-stream",
    )
  except Exception as exc:
    logger.exception("Chat stream endpoint error")
    return JSONResponse(
      status_code=500,
      content={"error": str(exc)},
    )


# --- Non-streaming fallback ---
@app.post("/api/chat")
async def chat(request: ChatRequest):
  """Non-streaming chat endpoint for testing."""
  try:
    chunks: list[str] = []
    session_id = request.session_id
    async for sse_chunk in orchestrator.handle_message(
      session_id=session_id,
      message=request.message,
    ):
      chunks.append(sse_chunk)

    # Extract the text content from SSE chunks
    text_parts: list[str] = []
    final_session_id = session_id or ""
    for chunk in chunks:
      if "event: text" in chunk:
        import json
        data_line = chunk.split("data: ", 1)[-1].strip()
        try:
          payload = json.loads(data_line)
          text_parts.append(payload.get("content", ""))
        except json.JSONDecodeError:
          pass
      if "event: done" in chunk:
        import json
        data_line = chunk.split("data: ", 1)[-1].strip()
        try:
          payload = json.loads(data_line)
          final_session_id = payload.get("session_id", final_session_id)
        except json.JSONDecodeError:
          pass

    return {
      "session_id": final_session_id,
      "message": "\n".join(text_parts) if text_parts else "No response generated.",
    }
  except Exception as exc:
    logger.exception("Chat endpoint error")
    return JSONResponse(
      status_code=500,
      content={"error": str(exc)},
    )


# ====================================================================== #
# Debug / Simulator endpoints
# ====================================================================== #

@app.get("/api/debug/personas")
async def debug_list_personas():
  """List all simulated user personas."""
  try:
    return {"personas": user_simulator.list_personas()}
  except Exception as exc:
    logger.exception("Debug personas error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/simulate")
async def debug_simulate(request: SimulateRequest):
  """Run a simulated conversation for a given persona."""
  try:
    persona = user_simulator.get_persona(request.persona)
    messages = user_simulator.generate_conversation(
      persona=persona,
      turns=request.turns,
    )
    return {
      "persona": persona.name,
      "turns": len(messages),
      "messages": messages,
    }
  except KeyError as exc:
    return JSONResponse(status_code=404, content={"error": str(exc)})
  except Exception as exc:
    logger.exception("Debug simulate error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/evaluate")
async def debug_evaluate(request: EvaluateRequest):
  """Evaluate conversation quality for a given session."""
  try:
    from agent.memory.session import session_memory

    history = session_memory.get_history(request.session_id)
    if not history:
      return JSONResponse(
        status_code=404,
        content={"error": f"Session '{request.session_id}' not found or empty"},
      )

    report = evaluator.evaluate_conversation(messages=history)
    return {
      "session_id": request.session_id,
      "evaluation": report.to_dict(),
    }
  except Exception as exc:
    logger.exception("Debug evaluate error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/debug/scenarios")
async def debug_list_scenarios():
  """List all available simulation scenarios."""
  try:
    return {"scenarios": env_simulator.list_scenarios()}
  except Exception as exc:
    logger.exception("Debug scenarios error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/inject-fault")
async def debug_inject_fault(request: InjectFaultRequest):
  """Inject a fault into the simulated environment."""
  try:
    result = env_simulator.inject_fault(
      fault_type=request.fault_type,
      **request.params,
    )
    return result
  except ValueError as exc:
    return JSONResponse(status_code=400, content={"error": str(exc)})
  except Exception as exc:
    logger.exception("Debug inject-fault error")
    return JSONResponse(status_code=500, content={"error": str(exc)})
