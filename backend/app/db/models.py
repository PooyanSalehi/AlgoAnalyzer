"""Database models for AlgoAnalyzer.

Entity relationships::

    User 1──* Project 1──* Algorithm
                     └──* AnalysisRun *──1 Algorithm (a)   ┐ references
                                     *──1 Algorithm (b)   ┘ algorithms
                AnalysisRun 1──* Report
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp helper."""
    return datetime.now(timezone.utc)


class User(Base):
    """A platform user. The API ships a lightweight 'demo' user flow."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """A named collection of algorithms and analyses (workspace)."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")
    algorithms: Mapped[list["Algorithm"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    analyses: Mapped[list["AnalysisRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Algorithm(Base):
    """A stored algorithm submission (source code + input mode)."""

    __tablename__ = "algorithms"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_algorithm_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(16), default="python")  # python | pseudocode | natural
    code: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="algorithms")


class AnalysisRun(Base):
    """One execution of the full analysis pipeline (immutable history entry)."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    algorithm_a_id: Mapped[int | None] = mapped_column(ForeignKey("algorithms.id"), nullable=True)
    algorithm_b_id: Mapped[int | None] = mapped_column(ForeignKey("algorithms.id"), nullable=True)

    algorithm_a_name: Mapped[str] = mapped_column(String(128), default="Algorithm A")
    algorithm_b_name: Mapped[str] = mapped_column(String(128), default="Algorithm B")

    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    functional_verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)

    request_json: Mapped[str] = mapped_column(Text)   # raw AnalyzeRequest payload
    result_json: Mapped[str] = mapped_column(Text)    # full AnalysisResult payload
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="analyses")
    reports: Mapped[list["Report"]] = relationship(back_populates="analysis_run", cascade="all, delete-orphan")


class Report(Base):
    """A generated (downloadable) analysis report."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    format: Mapped[str] = mapped_column(String(16), default="markdown")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis_run: Mapped["AnalysisRun"] = relationship(back_populates="reports")
