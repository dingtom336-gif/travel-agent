# FastAPI entry point for TravelMind Agent Service
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from agent.config.settings import get_settings
from agent.models import ChatRequest
from agent.orchestrator.agent import orchestrator

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

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
