# FastAPI entry point for TravelMind Agent Service
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agent.config.settings import get_settings
from agent.db import init_db, close_db
from agent.models import ChatRequest
from agent.orchestrator.agent import orchestrator
from agent.routes.export import router as export_router
from agent.routes.itinerary import router as itinerary_router
from agent.routes.profile import router as profile_router
from agent.simulator.battle_runner import run_battle, run_battle_stream
from agent.simulator.env_simulator import get_env_simulator
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
env_simulator = get_env_simulator()  # shared singleton with base.py
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


class BattleRequest(BaseModel):
  """Request body for POST /api/debug/battle."""
  persona: str = Field(..., description="Persona name")
  turns: int = Field(default=3, ge=1, le=10, description="Number of turns")
  scenario: Optional[str] = Field(default=None, description="Scenario to activate")


class ActivateScenarioRequest(BaseModel):
  """Request body for POST /api/debug/activate-scenario."""
  scenario: str = Field(..., description="Scenario name to activate")


@asynccontextmanager
async def lifespan(application: FastAPI):
  # Startup
  ok = await init_db()
  if ok:
    logger.info("Database connected")
  else:
    logger.warning("Database unavailable – using in-memory fallback")
  yield
  # Shutdown
  await close_db()


app = FastAPI(
  title=settings.APP_NAME,
  version=settings.APP_VERSION,
  description="TravelMind Agent Service – multi-agent travel planning",
  lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.CORS_ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- CRUD routers ---
app.include_router(itinerary_router)
app.include_router(profile_router)
app.include_router(export_router)


# --- Health check ---
@app.get("/health")
async def health_check():
  try:
    return {
      "status": "ok",
      "service": "travelmind-agent",
      "version": settings.APP_VERSION,
      "has_api_key": bool(settings.DEEPSEEK_API_KEY),
      "llm_model": settings.DEEPSEEK_MODEL,
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
    async def event_generator() -> AsyncGenerator[dict, None]:
      try:
        async for sse_chunk in orchestrator.handle_message(
          session_id=request.session_id,
          message=request.message,
        ):
          yield sse_chunk
      except Exception as exc:
        logger.exception("Stream generator error")
        import json
        yield {"event": "error", "data": json.dumps({"error": str(exc)})}
        yield {"event": "done", "data": json.dumps({"session_id": request.session_id or ""})}

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

    # Extract the text content from SSE chunks (each chunk is a dict)
    import json
    text_parts: list[str] = []
    final_session_id = session_id or ""
    for chunk in chunks:
      if isinstance(chunk, dict):
        evt = chunk.get("event", "")
        data_str = chunk.get("data", "{}")
        try:
          payload = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
          continue
        if evt == "text":
          text_parts.append(payload.get("content", ""))
        elif evt == "done":
          final_session_id = payload.get("session_id", final_session_id)

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

    traces = session_memory.get_traces(request.session_id)
    report = evaluator.evaluate_conversation(
      messages=history, agent_traces=traces,
    )
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


@app.post("/api/debug/activate-scenario")
async def debug_activate_scenario(request: ActivateScenarioRequest):
  """Activate a pre-defined fault scenario."""
  try:
    result = env_simulator.simulate_scenario(request.scenario)
    return result.to_dict()
  except ValueError as exc:
    return JSONResponse(status_code=400, content={"error": str(exc)})
  except Exception as exc:
    logger.exception("Debug activate-scenario error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/reset")
async def debug_reset():
  """Reset all active faults and environment state."""
  try:
    return env_simulator.reset()
  except Exception as exc:
    logger.exception("Debug reset error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/debug/fault-config")
async def debug_fault_config():
  """Get current fault configuration."""
  try:
    return env_simulator.get_fault_config()
  except Exception as exc:
    logger.exception("Debug fault-config error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/debug/sessions")
async def debug_list_sessions():
  """List all active sessions with message/trace counts."""
  try:
    from agent.memory.session import session_memory

    sessions = session_memory.list_sessions()
    result = []
    for sid in sessions:
      result.append({
        "session_id": sid,
        "message_count": len(session_memory.get_history(sid)),
        "trace_count": len(session_memory.get_traces(sid)),
      })
    return {"sessions": result}
  except Exception as exc:
    logger.exception("Debug sessions error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/debug/sessions/{session_id}")
async def debug_session_detail(session_id: str):
  """Get full detail of a session including messages and traces."""
  try:
    from agent.memory.session import session_memory

    history = session_memory.get_history(session_id)
    traces = session_memory.get_traces(session_id)
    if not history and not traces:
      return JSONResponse(
        status_code=404,
        content={"error": f"Session '{session_id}' not found"},
      )
    return {
      "session_id": session_id,
      "messages": history,
      "traces": traces,
      "message_count": len(history),
      "trace_count": len(traces),
    }
  except Exception as exc:
    logger.exception("Debug session detail error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/battle")
async def debug_battle(request: BattleRequest):
  """Run an automated persona vs orchestrator battle (non-streaming)."""
  try:
    result = await run_battle(
      persona_name=request.persona,
      turns=request.turns,
      scenario_name=request.scenario,
    )
    return result.to_dict()
  except KeyError as exc:
    return JSONResponse(status_code=404, content={"error": str(exc)})
  except Exception as exc:
    logger.exception("Debug battle error")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/api/debug/battle/stream")
async def debug_battle_stream(request: BattleRequest):
  """Run an automated battle with SSE progress streaming."""
  try:
    from collections.abc import AsyncGenerator as AG

    async def event_gen() -> AG[dict, None]:
      try:
        async for evt in run_battle_stream(
          persona_name=request.persona,
          turns=request.turns,
          scenario_name=request.scenario,
        ):
          yield evt
      except Exception as exc:
        import json
        logger.exception("Battle stream error")
        yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(
      event_gen(),
      media_type="text/event-stream",
    )
  except Exception as exc:
    logger.exception("Debug battle stream error")
    return JSONResponse(status_code=500, content={"error": str(exc)})
