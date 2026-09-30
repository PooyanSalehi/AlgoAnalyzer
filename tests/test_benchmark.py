"""Unit tests for the benchmark engine and its sandbox."""
from __future__ import annotations

from app.services.benchmark.engine import BenchmarkEngine, _infer_input_spec, _sizes_for
from app.services.complexity.analyzer import ComplexityAnalyzer
from app.services.complexity.classes import COMPLEXITY_CLASSES
from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import InputMode


def ir_for(code: str):
    return AlgorithmParser().parse(code, "T", InputMode.PYTHON)


class TestInputSpecInference:
    def test_list_only(self):
        ir = ir_for("def sort(arr):\n    return sorted(arr)\n")
        assert _infer_input_spec(ir)[0] == ["int_list"]

    def test_search_pair_gets_sorted_input(self):
        ir = ir_for("def binary_search(arr, target):\n    return arr.index(target)\n")
        assert _infer_input_spec(ir)[0] == ["int_list_sorted", "int_target"]

    def test_optional_args_ignored(self):
        ir = ir_for("def quick_sort(arr, low=0, high=None):\n    return arr\n")
        assert _infer_input_spec(ir)[0] == ["int_list"]

    def test_int_only(self):
        ir = ir_for("def fib(n):\n    return n\n")
        assert _infer_input_spec(ir)[0] == ["int"]

    def test_unsupported_signature(self):
        ir = ir_for("def weird(a, b, c):\n    return a\n")
        spec, error = _infer_input_spec(ir)
        assert spec == [] and error is not None

    def test_pseudocode_skipped(self):
        ir = AlgorithmParser().parse("FUNCTION X(A)\nEND FUNCTION", "T", InputMode.PSEUDOCODE)
        assert _infer_input_spec(ir)[1] is not None


class TestSizeLadders:
    def test_fast_algorithms_get_big_inputs(self):
        sizes, ladder = _sizes_for(COMPLEXITY_CLASSES["n_log_n"].rank)
        assert ladder == "fast" and max(sizes) >= 5000

    def test_exponential_gets_tiny_inputs(self):
        sizes, ladder = _sizes_for(COMPLEXITY_CLASSES["exponential"].rank)
        assert ladder == "exponential" and max(sizes) <= 18


class TestBenchmarkRun:
    def test_end_to_end_benchmark_and_agreement(self):
        engine = BenchmarkEngine()
        code_a = "def sort_a(arr):\n    return sorted(arr)\n"
        code_b = "def sort_b(arr):\n    return [x for x in sorted(arr)]\n"
        ir_a, ir_b = ir_for(code_a), ir_for(code_b)
        c_a = ComplexityAnalyzer().analyze(ir_a)
        c_b = ComplexityAnalyzer().analyze(ir_b)
        report = engine.run(ir_a, ir_b, c_a, c_b)

        assert report.status == "completed"
        assert report.a.status == "completed" and report.b.status == "completed"
        assert len(report.a.points) >= 2
        assert all(p.time_ms is not None for p in report.a.points)
        assert all(p.memory_kb is not None for p in report.a.points)
        # Identical outputs on shared inputs → agreement.
        assert report.output_agreement is True
        assert len(report.comparison) >= 2

    def test_runtime_error_is_reported_not_raised(self):
        engine = BenchmarkEngine()
        code = "def boom(arr):\n    raise ValueError('boom')\n"
        ir = ir_for(code)
        comp = ComplexityAnalyzer().analyze(ir)
        report = engine.run(ir, ir, comp, comp)
        assert report.a.status in {"error", "partial"}
        assert report.a.points == [] or all(p.error for p in report.a.points)

    def test_infinite_loop_killed_by_timeout(self):
        engine = BenchmarkEngine()
        engine._settings.benchmark_timeout_seconds = 6  # keep the test fast
        code = "def spin(arr):\n    while True:\n        pass\n"
        ir = ir_for(code)
        comp = ComplexityAnalyzer().analyze(ir)
        report = engine.run(ir, ir, comp, comp)
        assert report.a.status in {"error", "partial"}
