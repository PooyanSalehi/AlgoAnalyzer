"""Data-access helpers (repository pattern) used by the API routes.

Keeping persistence out of the analysis services makes the pipeline pure
and therefore trivially unit-testable.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Algorithm, AnalysisRun, Project, Report, User

DEFAULT_USERNAME = "demo"


def ensure_default_user_and_project(db: Session) -> Project:
    """Return the auto-provisioned demo workspace, creating it if needed."""
    user = db.scalar(select(User).where(User.username == DEFAULT_USERNAME))
    if user is None:
        user = User(username=DEFAULT_USERNAME, email="demo@algoanalyzer.local")
        db.add(user)
        db.flush()

    project = db.scalar(
        select(Project).where(Project.user_id == user.id, Project.name == "Playground")
    )
    if project is None:
        project = Project(user_id=user.id, name="Playground",
                          description="Default workspace created by AlgoAnalyzer.")
        db.add(project)
        db.flush()
    return project


def save_analysis_run(
    db: Session,
    project_id: int,
    request_payload: dict,
    result_payload: dict,
    report_markdown: str,
    algorithm_a_id: int | None = None,
    algorithm_b_id: int | None = None,
) -> AnalysisRun:
    """Persist one analysis run together with its markdown report."""
    similarity = result_payload.get("similarity", {})
    functional = result_payload.get("functional", {})
    run = AnalysisRun(
        project_id=project_id,
        algorithm_a_id=algorithm_a_id,
        algorithm_b_id=algorithm_b_id,
        algorithm_a_name=result_payload.get("a", {}).get("overview", {}).get("name", "Algorithm A"),
        algorithm_b_name=result_payload.get("b", {}).get("overview", {}).get("name", "Algorithm B"),
        similarity_score=similarity.get("score"),
        functional_verdict=functional.get("verdict"),
        request_json=json.dumps(request_payload),
        result_json=json.dumps(result_payload),
    )
    db.add(run)
    db.flush()
    db.add(Report(analysis_run_id=run.id, format="markdown", content=report_markdown))
    db.commit()
    db.refresh(run)
    return run


def upsert_algorithm(db: Session, project_id: int, name: str, mode: str, code: str) -> Algorithm:
    """Insert or update an algorithm inside a project (idempotent by name)."""
    algo = db.scalar(
        select(Algorithm).where(Algorithm.project_id == project_id, Algorithm.name == name)
    )
    if algo is None:
        algo = Algorithm(project_id=project_id, name=name, mode=mode, code=code)
        db.add(algo)
    else:
        algo.mode, algo.code = mode, code
    db.flush()
    return algo


def list_analysis_runs(db: Session, project_id: int | None = None, limit: int = 25) -> list[AnalysisRun]:
    """Most recent analysis runs, optionally filtered by project."""
    stmt = select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit)
    if project_id is not None:
        stmt = stmt.where(AnalysisRun.project_id == project_id)
    return list(db.scalars(stmt))


def get_analysis_run(db: Session, run_id: int) -> AnalysisRun | None:
    return db.get(AnalysisRun, run_id)


def get_report_for_run(db: Session, run_id: int) -> Report | None:
    return db.scalar(select(Report).where(Report.analysis_run_id == run_id))
