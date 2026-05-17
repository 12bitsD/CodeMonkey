from contextlib import asynccontextmanager
import json
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from psycopg2 import DataError, DatabaseError, IntegrityError, InterfaceError, OperationalError
from psycopg2.pool import PoolError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import get_cors_origins, get_cors_allow_credentials, settings
from database import SchemaNotReadyError, close_connection_pool, get_db_context
from routers import ai, auth, graph, notes, plans, stats, user
from utils.limiter import limiter
from utils.observability import (
    get_metrics_snapshot,
    record_db_error,
    record_request,
)

logger = logging.getLogger(__name__)

# 生产环境关闭 OpenAPI 文档（S12）
_docs_url = "/docs" if settings.DEBUG else None
_redoc_url = "/redoc" if settings.DEBUG else None
_openapi_url = "/openapi.json" if settings.DEBUG else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_connection_pool()

app = FastAPI(
    title="PathFinder API",
    description="Learning Path Planner Backend",
    version="1.0.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=get_cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_and_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    route = getattr(request.scope.get("route"), "path", request.url.path)
    record_request(request.method, route, response.status_code, duration_ms)
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "route": route,
                "statusCode": response.status_code,
                "durationMs": round(duration_ms, 2),
            },
            ensure_ascii=False,
        )
    )
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault(
        "Content-Security-Policy",
        (
            "default-src 'self'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' https:; "
            "connect-src 'self' http: https:"
        ),
    )
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    return response

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(graph.router)
app.include_router(plans.router)
app.include_router(notes.router)
app.include_router(stats.router)
app.include_router(ai.router)


def _default_error_code(status_code: int) -> str:
    if status_code == 400:
        return "BAD_REQUEST"
    if status_code == 401:
        return "UNAUTHORIZED"
    if status_code == 403:
        return "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    return "HTTP_ERROR"


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
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
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {"code": "BAD_REQUEST", "message": "请求参数错误"},
        },
    )


@app.exception_handler(SchemaNotReadyError)
async def schema_not_ready_exception_handler(request: Request, exc: SchemaNotReadyError):
    record_db_error("SCHEMA_NOT_READY")
    logger.warning("Database schema is not ready: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": "SCHEMA_NOT_READY",
                "message": "数据库结构尚未完成迁移，请先执行数据库 migration",
                "missingColumns": exc.missing_columns,
            },
        },
    )


@app.exception_handler(PoolError)
async def database_pool_exception_handler(request: Request, exc: PoolError):
    record_db_error("DATABASE_UNAVAILABLE")
    logger.warning("Database pool unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "数据库连接暂时不可用，请稍后重试",
            },
        },
    )


@app.exception_handler(OperationalError)
async def database_operational_exception_handler(request: Request, exc: OperationalError):
    record_db_error("DATABASE_UNAVAILABLE")
    logger.warning("Database operational error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "数据库暂时不可用，请稍后重试",
            },
        },
    )


@app.exception_handler(InterfaceError)
async def database_interface_exception_handler(request: Request, exc: InterfaceError):
    record_db_error("DATABASE_CONNECTION_LOST")
    logger.warning("Database interface error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_CONNECTION_LOST",
                "message": "数据库连接已中断，请稍后重试",
            },
        },
    )


@app.exception_handler(IntegrityError)
async def database_integrity_exception_handler(request: Request, exc: IntegrityError):
    record_db_error("DATABASE_CONFLICT")
    logger.warning("Database integrity error: %s", exc)
    return JSONResponse(
        status_code=409,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_CONFLICT",
                "message": "数据已发生变化，请刷新后重试",
            },
        },
    )


@app.exception_handler(DataError)
async def database_data_exception_handler(request: Request, exc: DataError):
    record_db_error("DATABASE_INVALID_DATA")
    logger.warning("Database data error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_INVALID_DATA",
                "message": "数据格式不合法，请检查后重试",
            },
        },
    )


@app.exception_handler(DatabaseError)
async def database_exception_handler(request: Request, exc: DatabaseError):
    record_db_error("DATABASE_ERROR")
    logger.exception("Database error")
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error": {
                "code": "DATABASE_ERROR",
                "message": "数据库请求失败，请稍后重试",
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"},
        },
    )



@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check():
    started = time.perf_counter()
    try:
        with get_db_context() as db:
            db.execute("SELECT 1").fetchone()
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        record_db_error("DATABASE_UNAVAILABLE")
        logger.warning(
            json.dumps(
                {
                    "event": "database_health_check",
                    "status": "degraded",
                    "database": "unavailable",
                    "latencyMs": latency_ms,
                    "errorType": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        )
        return {
            "status": "degraded",
            "database": "unavailable",
            "latencyMs": latency_ms,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return {"status": "ok", "database": "ok", "latencyMs": latency_ms}


@app.get("/health/metrics")
def health_metrics():
    return {"status": "ok", "metrics": get_metrics_snapshot()}


@app.get("/")
def root():
    return {"message": "PathFinder API", "docs": "/docs", "version": "1.0.0"}
