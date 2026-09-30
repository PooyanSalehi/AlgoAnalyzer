"""Metadata endpoints: health, examples, projects and algorithms CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data.examples import EXAMPLE_PAIRS
from app.db import repositories as repo
from app.db.models import Algorithm, Project
from app.db.session import get_db
from app.schemas.analysis import (
    AlgorithmCreate,
    ExamplePair,
    ProjectCreate,
)

router = APIRouter(tags=["meta"])


@router.get("/health", summary="Service health check")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    db_ok = True
    try:
        db.execute(select(1))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": "connected" if db_ok else "unavailable",
    }


@router.get("/examples", response_model=list[ExamplePair], summary="Curated example comparisons")
def examples() -> list[dict]:
    return EXAMPLE_PAIRS


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
@router.get("/projects", summary="List projects")
def list_projects(db: Session = Depends(get_db)) -> list[dict]:
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    out = []
    for p in projects:
        out.append({
            "id": p.id, "name": p.name, "description": p.description,
            "created_at": p.created_at,
            "algorithm_count": len(p.algorithms),
            "analysis_count": len(p.analyses),
        })
    return out


@router.post("/projects", status_code=201, summary="Create a project")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> dict:
    user_project = repo.ensure_default_user_and_project(db)
    project = Project(user_id=user_project.user_id, name=payload.name,
                      description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description}


# --------------------------------------------------------------------------- #
# Algorithms
# --------------------------------------------------------------------------- #
@router.get("/algorithms", summary="List stored algorithms")
def list_algorithms(project_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(Algorithm).order_by(Algorithm.updated_at.desc())
    if project_id is not None:
        stmt = stmt.where(Algorithm.project_id == project_id)
    return [
        {"id": a.id, "project_id": a.project_id, "name": a.name, "mode": a.mode,
         "created_at": a.created_at, "updated_at": a.updated_at, "code": a.code}
        for a in db.scalars(stmt)
    ]


@router.post("/algorithms", status_code=201, summary="Store an algorithm")
def create_algorithm(payload: AlgorithmCreate, db: Session = Depends(get_db)) -> dict:
    project = repo.ensure_default_user_and_project(db)
    algo = repo.upsert_algorithm(db, project.id, payload.name, payload.mode.value, payload.code)
    db.commit()
    db.refresh(algo)
    return {"id": algo.id, "name": algo.name, "mode": algo.mode}


@router.delete("/algorithms/{algorithm_id}", status_code=204, summary="Delete an algorithm")
def delete_algorithm(algorithm_id: int, db: Session = Depends(get_db)) -> None:
    algo = db.get(Algorithm, algorithm_id)
    if algo is None:
        raise HTTPException(status_code=404, detail=f"Algorithm {algorithm_id} not found")
    db.delete(algo)
    db.commit()
