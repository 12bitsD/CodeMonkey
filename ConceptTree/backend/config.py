"""应用配置管理（Supabase 单数据库）"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


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
    APP_NAME: str = _get_env("APP_NAME", "LearningMaster API")
    APP_VERSION: str = _get_env("APP_VERSION", "1.0.0")
    DEBUG: bool = _get_bool_env("DEBUG", False)

    DATABASE_URL: str = _get_env("DATABASE_URL", "")
    DATABASE_SCHEMA: str = _get_env("DATABASE_SCHEMA", "")
    DB_POOL_MIN_SIZE: int = int(_get_env("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(_get_env("DB_POOL_MAX_SIZE", "10"))
    DB_CONNECT_TIMEOUT: int = int(_get_env("DB_CONNECT_TIMEOUT", "5"))
    DB_STATEMENT_TIMEOUT_MS: int = int(_get_env("DB_STATEMENT_TIMEOUT_MS", "15000"))
    DB_LOCK_TIMEOUT_MS: int = int(_get_env("DB_LOCK_TIMEOUT_MS", "3000"))
    DB_IDLE_IN_TX_TIMEOUT_MS: int = int(_get_env("DB_IDLE_IN_TX_TIMEOUT_MS", "10000"))

    JWT_SECRET_KEY: str = _get_env(
        "JWT_SECRET_KEY", "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = _get_env("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_DAYS: int = int(_get_env("JWT_EXPIRE_DAYS", "7"))

    CORS_ORIGINS_RAW: str = _get_env("CORS_ORIGINS", "")
    CORS_ALLOW_CREDENTIALS: bool = _get_bool_env(
        "CORS_ALLOW_CREDENTIALS",
        True,
    )

    # LLM Configuration
    LLM_PROVIDER: str = _get_env("LLM_PROVIDER", "mimo_token_plan_cn")
    LLM_API_KEY: str = _get_env("LLM_API_KEY", "")
    LLM_BASE_URL: str = _get_env(
        "LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"
    )
    LLM_MODEL: str = _get_env("LLM_MODEL", "mimo-v2.5-pro")
    LLM_TIMEOUT: int = int(_get_env("LLM_TIMEOUT", "30"))
    LLM_MAX_RETRIES: int = int(_get_env("LLM_MAX_RETRIES", "2"))
    LLM_TEMPERATURE: float = float(_get_env("LLM_TEMPERATURE", "0.7"))
    LLM_REASONING_EFFORT: str = _get_env("LLM_REASONING_EFFORT", "low")

    # Image generation provider. Keep separate from the chat LLM so OpenRouter
    # credits/config can be used only when image_type == "dalle".
    IMAGE_PROVIDER: str = _get_env("IMAGE_PROVIDER", "openrouter")
    IMAGE_API_KEY: str = _get_env("IMAGE_API_KEY", _get_env("OPENROUTER_API_KEY", ""))
    IMAGE_BASE_URL: str = _get_env("IMAGE_BASE_URL", "https://openrouter.ai/api/v1")
    IMAGE_MODEL: str = _get_env("IMAGE_MODEL", "openai/gpt-5.4-image-2")
    IMAGE_TIMEOUT: int = int(_get_env("IMAGE_TIMEOUT", "300"))

    # Fallback configuration
    LLM_FALLBACK_ENABLED: bool = _get_bool_env("LLM_FALLBACK_ENABLED", False)
    LLM_FALLBACK_PROVIDER: str = _get_env("LLM_FALLBACK_PROVIDER", "openai")
    LLM_FALLBACK_API_KEY: str = _get_env("LLM_FALLBACK_API_KEY", "")
    LLM_FALLBACK_BASE_URL: str = _get_env("LLM_FALLBACK_BASE_URL", "")
    LLM_FALLBACK_MODEL: str = _get_env("LLM_FALLBACK_MODEL", "gpt-4o-mini")
    SEARCH_ENABLED: bool = _get_bool_env("SEARCH_ENABLED", False)
    SEARCH_PROVIDER: str = _get_env("SEARCH_PROVIDER", "tavily")
    SEARCH_API_KEY: str = _get_env("SEARCH_API_KEY", "")
    SEARCH_TIMEOUT: int = int(_get_env("SEARCH_TIMEOUT", "8"))
    SEARCH_MAX_RESULTS: int = int(_get_env("SEARCH_MAX_RESULTS", "5"))
    SEARCH_ALLOWED_DOMAINS_RAW: str = _get_env("SEARCH_ALLOWED_DOMAINS", "")
    SEARCH_CACHE_TTL_SECONDS: int = int(_get_env("SEARCH_CACHE_TTL_SECONDS", "1800"))

    # Supabase Storage (for DALL-E image uploads)
    SUPABASE_URL: str = _get_env("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = _get_env("SUPABASE_SERVICE_ROLE_KEY", "")
    BACKEND_PUBLIC_BASE_URL: str = _get_env("BACKEND_PUBLIC_BASE_URL", "http://127.0.0.1:8000")


settings = Settings()


def get_cors_origins() -> list[str]:
    raw = settings.CORS_ORIGINS_RAW.strip()
    if raw == "*":
        return ["*"]
    if raw == "":
        # 未配置时默认只允许本地开发域名（生产环境需在 .env 显式设置 CORS_ORIGINS）
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [part.strip() for part in raw.split(",") if part.strip()]


def get_cors_allow_credentials() -> bool:
    """credentials=True 不能与 allow_origins=* 同时使用（浏览器拒绝）。"""
    origins = get_cors_origins()
    if origins == ["*"]:
        return False
    return settings.CORS_ALLOW_CREDENTIALS


def get_search_allowed_domains() -> list[str]:
    raw = settings.SEARCH_ALLOWED_DOMAINS_RAW.strip()
    if raw == "":
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]
