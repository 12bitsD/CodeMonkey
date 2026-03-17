"""应用配置管理（Supabase 单数据库）"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = _get_env("APP_NAME", "PathFinder API")
    APP_VERSION: str = _get_env("APP_VERSION", "1.0.0")
    DEBUG: bool = _get_bool_env("DEBUG", True)

    DATABASE_URL: str = _get_env("DATABASE_URL", "")
    DATABASE_SCHEMA: str = _get_env("DATABASE_SCHEMA", "")

    JWT_SECRET_KEY: str = _get_env(
        "JWT_SECRET_KEY", "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = _get_env("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_DAYS: int = int(_get_env("JWT_EXPIRE_DAYS", "7"))

    CORS_ORIGINS_RAW: str = _get_env("CORS_ORIGINS", "*")
    CORS_ALLOW_CREDENTIALS: bool = _get_bool_env(
        "CORS_ALLOW_CREDENTIALS",
        True,
    )

    # LLM Configuration
    LLM_PROVIDER: str = _get_env("LLM_PROVIDER", "kimi")
    LLM_API_KEY: str = _get_env("LLM_API_KEY", "")
    LLM_BASE_URL: str = _get_env("LLM_BASE_URL", "https://api.moonshot.cn/v1")
    LLM_MODEL: str = _get_env("LLM_MODEL", "kimi-k2-5")
    LLM_TIMEOUT: int = int(_get_env("LLM_TIMEOUT", "30"))
    LLM_MAX_RETRIES: int = int(_get_env("LLM_MAX_RETRIES", "3"))
    LLM_TEMPERATURE: float = float(_get_env("LLM_TEMPERATURE", "0.7"))

    # Fallback configuration
    LLM_FALLBACK_ENABLED: bool = _get_bool_env("LLM_FALLBACK_ENABLED", True)
    LLM_FALLBACK_PROVIDER: str = _get_env("LLM_FALLBACK_PROVIDER", "openai")
    LLM_FALLBACK_API_KEY: str = _get_env("LLM_FALLBACK_API_KEY", "")
    LLM_FALLBACK_BASE_URL: str = _get_env("LLM_FALLBACK_BASE_URL", "")
    LLM_FALLBACK_MODEL: str = _get_env("LLM_FALLBACK_MODEL", "gpt-4o-mini")


settings = Settings()


def get_cors_origins() -> list[str]:
    raw = settings.CORS_ORIGINS_RAW.strip()
    if raw == "*" or raw == "":
        return ["*"]
    return [part.strip() for part in raw.split(",") if part.strip()]
