"""
PathFinder API — Application entry point.

This module assembles the FastAPI application: it registers all routers,
configures CORS middleware, and installs three global exception handlers
that normalize every error response into a consistent JSON envelope::

    {"success": false, "error": {"code": "...", "message": "..."}}

A new developer should start here to understand the full request lifecycle.
To add a feature, import its router and call ``app.include_router()`` below.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from config import get_cors_origins, settings
from routers import ai, auth, graph, notes, plans, stats, user

app = FastAPI(
    title="PathFinder API",
    description="Learning Path Planner Backend",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(graph.router)
app.include_router(plans.router)
app.include_router(notes.router)
app.include_router(stats.router)
app.include_router(ai.router)


# ---------------------------------------------------------------------------
# Error-response helpers
# ---------------------------------------------------------------------------


def _default_error_code(status_code: int) -> str:
    """Return a machine-readable error code for common HTTP status codes.

    Used as a fallback when the raised ``HTTPException`` does not already
    carry a structured ``code`` field in its detail.

    Args:
        status_code: The HTTP numeric status code (e.g. 404).

    Returns:
        A short uppercase string such as ``"NOT_FOUND"``, or ``"HTTP_ERROR"``
        for codes not explicitly mapped.
    """
    if status_code == 400:
        return "BAD_REQUEST"
    if status_code == 401:
        return "UNAUTHORIZED"
    if status_code == 403:
        return "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    return "HTTP_ERROR"


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
# All three handlers return the same JSON shape, so clients need only one
# error-parsing branch:
#   {"success": false, "error": {"code": "<UPPER_SNAKE>", "message": "<text>"}}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Convert any ``HTTPException`` into the standard error envelope.

    Routers may raise ``HTTPException`` with either a plain-string detail or
    a structured dict.  This handler normalises both forms.

    Accepted ``detail`` shapes:

    - ``str`` — used directly as the message.
    - ``{"code": ..., "message": ...}`` — fields extracted directly.
    - ``{"error": {"code": ..., "message": ...}}`` — nested error object extracted.

    Args:
        request: The incoming FastAPI request (required by the handler signature).
        exc: The raised ``HTTPException``.

    Returns:
        A ``JSONResponse`` with the original status code and a normalised body.
    """
    detail = exc.detail
    code = _default_error_code(exc.status_code)
    message = "请求失败"

    if isinstance(detail, dict):
        if "error" in detail and isinstance(detail.get("error"), dict):
            error = detail["error"]
            code = error.get("code", code)
            message = error.get("message", message)
        else:
            code = detail.get("code", code)
            message = detail.get("message", message)
    elif isinstance(detail, str) and detail.strip():
        message = detail

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a 400 error when request body or query parameters fail Pydantic validation.

    Raw Pydantic error details are intentionally suppressed to avoid leaking
    internal field names to API consumers.

    Args:
        request: The incoming FastAPI request.
        exc: The Pydantic ``RequestValidationError``.

    Returns:
        A ``JSONResponse`` with status 400 and a ``BAD_REQUEST`` error envelope.
    """
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {"code": "BAD_REQUEST", "message": "请求参数错误"},
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for any unhandled exception, returning a 500 response.

    Prevents FastAPI from leaking stack traces to API consumers in production.
    Actual error details should be captured via server-side logging.

    Args:
        request: The incoming FastAPI request.
        exc: Any unhandled ``Exception``.

    Returns:
        A ``JSONResponse`` with status 500 and an ``INTERNAL_ERROR`` envelope.
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
        },
    )


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check():
    """Liveness probe used by load balancers and container orchestrators.

    Returns:
        A JSON object ``{"status": "ok"}`` when the server is running.
    """
    return {"status": "ok"}


@app.get("/")
def root():
    """Root endpoint returning basic API identification information.

    Returns:
        A JSON object with the API name, interactive docs URL, and version string.
    """
    return {"message": "PathFinder API", "docs": "/docs", "version": "1.0.0"}
