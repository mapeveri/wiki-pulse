"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .routers import metrics

settings = Settings.from_env()

app = FastAPI(
    title="WikiPulse API",
    version="0.1.0",
    description="Audience and content analytics for a curated set of topics.",
)

origins = (
    ["*"]
    if settings.cors_origins == "*"
    else [origin.strip() for origin in settings.cors_origins.split(",")]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(metrics.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": "WikiPulse API", "version": app.version}


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    from .db import query

    query("select 1")
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
