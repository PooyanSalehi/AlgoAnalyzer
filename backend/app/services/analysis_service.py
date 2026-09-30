"""Analysis orchestrator — wires the pipeline stages together.

Pipeline::

    parse A ┐
            ├─► complexity ─► similarity ─► functional ─┐
    parse B ┘                                            ├─► AI explanation ─► report
                                benchmarks ─────────────┘

The service is intentionally *pure* (no database, no HTTP concerns); the
API layer handles persistence. This keeps every stage unit-testable and
the data flow easy to explain academically.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.schemas.analysis import (
    AlgorithmBenchmarkModel,
    AlgorithmComplexity,
    AlgorithmOverview,
    AllocationSummary,
    AnalysisResult,
    AnalyzeRequest,
    ArgSummary,
    BenchmarkPointModel,
    BenchmarkReportModel,
    ComplexityComparisonRow,
    FunctionSummary,
    FunctionalReportModel,
    GrowthPoint,
    LoopSummary,
    SimilarityFeature,
    SimilarityReportModel,
    SpaceComplexity,
    TimeComplexity,
)
from app.services.ai.base import get_explainer
from app.services.benchmark.engine import BenchmarkEngine
from app.services.complexity.analyzer import ComplexityAnalyzer
from app.services.complexity.classes import ComplexityClass
from app.services.functional.analyzer import FunctionalAnalyzer
from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import AlgorithmIR, InputMode
from app.services.reports.generator import ReportGenerator, ReportInputs
from app.services.similarity.engine import SimilarityEngine

#: Input sizes used for the theoretical growth-chart series.
GROWTH_SIZES = [4, 8, 16, 32, 64, 128, 256, 512, 1024]


class AnalysisService:
    """Executes the full analysis pipeline for a pair of algorithms."""

    def __init__(self) -> None:
        self.parser = AlgorithmParser()
        self.complexity = ComplexityAnalyzer()
        self.functional = FunctionalAnalyzer()
        self.similarity = SimilarityEngine()
        self.benchmark = BenchmarkEngine()
        self.reports = ReportGenerator()

    # ------------------------------------------------------------------ parse
    def _overview(self, ir: AlgorithmIR, purpose: str) -> AlgorithmOverview:
        from app.services.parser.models import FunctionIR

        def function_summary(fn: FunctionIR) -> FunctionSummary:
            return FunctionSummary(
                name=fn.name,
                args=[ArgSummary(name=a.name, kind=a.kind, annotation=a.annotation,
                                 has_default=a.has_default) for a in fn.args],
                returns=fn.returns,
                loops=[LoopSummary(kind=l.kind, depth=l.depth, bound=l.bound.value,
                                   line=l.line, note=l.note) for l in fn.loops],
                max_loop_depth=fn.max_loop_depth,
                is_recursive=fn.is_recursive,
                recursive_call_count=fn.recursive_call_count,
                recursion_shrink=fn.recursion_shrink,
                recursion_branching=fn.recursion_branching,
                memoized=fn.memoized,
                conditionals=fn.conditionals,
                early_exit=fn.early_exit,
                allocations=[AllocationSummary(kind=a.kind, size=a.size, note=a.note)
                             for a in fn.allocations],
                builtin_calls=fn.builtin_calls,
                method_calls=fn.method_calls,
                data_structures=fn.data_structures,
                operations=fn.operations,
                hints=sorted(fn.hints),
                notes=fn.notes,
            )

        return AlgorithmOverview(
            name=ir.name,
            mode=ir.mode,
            line_count=ir.line_count,
            imports=ir.imports,
            functions=[function_summary(f) for f in ir.functions],
            primary=ir.primary.name if ir.primary else None,
            purpose=purpose,
            confidence=ir.confidence,
            warnings=ir.warnings,
        )

    @staticmethod
    def _complexity_model(report) -> AlgorithmComplexity:
        return AlgorithmComplexity(
            time=TimeComplexity(
                best=report.time.best.label,
                average=report.time.average.label,
                worst=report.time.worst.label,
                best_rank=report.time.best.rank,
                average_rank=report.time.average.rank,
                worst_rank=report.time.worst.rank,
                pattern=report.pattern,
                recurrence=report.recurrence,
                explanations=report.explanations,
            ),
            space=SpaceComplexity(
                auxiliary=report.space.auxiliary.label,
                total=report.space.total.label,
                recursion_depth=report.space.recursion_depth.label
                if report.space.recursion_depth else None,
                explanations=report.space.explanations,
            ),
        )

    # ---------------------------------------------------------------- analyze
    def analyze(self, request: AnalyzeRequest) -> AnalysisResult:
        a_in, b_in = request.algorithm_a, request.algorithm_b

        # 1. Parse ----------------------------------------------------------
        ir_a = self.parser.parse(a_in.code, a_in.name or "Algorithm A", InputMode(a_in.mode))
        ir_b = self.parser.parse(b_in.code, b_in.name or "Algorithm B", InputMode(b_in.mode))

        # 2. Complexity ------------------------------------------------------
        comp_a = self.complexity.analyze(ir_a)
        comp_b = self.complexity.analyze(ir_b)

        # 3. Similarity (before functional, which consumes the score) ----------
        similarity = self.similarity.compare(ir_a, ir_b, comp_a, comp_b)

        # 4. Functional equivalence --------------------------------------------
        functional = self.functional.compare(ir_a, ir_b, comp_a, comp_b, similarity.score)

        # 5. Benchmarks -----------------------------------------------------------
        benchmark_report = None
        if request.options.run_benchmarks:
            benchmark_report = self.benchmark.run(ir_a, ir_b, comp_a, comp_b)
            # Feed empirical evidence back into the functional verdict.
            functional.empirical_output_match = benchmark_report.output_agreement
            functional.empirical_samples = benchmark_report.agreement_samples
            if benchmark_report.output_agreement and not functional.equivalent:
                # Executing both algorithms on shared inputs produced identical
                # outputs — execution evidence overrides keyword classification.
                functional.equivalent = True
                functional.verdict = ("Functionally equivalent — verified empirically "
                                      "(identical outputs on shared random inputs)")
                functional.reasoning.append(
                    "Although keyword classification suggested different purposes, running both "
                    f"algorithms on {benchmark_report.agreement_samples} identical random inputs "
                    "produced exactly the same outputs — they compute the same function."
                )
            elif benchmark_report.output_agreement is False and functional.equivalent:
                functional.reasoning.append(
                    "⚠️ Empirical check: the algorithms produced different outputs on random "
                    "inputs — verify their preconditions (e.g. binary search requires sorted "
                    "input) before treating them as interchangeable."
                )

        # 6. AI explanation ---------------------------------------------------------
        explainer = get_explainer(request.options.ai_provider or get_settings().ai_provider)
        report_inputs = ReportInputs(
            ir_a=ir_a, ir_b=ir_b,
            complexity_a=comp_a, complexity_b=comp_b,
            functional=functional, similarity=similarity,
            benchmark=benchmark_report or self._empty_benchmark(),
            explanation="",
        )
        explanation = explainer.explain(report_inputs)
        report_inputs.explanation = explanation

        # 7. Report -----------------------------------------------------------------
        markdown = self.reports.generate(report_inputs)

        # 8. Growth series for charts -------------------------------------------------
        growth = [
            GrowthPoint(
                n=n,
                a=round(comp_a.time.worst.growth(n), 2),
                b=round(comp_b.time.worst.growth(n), 2),
            )
            for n in GROWTH_SIZES
        ]

        # 9. Assemble response ----------------------------------------------------------
        purpose_a = functional.purpose_a
        purpose_b = functional.purpose_b
        warnings = list(ir_a.warnings) + list(ir_b.warnings)

        benchmark_model = self._benchmark_model(benchmark_report) if benchmark_report \
            else self._benchmark_model(self._empty_benchmark())

        return AnalysisResult(
            analysis_id=None,
            created_at=datetime.now(timezone.utc),
            a={"overview": self._overview(ir_a, purpose_a).model_dump(),
               "complexity": self._complexity_model(comp_a).model_dump()},
            b={"overview": self._overview(ir_b, purpose_b).model_dump(),
               "complexity": self._complexity_model(comp_b).model_dump()},
            complexity_table=[
                ComplexityComparisonRow(metric="Time — Best", a=comp_a.time.best.label,
                                        b=comp_b.time.best.label),
                ComplexityComparisonRow(metric="Time — Average", a=comp_a.time.average.label,
                                        b=comp_b.time.average.label),
                ComplexityComparisonRow(metric="Time — Worst", a=comp_a.time.worst.label,
                                        b=comp_b.time.worst.label),
                ComplexityComparisonRow(metric="Space — Auxiliary", a=comp_a.space.auxiliary.label,
                                        b=comp_b.space.auxiliary.label),
                ComplexityComparisonRow(metric="Space — Total (incl. input)",
                                        a=comp_a.space.total.label, b=comp_b.space.total.label),
            ],
            similarity=SimilarityReportModel(
                score=similarity.score,
                band=similarity.band,
                summary=similarity.summary,
                features=[SimilarityFeature(feature=f.feature, score=round(f.score, 3),
                                            weight=f.weight, detail=f.detail)
                          for f in similarity.features],
            ),
            functional=FunctionalReportModel(**functional.__dict__),
            benchmark=benchmark_model,
            growth=growth,
            growth_labels={"a": comp_a.time.worst.label, "b": comp_b.time.worst.label},
            explanation=explanation,
            explanation_provider=explainer.name,
            report_markdown=markdown,
            warnings=warnings,
        )

    @staticmethod
    def _empty_benchmark():
        from app.services.benchmark.engine import AlgorithmBenchmark, BenchmarkReport

        return BenchmarkReport(
            status="skipped",
            a=AlgorithmBenchmark("A", "skipped", notes=["Benchmarks were disabled for this run."]),
            b=AlgorithmBenchmark("B", "skipped", notes=["Benchmarks were disabled for this run."]),
            notes=["Benchmarks were disabled for this run."],
        )

    @staticmethod
    def _benchmark_model(report) -> BenchmarkReportModel:
        return BenchmarkReportModel(
            status=report.status,
            a=AlgorithmBenchmarkModel(
                name=report.a.name, status=report.a.status, notes=report.a.notes,
                points=[BenchmarkPointModel(n=p.n, time_ms=p.time_ms,
                                            memory_kb=p.memory_kb, error=p.error)
                        for p in report.a.points],
            ),
            b=AlgorithmBenchmarkModel(
                name=report.b.name, status=report.b.status, notes=report.b.notes,
                points=[BenchmarkPointModel(n=p.n, time_ms=p.time_ms,
                                            memory_kb=p.memory_kb, error=p.error)
                        for p in report.b.points],
            ),
            output_agreement=report.output_agreement,
            agreement_samples=report.agreement_samples,
            comparison=report.comparison,
            notes=report.notes,
        )
