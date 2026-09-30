"""Benchmark engine: empirical measurement of runtime and memory.

For each algorithm the engine:

1. infers a *calling convention* from the parsed signature
   (e.g. ``[int_list]``, ``[int_list, int]`` for search, ``[int]`` for n-based
   algorithms such as Fibonacci);
2. selects escalating input sizes that are safe for the **detected worst-case
   complexity** (quadratic algorithms get smaller sizes, exponential ones only
   tiny sizes);
3. executes the algorithm inside the sandbox subprocess (see ``sandbox.py``)
   with deterministic seeded inputs, taking the best of N repetitions per size
   and measuring peak allocations with ``tracemalloc``;
4. optionally performs an **output-agreement check** (both algorithms on the
   same inputs) which feeds empirical evidence back into the functional
   analysis.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services.benchmark import sandbox
from app.services.complexity.analyzer import ComplexityReport
from app.services.parser.models import AlgorithmIR, InputMode

# Size ladders indexed by the worst-case complexity rank (1..10).
SIZE_LADDERS: dict[str, list[int]] = {
    "fast": [100, 500, 1000, 2000, 5000],      # O(1) … O(n log n), O(V+E)
    "quadratic": [100, 250, 500, 1000, 2000],  # O(n²), O(n² log n)
    "cubic": [50, 75, 100, 150, 200],          # O(n³)
    "slow": [10, 14, 18, 22, 26],              # O(n^k), k > 3
    "exponential": [6, 9, 12, 15, 18],         # O(2ⁿ), O(n!)
}


@dataclass
class BenchmarkPoint:
    """One measured (size → time, memory) sample."""

    n: int
    time_ms: float | None = None
    memory_kb: float | None = None
    error: str | None = None


@dataclass
class AlgorithmBenchmark:
    """Benchmark outcome for a single algorithm."""

    name: str
    status: str = "pending"  # completed | skipped | error
    points: list[BenchmarkPoint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class BenchmarkReport:
    """Combined benchmark outcome."""

    status: str = "pending"  # completed | partial | skipped | error
    a: AlgorithmBenchmark = field(default_factory=lambda: AlgorithmBenchmark("A"))
    b: AlgorithmBenchmark = field(default_factory=lambda: AlgorithmBenchmark("B"))
    output_agreement: bool | None = None
    agreement_samples: int = 0
    comparison: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _infer_input_spec(ir: AlgorithmIR) -> tuple[list[str], str | None]:
    """Return (spec, error). spec is a list of arg kinds the driver can build."""
    fn = ir.primary
    if ir.mode != InputMode.PYTHON or fn is None:
        return [], "Benchmarks are only available for executable Python source code."
    if fn.name == "<module>":
        return [], "No function definition found to execute."

    from app.services.functional.analyzer import classify_purpose

    purpose = classify_purpose(ir)
    searching = purpose == "searching"

    # Only *required* parameters must be provided by the driver; optional
    # parameters (with defaults) are left to the algorithm itself.
    required = [a.kind for a in fn.args if not a.has_default]
    optional = [a.kind for a in fn.args if a.has_default]
    kinds = required if required else optional

    list_kind = "int_list_sorted" if searching else "int_list"

    if kinds == ["iterable"]:
        return [list_kind], None
    if kinds[:1] == ["iterable"] and len(kinds) >= 2:
        rest = kinds[1:]
        if rest == ["int"]:
            return [list_kind, "int_target"], None
        if rest == ["int", "int"]:
            return [list_kind, "int", "int"], None
        if all(k == "int" for k in rest):
            return [list_kind] + ["int"] * len(rest), None
    if kinds[:1] == ["graph"] or (fn.args and fn.args[0].kind == "graph"):
        rest = kinds[1:]
        if all(k == "int" for k in rest):
            return ["graph"] + ["int_start"] * len(rest), None
        return ["graph"], None
    if kinds == ["int"]:
        return ["int"], None
    if kinds == ["string"]:
        return ["string"], None
    return [], (
        f"Cannot infer a safe calling convention for parameters ({', '.join(kinds)}); "
        "benchmarks were skipped."
    )


def _sizes_for(worst_rank: int) -> tuple[list[int], str]:
    if worst_rank <= 5:
        return SIZE_LADDERS["fast"], "fast"
    if worst_rank <= 7:
        return SIZE_LADDERS["quadratic"], "quadratic"
    if worst_rank == 8:
        return SIZE_LADDERS["cubic"], "cubic"
    if worst_rank <= 9:
        return SIZE_LADDERS["exponential"], "exponential"
    return SIZE_LADDERS["exponential"], "exponential"


class BenchmarkEngine:
    """Runs both algorithms under measurement and compares them."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------ one
    def _benchmark_one(
        self, ir: AlgorithmIR, complexity: ComplexityReport, workdir: str, stem: str
    ) -> AlgorithmBenchmark:
        spec, error = _infer_input_spec(ir)
        if error:
            return AlgorithmBenchmark(name=ir.name, status="skipped", notes=[error])

        sizes, ladder = _sizes_for(complexity.time.worst.rank)
        notes = [f"Input sizes chosen for detected worst case {complexity.time.worst.label} "
                 f"({ladder} ladder); best of {self._settings.benchmark_repeats} runs per size."]

        code_path = sandbox.write_module(ir.source, workdir, stem)
        driver_path = os.path.join(workdir, f"driver_{stem}.py")
        sandbox.build_benchmark_driver(
            code_path=code_path,
            fn_name=ir.primary.name,
            sizes=sizes,
            repeats=self._settings.benchmark_repeats,
            input_spec=spec,
            time_budget=self._settings.benchmark_time_budget_seconds,
            out_path=driver_path,
        )
        try:
            result = sandbox.run_driver(
                driver_path,
                timeout=self._settings.benchmark_timeout_seconds,
                max_memory_mb=self._settings.benchmark_max_memory_mb,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a status, never a 500
            return AlgorithmBenchmark(name=ir.name, status="error",
                                      notes=[f"Sandbox execution failed: {exc}"] + notes)

        points = [
            BenchmarkPoint(
                n=p.get("n", 0),
                time_ms=p.get("time_ms"),
                memory_kb=p.get("memory_kb"),
                error=p.get("error"),
            )
            for p in result.get("points", [])
        ]
        status = "completed" if any(p.time_ms is not None for p in points) else "error"
        if any(p.error for p in points):
            status = "partial" if status == "completed" else "error"
        return AlgorithmBenchmark(name=ir.name, status=status, points=points, notes=notes)

    # --------------------------------------------------------------- both
    def run(
        self,
        ir_a: AlgorithmIR,
        ir_b: AlgorithmIR,
        comp_a: ComplexityReport,
        comp_b: ComplexityReport,
    ) -> BenchmarkReport:
        if not self._settings.benchmark_enabled:
            return BenchmarkReport(
                status="skipped",
                a=AlgorithmBenchmark(ir_a.name, "skipped", notes=["Benchmarks disabled by configuration."]),
                b=AlgorithmBenchmark(ir_b.name, "skipped", notes=["Benchmarks disabled by configuration."]),
                notes=["Benchmark engine disabled (BENCHMARK_ENABLED=false)."],
            )

        report = BenchmarkReport()
        workdir = sandbox.temp_directory()
        try:
            report.a = self._benchmark_one(ir_a, comp_a, workdir, "algo_a")
            report.b = self._benchmark_one(ir_b, comp_b, workdir, "algo_b")
            self._agreement_check(ir_a, ir_b, workdir, report,
                                  comp_a.time.worst.rank, comp_b.time.worst.rank)
            self._build_comparison(report)
        finally:
            # Best-effort cleanup of temporary sandbox files.
            try:
                for entry in os.listdir(workdir):
                    os.unlink(os.path.join(workdir, entry))
                os.rmdir(workdir)
            except OSError:
                pass

        if report.a.status == "skipped" and report.b.status == "skipped":
            report.status = "skipped"
        elif report.a.status == "error" and report.b.status == "error":
            report.status = "error"
        else:
            report.status = "completed" if (
                report.a.status == "completed" and report.b.status == "completed"
            ) else "partial"

        report.notes.append(
            "Execution sandbox: isolated subprocess, "
            f"{self._settings.benchmark_timeout_seconds}s timeout, "
            f"{self._settings.benchmark_max_memory_mb}MB address-space limit."
        )
        return report

    # ----------------------------------------------------------- agreement
    def _agreement_check(
        self, ir_a: AlgorithmIR, ir_b: AlgorithmIR, workdir: str, report: BenchmarkReport,
        comp_rank_a: int = 4, comp_rank_b: int = 4,
    ) -> None:
        """Run both algorithms on identical inputs and compare outputs."""
        if ir_a.mode != InputMode.PYTHON or ir_b.mode != InputMode.PYTHON:
            return
        spec_a, err_a = _infer_input_spec(ir_a)
        spec_b, err_b = _infer_input_spec(ir_b)
        if err_a or err_b:
            return
        if spec_a and spec_b and spec_a[0] != spec_b[0]:
            return  # different primary input kinds → cannot share inputs
        try:
            driver = os.path.join(workdir, "driver_agreement.py")
            sandbox.build_agreement_driver(
                path_a=os.path.join(workdir, "algo_a.py"),
                path_b=os.path.join(workdir, "algo_b.py"),
                name_a=ir_a.primary.name,
                name_b=ir_b.primary.name,
                spec_a=spec_a or ["int"],
                spec_b=spec_b or ["int"],
                n=12 if max(comp_rank_a, comp_rank_b) >= 9 else 40,
                seeds=[0, 1, 2, 3, 4],
                out_path=driver,
            )
            result = sandbox.run_driver(
                driver,
                timeout=self._settings.benchmark_timeout_seconds,
                max_memory_mb=self._settings.benchmark_max_memory_mb,
            )
            report.agreement_samples = result.get("samples", 0)
            if result.get("match", 0) and not result.get("mismatch", 0) and not result.get("errored", 0):
                report.output_agreement = True
            elif result.get("mismatch", 0):
                report.output_agreement = False
            else:
                report.output_agreement = None
        except Exception:  # noqa: BLE001 - agreement check is best effort
            report.output_agreement = None

    # ----------------------------------------------------------- comparison
    def _build_comparison(self, report: BenchmarkReport) -> None:
        times_a = {p.n: p.time_ms for p in report.a.points if p.time_ms is not None}
        times_b = {p.n: p.time_ms for p in report.b.points if p.time_ms is not None}
        for n in sorted(set(times_a) & set(times_b)):
            report.comparison.append({
                "n": n,
                "time_a_ms": round(times_a[n], 4),
                "time_b_ms": round(times_b[n], 4),
                "ratio": round(times_b[n] / times_a[n], 3) if times_a[n] > 0 else None,
            })
