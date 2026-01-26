from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "PathFinder API", "docs": "/docs", "version": "1.0.0"}
