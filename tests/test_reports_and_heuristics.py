"""Tests for the pseudocode / natural-language backends, report generator
and the heuristic AI explainer."""
from __future__ import annotations

from app.services.ai.heuristic_explainer import HeuristicExplainer
from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import InputMode
from app.services.reports.generator import ReportGenerator, ReportInputs


class TestPseudocodeParser:
    def test_merge_sort_pseudocode(self):
        code = """
FUNCTION MergeSort(A)
    IF length(A) <= 1 THEN
        RETURN A
    END IF
    mid <- length(A) / 2
    left <- MergeSort(A[1..mid])
    right <- MergeSort(A[mid+1..length(A)])
    RETURN Merge(left, right)
END FUNCTION
"""
        ir = AlgorithmParser().parse(code, "Pseudo", InputMode.PSEUDOCODE)
        fn = ir.primary
        assert fn.is_recursive
        assert fn.recursion_shrink == "half"
        assert ir.confidence < 1.0

    def test_nested_pseudocode_loops(self):
        code = """
FUNCTION BubbleSort(A)
    n <- length(A)
    FOR i FROM 0 TO n-1 DO
        FOR j FROM 0 TO n-i-2 DO
            IF A[j] > A[j+1] THEN
                swap A[j] and A[j+1]
            END IF
        END FOR
    END FOR
END FUNCTION
"""
        ir = AlgorithmParser().parse(code, "Pseudo", InputMode.PSEUDOCODE)
        assert ir.primary.max_loop_depth == 2
        assert all(l.bound.value == "n" for l in ir.primary.loops)

    def test_constant_pseudocode_bound(self):
        code = """
FUNCTION X(A)
    FOR i FROM 1 TO 10 DO
        process A[i]
    END FOR
END FUNCTION
"""
        ir = AlgorithmParser().parse(code, "P", InputMode.PSEUDOCODE)
        assert ir.primary.loops[0].bound.value == "constant"


class TestNaturalLanguageParser:
    def test_stated_complexity_extracted(self):
        text = ("Merge sort recursively splits the array in half and merges sorted halves. "
                "It always runs in n log n time and needs a temporary array of size n.")
        ir = AlgorithmParser().parse(text, "Merge Sort", InputMode.NATURAL)
        assert ir.primary.estimated_time is not None
        assert ir.primary.estimated_time["worst"] == "n_log_n"

    def test_degrades_to_quadratic(self):
        text = ("Quick sort partitions around a pivot and recurses. On average it runs in "
                "n log n time, but in the worst case it degrades to n squared.")
        ir = AlgorithmParser().parse(text, "Quick Sort", InputMode.NATURAL)
        est = ir.primary.estimated_time
        assert est["average"] == "n_log_n"
        assert est["worst"] == "quadratic"

    def test_in_place_memory_wording(self):
        text = ("Quick sort partitions in place; it uses little extra memory.")
        ir = AlgorithmParser().parse(text, "Quick Sort", InputMode.NATURAL)
        assert ir.primary.allocations == []

    def test_low_confidence_flagged(self):
        ir = AlgorithmParser().parse("A sorting algorithm.", "S", InputMode.NATURAL)
        assert ir.confidence <= 0.5
        assert any("approximate" in w.lower() for w in ir.warnings)


class TestReportAndExplainer:
    def _inputs(self, run_service):
        result = run_service(
            "def sort_a(arr):\n    return sorted(arr)\n",
            "def sort_b(arr):\n    arr.sort()\n    return arr\n",
            "Sorted Copy", "In-Place Sort", benchmarks=False,
        )
        from app.services.parser.facade import AlgorithmParser
        from app.services.complexity.analyzer import ComplexityAnalyzer
        from app.services.similarity.engine import SimilarityEngine
        from app.services.functional.analyzer import FunctionalAnalyzer

        parser = AlgorithmParser()
        ir_a = parser.parse("def sort_a(arr):\n    return sorted(arr)\n", "sort_a", InputMode.PYTHON)
        ir_b = parser.parse("def sort_b(arr):\n    arr.sort()\n    return arr\n", "sort_b", InputMode.PYTHON)
        c_a, c_b = ComplexityAnalyzer().analyze(ir_a), ComplexityAnalyzer().analyze(ir_b)
        sim = SimilarityEngine().compare(ir_a, ir_b, c_a, c_b)
        func = FunctionalAnalyzer().compare(ir_a, ir_b, c_a, c_b, sim.score)
        from app.services.benchmark.engine import AlgorithmBenchmark, BenchmarkReport
        bench = BenchmarkReport(
            status="skipped",
            a=AlgorithmBenchmark("A", "skipped", notes=["n/a"]),
            b=AlgorithmBenchmark("B", "skipped", notes=["n/a"]),
        )
        return ReportInputs(ir_a=ir_a, ir_b=ir_b, complexity_a=c_a, complexity_b=c_b,
                            functional=func, similarity=sim, benchmark=bench,
                            explanation=HeuristicExplainer().explain(
                                ReportInputs(ir_a=ir_a, ir_b=ir_b, complexity_a=c_a,
                                             complexity_b=c_b, functional=func, similarity=sim,
                                             benchmark=bench, explanation="")))

    def test_report_sections(self, run_service):
        data = self._inputs(run_service)
        markdown = ReportGenerator().generate(data)
        for section in ("1. Algorithm Overview", "2. Functional Comparison",
                        "3. Complexity Comparison", "4. Benchmark Results",
                        "5. Mathematical Explanation", "6. AI Summary", "7. Final Summary"):
            assert section in markdown

    def test_heuristic_explainer_produces_prose(self, run_service):
        data = self._inputs(run_service)
        text = HeuristicExplainer().explain(data)
        assert len(text) > 200
        assert "sort_a" in text and "sort_b" in text
        assert "O(n log n)" in text
