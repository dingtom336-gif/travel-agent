# Application settings powered by pydantic-settings
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Resolve .env relative to project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
  """Global configuration – loaded from env vars / .env file."""

  # --- App ---
  APP_NAME: str = "TravelMind Agent Service"
  APP_VERSION: str = "0.8.0"
  DEBUG: bool = True

  # --- AI (DeepSeek – OpenAI-compatible API) ---
  DEEPSEEK_API_KEY: str = ""
  DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
  DEEPSEEK_MODEL: str = "deepseek-chat"
  DEEPSEEK_REASONER_MODEL: str = "deepseek-reasoner"
  LLM_MAX_TOKENS: int = 2048
  LLM_AGENT_TOKENS: int = 1024
  LLM_TIMEOUT: float = 30.0
  LLM_TASK_TIMEOUT: float = 45.0
  LLM_SYNTHESIS_TIMEOUT: float = 60.0
  LLM_STREAM_CHUNK_TIMEOUT: float = 30.0
  LLM_CACHE_SIZE: int = 100
  LLM_CACHE_TTL: int = 300
  LLM_RATE_LIMIT_RPM: int = 300
  LLM_MAX_CONCURRENT: int = 3

  # Legacy – kept for compatibility checks
  ANTHROPIC_API_KEY: str = ""

  # --- Infra ---
  REDIS_URL: str = "redis://localhost:6379/0"
  DATABASE_URL: str = "postgresql+asyncpg://xiaozhang@localhost:5432/travelmind"
  DATABASE_POOL_SIZE: int = 5
  DATABASE_MAX_OVERFLOW: int = 10
  DATABASE_ECHO: bool = False

  # --- Serper API ---
  SERPER_API_KEY: str = ""

  # --- Amap (高德地图) ---
  AMAP_API_KEY: str = ""

  # --- QWeather (和风天气) ---
  QWEATHER_API_KEY: str = ""

  # --- CORS ---
  CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
  ]

  # --- Memory ---
  MAX_SESSION_TURNS: int = 20
  SESSION_MAX_COUNT: int = 1000
  SESSION_TTL_SECONDS: int = 7200
  TRACE_MAX_PER_SESSION: int = 200
  PROFILE_MAX_COUNT: int = 5000

  model_config = {
    "env_file": str(_ENV_FILE),
    "env_file_encoding": "utf-8",
    "extra": "ignore",
  }


@lru_cache()
def get_settings() -> Settings:
  """Singleton accessor for settings."""
  return Settings()
