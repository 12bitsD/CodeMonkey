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

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
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


@app.get("/")
def root():
    return {"message": "PathFinder API", "docs": "/docs", "version": "1.0.0"}
