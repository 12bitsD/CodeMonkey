"""
Application configuration for the PathFinder API.

All runtime settings are read from environment variables at import time and
stored in the immutable ``Settings`` dataclass.  Import ``settings`` anywhere
in the codebase to access a value — never call ``os.getenv()`` directly in
other modules.

Quick reference — environment variables
---------------------------------------

=========================  ==============================================
Variable                   Purpose
=========================  ==============================================
APP_NAME                   API display name (default: "PathFinder API")
APP_VERSION                Semver string (default: "1.0.0")
DEBUG                      Enable debug mode (default: true)
DATABASE_URL               PostgreSQL connection string (required)
DATABASE_SCHEMA            Optional schema name for search_path
JWT_SECRET_KEY             HMAC secret — **change before deploying**
JWT_ALGORITHM              JWT signing algorithm (default: HS256)
JWT_EXPIRE_DAYS            Token lifetime in days (default: 7)
CORS_ORIGINS               Comma-separated origins or "*" (default: "*")
CORS_ALLOW_CREDENTIALS     Allow cookies in cross-origin requests
LLM_PROVIDER               Primary LLM provider (default: "kimi")
LLM_API_KEY                API key for the primary LLM
LLM_BASE_URL               Base URL for the primary LLM API
LLM_MODEL                  Model name (default: "kimi-k2-5")
LLM_TIMEOUT                Request timeout in seconds (default: 30)
LLM_MAX_RETRIES            Retry attempts on transient errors (default: 3)
LLM_TEMPERATURE            Sampling temperature 0–1 (default: 0.7)
LLM_FALLBACK_ENABLED       Enable fallback LLM provider (default: true)
LLM_FALLBACK_PROVIDER      Fallback provider name (default: "openai")
LLM_FALLBACK_API_KEY       API key for the fallback provider
LLM_FALLBACK_BASE_URL      Base URL for the fallback provider
LLM_FALLBACK_MODEL         Fallback model (default: "gpt-4o-mini")
=========================  ==============================================

Security note
-------------
The default ``JWT_SECRET_KEY`` is a placeholder.  Set a strong random
value via the environment variable before deploying to production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Environment-variable helpers
# ---------------------------------------------------------------------------


def _get_env(name: str, default: str = "") -> str:
    """Return the value of an environment variable, or ``default`` if absent.

    Treats an empty string (``""``) the same as a missing variable, so that
    ``VAR=`` in a ``.env`` file falls back to the default rather than
    silently passing an empty string to consumers.

    Args:
        name: The environment variable name (case-sensitive).
        default: Value to return when the variable is unset or empty.

    Returns:
        The variable's value as a string, or ``default``.
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_bool_env(name: str, default: bool) -> bool:
    """Return the boolean interpretation of an environment variable.

    Accepts ``"1"``, ``"true"``, ``"yes"``, ``"y"``, or ``"on"``
    (case-insensitive) as truthy values.  Any other non-empty value is
    treated as ``False``.  Unset or empty variables fall back to ``default``.

    Args:
        name: The environment variable name.
        default: Value to return when the variable is unset or empty.

    Returns:
        ``True`` if the raw value is a recognised truthy string, ``False`` otherwise.
    """
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of all application configuration, read at startup.

    Using a frozen dataclass guarantees that no module can accidentally
    mutate a setting after the application boots.  All values are sourced
    from environment variables with sensible development defaults.

    Attributes:
        APP_NAME: Human-readable API name shown in logs and the OpenAPI UI.
        APP_VERSION: Semantic version string, surfaced in the ``/`` endpoint.
        DEBUG: When ``True``, FastAPI returns detailed error tracebacks.

        DATABASE_URL: PostgreSQL connection string (required for startup).
        DATABASE_SCHEMA: PostgreSQL schema name appended to ``search_path``.
            Leave empty to use the database's default schema.

        JWT_SECRET_KEY: HMAC secret used to sign and verify JWTs.
            **Must** be replaced with a strong random value in production.
        JWT_ALGORITHM: Signing algorithm (default: ``"HS256"``).
        JWT_EXPIRE_DAYS: Number of days before an issued token expires.

        CORS_ORIGINS_RAW: Raw comma-separated string from the environment.
            Use ``get_cors_origins()`` to get a parsed list.
        CORS_ALLOW_CREDENTIALS: Whether to allow cookies in cross-origin
            requests.  Must be ``False`` when ``CORS_ORIGINS`` is ``"*"``.

        LLM_PROVIDER: Identifier for the primary LLM integration (e.g. ``"kimi"``).
        LLM_API_KEY: API key for the primary LLM provider.
        LLM_BASE_URL: Base URL for the primary LLM API.
        LLM_MODEL: Model name to request from the primary provider.
        LLM_TIMEOUT: Seconds before an LLM request is abandoned.
        LLM_MAX_RETRIES: Retry budget for transient LLM errors.
        LLM_TEMPERATURE: Sampling randomness (0 = deterministic, 1 = creative).

        LLM_FALLBACK_ENABLED: Whether to retry failed LLM calls via the
            fallback provider.
        LLM_FALLBACK_PROVIDER: Name of the fallback LLM provider.
        LLM_FALLBACK_API_KEY: API key for the fallback provider.
        LLM_FALLBACK_BASE_URL: Base URL for the fallback provider.
        LLM_FALLBACK_MODEL: Model name to use with the fallback provider.
    """

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


# ---------------------------------------------------------------------------
# Helpers for consuming settings
# ---------------------------------------------------------------------------


def get_cors_origins() -> list[str]:
    """Parse ``settings.CORS_ORIGINS_RAW`` into a list for FastAPI's CORS middleware.

    A raw value of ``"*"`` or an empty string allows all origins.  Otherwise
    the value is split on commas and each part is stripped of surrounding
    whitespace.

    Returns:
        ``["*"]`` to allow all origins, or a list of specific origin URLs.

    Examples:
        >>> get_cors_origins()  # CORS_ORIGINS="*"
        ['*']
        >>> get_cors_origins()  # CORS_ORIGINS="http://localhost:3000,https://app.example.com"
        ['http://localhost:3000', 'https://app.example.com']
    """
    raw = settings.CORS_ORIGINS_RAW.strip()
    if raw == "*" or raw == "":
        return ["*"]
    return [part.strip() for part in raw.split(",") if part.strip()]
