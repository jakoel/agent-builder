"""Agent Builder Platform -- FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import agents, builder, models, runs, tool_library


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create required storage directories on startup."""
    (settings.STORAGE_PATH / "agents").mkdir(parents=True, exist_ok=True)
    (settings.STORAGE_PATH / "runs").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Agent Builder Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(agents.router)
app.include_router(builder.router)
app.include_router(runs.router)
app.include_router(models.router)
app.include_router(tool_library.router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "name": "Agent Builder Platform"}
