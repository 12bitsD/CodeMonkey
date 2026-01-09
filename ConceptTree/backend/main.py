from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_database
from routers import graph, plans, notes, stats

app = FastAPI(
    title="PathFinder API",
    description="Learning Path Planner Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph.router)
app.include_router(plans.router)
app.include_router(notes.router)
app.include_router(stats.router)


@app.on_event("startup")
def startup():
    init_database()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "message": "PathFinder API",
        "docs": "/docs",
        "version": "1.0.0"
    }
