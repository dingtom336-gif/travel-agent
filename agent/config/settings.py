# Application settings powered by pydantic-settings
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  """Global configuration – loaded from env vars / .env file."""

  # --- App ---
  APP_NAME: str = "TravelMind Agent Service"
  APP_VERSION: str = "0.1.0"
  DEBUG: bool = True

  # --- AI ---
  ANTHROPIC_API_KEY: str = ""
  CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
  CLAUDE_MAX_TOKENS: int = 4096

  # --- Infra (not used yet, placeholders) ---
  REDIS_URL: str = "redis://localhost:6379/0"
  DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travelmind"

  # --- CORS ---
  CORS_ORIGINS: List[str] = ["*"]

  # --- Memory ---
  MAX_SESSION_TURNS: int = 20

  model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "ignore",
  }


@lru_cache()
def get_settings() -> Settings:
  """Singleton accessor for settings."""
  return Settings()
