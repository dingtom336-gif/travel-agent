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
  APP_VERSION: str = "0.1.0"
  DEBUG: bool = True

  # --- AI (DeepSeek – OpenAI-compatible API) ---
  DEEPSEEK_API_KEY: str = ""
  DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
  DEEPSEEK_MODEL: str = "deepseek-chat"
  LLM_MAX_TOKENS: int = 2048
  LLM_AGENT_TOKENS: int = 1024
  LLM_TIMEOUT: float = 30.0
  LLM_TASK_TIMEOUT: float = 45.0

  # Legacy – kept for compatibility checks
  ANTHROPIC_API_KEY: str = ""

  # --- Infra (not used yet, placeholders) ---
  REDIS_URL: str = "redis://localhost:6379/0"
  DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travelmind"

  # --- CORS ---
  CORS_ORIGINS: List[str] = ["*"]

  # --- Memory ---
  MAX_SESSION_TURNS: int = 20

  model_config = {
    "env_file": str(_ENV_FILE),
    "env_file_encoding": "utf-8",
    "extra": "ignore",
  }


@lru_cache()
def get_settings() -> Settings:
  """Singleton accessor for settings."""
  return Settings()
