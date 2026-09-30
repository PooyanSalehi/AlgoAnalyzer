"""Core configuration for the AlgoAnalyzer backend.

All settings can be overridden through environment variables or a `.env`
file placed next to the backend working directory (see `.env.example`).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings (12-factor style, environment driven)."""

    # --- Application -----------------------------------------------------
    app_name: str = "AlgoAnalyzer"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    debug: bool = False

    # --- Database ---------------------------------------------------------
    # Defaults to a local SQLite file so the project runs out of the box.
    # Production / docker-compose uses PostgreSQL, e.g.:
    #   postgresql+psycopg://algo:algo@db:5432/algoanalyzer
    database_url: str = "sqlite:///./algodata.db"

    # --- CORS ---------------------------------------------------------------
    # The Vite dev server proxies /api, so a wildcard is sufficient here
    # because no cookies / credentials are used by the API.
    cors_origins: list[str] = ["*"]

    # --- AI explanation layer (modular & replaceable) ----------------------
    # "heuristic" works fully offline; "openai" requires an API key and
    # automatically falls back to the heuristic engine on any failure.
    ai_provider: str = "heuristic"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = 20

    # --- Benchmark engine ----------------------------------------------------
    benchmark_enabled: bool = True
    benchmark_timeout_seconds: int = 30
    benchmark_max_memory_mb: int = 512
    benchmark_repeats: int = 3
    benchmark_time_budget_seconds: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
