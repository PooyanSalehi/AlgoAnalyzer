"""Shared pytest fixtures for the AlgoAnalyzer test suite."""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Isolated throw-away database for every test run.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_algodata.db")


@pytest.fixture()
def analysis_service():
    """A fresh analysis pipeline (benchmarks enabled, fast ladders)."""
    from app.services.analysis_service import AnalysisService

    return AnalysisService()


@pytest.fixture()
def run_service(analysis_service):
    """Helper that runs a full analysis on two source strings."""

    def _run(code_a: str, code_b: str, name_a: str = "A", name_b: str = "B",
             benchmarks: bool = True, mode: str = "python"):
        from app.schemas.analysis import AlgorithmInput, AnalyzeRequest

        return analysis_service.analyze(AnalyzeRequest(
            algorithm_a=AlgorithmInput(name=name_a, code=code_a, mode=mode),
            algorithm_b=AlgorithmInput(name=name_b, code=code_b, mode=mode),
            options={"run_benchmarks": benchmarks},
        ))

    return _run


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    """FastAPI TestClient backed by a throw-away SQLite database."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    # Reset cached settings + engine so the new URL is picked up.
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.db.session as session_module

    engine = session_module._build_engine()
    monkeypatch.setattr(session_module, "engine", engine)
    monkeypatch.setattr(session_module, "SessionLocal",
                        __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
                            bind=engine, autoflush=False, autocommit=False))

    from app.main import app

    with TestClient(app) as client:
        yield client
    engine.dispose()
