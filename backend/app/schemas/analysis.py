"""Pydantic schemas defining the public API contract of the analysis pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class InputMode(str, Enum):
    """Supported input formats."""

    python = "python"
    pseudocode = "pseudocode"
    natural = "natural"


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #
class AlgorithmInput(BaseModel):
    """One algorithm submission."""

    name: str | None = Field(default=None, max_length=128,
                              description="Display name, e.g. 'Merge Sort'")
    code: str = Field(..., min_length=1, max_length=100_000,
                      description="Source code, pseudocode or natural-language description")
    mode: InputMode = Field(default=InputMode.python)


class AnalyzeOptions(BaseModel):
    """Options controlling the analysis pipeline."""

    run_benchmarks: bool = True
    ai_provider: str = Field(default="heuristic", pattern="^(heuristic|openai)$")


class AnalyzeRequest(BaseModel):
    """Body of ``POST /api/analyze``."""

    algorithm_a: AlgorithmInput
    algorithm_b: AlgorithmInput
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions)


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
class ArgSummary(BaseModel):
    name: str
    kind: str
    annotation: str | None = None
    has_default: bool = False


class LoopSummary(BaseModel):
    kind: str
    depth: int
    bound: str
    line: int
    note: str


class AllocationSummary(BaseModel):
    kind: str
    size: str
    note: str


class FunctionSummary(BaseModel):
    """Parsed fingerprint of one function."""

    name: str
    args: list[ArgSummary]
    returns: list[str]
    loops: list[LoopSummary]
    max_loop_depth: int
    is_recursive: bool
    recursive_call_count: int
    recursion_shrink: str | None
    recursion_branching: int
    memoized: bool
    conditionals: int
    early_exit: bool
    allocations: list[AllocationSummary]
    builtin_calls: list[str]
    method_calls: list[str]
    data_structures: list[str]
    operations: dict[str, int]
    hints: list[str]
    notes: list[str] = []


class AlgorithmOverview(BaseModel):
    """Parser output for one algorithm."""

    name: str
    mode: InputMode
    line_count: int
    imports: list[str]
    functions: list[FunctionSummary]
    primary: str | None
    purpose: str
    confidence: float
    warnings: list[str]


class TimeComplexity(BaseModel):
    best: str
    average: str
    worst: str
    best_rank: int
    average_rank: int
    worst_rank: int
    pattern: str
    recurrence: str | None = None
    explanations: list[str]


class SpaceComplexity(BaseModel):
    auxiliary: str
    total: str
    recursion_depth: str | None = None
    explanations: list[str]


class AlgorithmComplexity(BaseModel):
    time: TimeComplexity
    space: SpaceComplexity


class ComplexityComparisonRow(BaseModel):
    """One row of the headline comparison table."""

    metric: str
    a: str
    b: str


class SimilarityFeature(BaseModel):
    feature: str
    score: float
    weight: float
    detail: str


class SimilarityReportModel(BaseModel):
    score: float
    band: str
    summary: str
    features: list[SimilarityFeature]


class FunctionalReportModel(BaseModel):
    equivalent: bool
    verdict: str
    confidence: float
    purpose_a: str
    purpose_b: str
    input_analysis: str
    output_analysis: str
    operation_analysis: str
    reasoning: list[str]
    empirical_output_match: bool | None = None
    empirical_samples: int = 0


class BenchmarkPointModel(BaseModel):
    n: int
    time_ms: float | None = None
    memory_kb: float | None = None
    error: str | None = None


class AlgorithmBenchmarkModel(BaseModel):
    name: str
    status: str
    points: list[BenchmarkPointModel]
    notes: list[str]


class BenchmarkReportModel(BaseModel):
    status: str
    a: AlgorithmBenchmarkModel
    b: AlgorithmBenchmarkModel
    output_agreement: bool | None = None
    agreement_samples: int = 0
    comparison: list[dict] = []
    notes: list[str]


class GrowthPoint(BaseModel):
    """Theoretical operation count at input size n (worst-case model)."""

    n: int
    a: float
    b: float


class AnalysisResult(BaseModel):
    """Full analysis response returned by ``POST /api/analyze``."""

    analysis_id: int | None = None
    created_at: datetime
    a: dict  # {overview, complexity}
    b: dict
    complexity_table: list[ComplexityComparisonRow]
    similarity: SimilarityReportModel
    functional: FunctionalReportModel
    benchmark: BenchmarkReportModel
    growth: list[GrowthPoint]
    growth_labels: dict[str, str]
    explanation: str
    explanation_provider: str
    report_markdown: str
    warnings: list[str] = []


# --------------------------------------------------------------------------- #
# History / persistence
# --------------------------------------------------------------------------- #
class AnalysisRunSummary(BaseModel):
    """History list entry."""

    id: int
    created_at: datetime
    algorithm_a_name: str
    algorithm_b_name: str
    similarity_score: float | None
    functional_verdict: str | None


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None


class AlgorithmCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    mode: InputMode = InputMode.python
    code: str = Field(..., min_length=1)


class ExampleAlgorithm(BaseModel):
    name: str
    code: str
    mode: InputMode


class ExamplePair(BaseModel):
    """A curated example comparison."""

    id: str
    title: str
    description: str
    a: ExampleAlgorithm
    b: ExampleAlgorithm
