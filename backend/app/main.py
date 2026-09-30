"""AlgoAnalyzer backend — FastAPI application factory.

Run locally::

    uvicorn app.main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, meta
from app.core.config import get_settings
from app.core.errors import AlgoAnalyzerError
from app.db.session import init_db
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev convenience)."""
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description=(
            "Intelligent platform that analyses and compares two algorithms "
            "for functional equivalence, time/space complexity, empirical "
            "performance and conceptual similarity."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AlgoAnalyzerError)
    async def domain_error_handler(request, exc: AlgoAnalyzerError):  # noqa: ANN001
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(analysis.router, prefix=settings.api_prefix)
    app.include_router(meta.router, prefix=settings.api_prefix)

    @app.get("/", tags=["meta"], summary="Service banner")
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": settings.api_prefix,
        }

    return app


app = create_app()
