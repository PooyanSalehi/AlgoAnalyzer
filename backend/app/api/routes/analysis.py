"""Core analysis endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.errors import AlgoAnalyzerError, ParseError
from app.db import repositories as repo
from app.db.session import get_db
from app.schemas.analysis import AnalyzeRequest, AnalysisResult
from app.services.analysis_service import AnalysisService

router = APIRouter(tags=["analysis"])

#: Single shared service instance (stateless pipeline stages).
_analysis_service = AnalysisService()


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    responses={400: {"description": "Unparseable algorithm input"}},
    summary="Analyse and compare two algorithms",
)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalysisResult:
    """Run the full pipeline (parse → complexity → similarity → functional →
    benchmark → explanation → report) on a pair of algorithms and persist
    the run plus its report in the analysis history."""
    try:
        result = _analysis_service.analyze(request)
    except ParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AlgoAnalyzerError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - convert unexpected errors to 500 payload
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed unexpectedly: {exc}",
        ) from exc

    # --- persistence (best effort: never lose an analysis over a DB hiccup) ---
    try:
        project = repo.ensure_default_user_and_project(db)
        algo_a = repo.upsert_algorithm(
            db, project.id,
            result.a["overview"]["name"], request.algorithm_a.mode.value,
            request.algorithm_a.code,
        )
        algo_b = repo.upsert_algorithm(
            db, project.id,
            result.b["overview"]["name"], request.algorithm_b.mode.value,
            request.algorithm_b.code,
        )
        run = repo.save_analysis_run(
            db,
            project_id=project.id,
            request_payload=request.model_dump(mode="json"),
            result_payload=result.model_dump(mode="json"),
            report_markdown=result.report_markdown,
            algorithm_a_id=algo_a.id,
            algorithm_b_id=algo_b.id,
        )
        result.analysis_id = run.id
    except Exception:  # noqa: BLE001
        pass

    return result


@router.get(
    "/analyses",
    summary="List recent analysis runs (history)",
)
def list_analyses(limit: int = 25, db: Session = Depends(get_db)) -> list[dict]:
    runs = repo.list_analysis_runs(db, limit=limit)
    return [
        {
            "id": run.id,
            "created_at": run.created_at,
            "algorithm_a_name": run.algorithm_a_name,
            "algorithm_b_name": run.algorithm_b_name,
            "similarity_score": run.similarity_score,
            "functional_verdict": run.functional_verdict,
        }
        for run in runs
    ]


@router.get(
    "/analyses/{run_id}",
    response_model=AnalysisResult,
    summary="Fetch one stored analysis run",
)
def get_analysis(run_id: int, db: Session = Depends(get_db)) -> AnalysisResult:
    run = repo.get_analysis_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Analysis run {run_id} not found")
    return AnalysisResult.model_validate(json.loads(run.result_json))


@router.get(
    "/analyses/{run_id}/report",
    summary="Fetch the Markdown report of a stored analysis run",
)
def get_report(run_id: int, db: Session = Depends(get_db)) -> dict:
    report = repo.get_report_for_run(db, run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report for run {run_id} not found")
    return {"id": report.id, "analysis_run_id": report.analysis_run_id,
            "format": report.format, "content": report.content,
            "created_at": report.created_at}
