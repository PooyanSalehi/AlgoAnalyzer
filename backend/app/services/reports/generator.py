"""Professional Markdown report generation.

Assembles every analysis stage into a single, academically structured
document:

1. Algorithm overview
2. Functional comparison
3. Complexity comparison table
4. Benchmark results
5. Mathematical explanation
6. AI-generated summary
7. Final conclusion
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.benchmark.engine import BenchmarkReport
from app.services.complexity.analyzer import ComplexityReport
from app.services.functional.analyzer import FunctionalReport
from app.services.parser.models import AlgorithmIR
from app.services.similarity.engine import SimilarityReport


@dataclass
class ReportInputs:
    """Everything the generator needs — keeps it decoupled from services."""

    ir_a: AlgorithmIR
    ir_b: AlgorithmIR
    complexity_a: ComplexityReport
    complexity_b: ComplexityReport
    functional: FunctionalReport
    similarity: SimilarityReport
    benchmark: BenchmarkReport
    explanation: str


class ReportGenerator:
    """Renders the final Markdown report."""

    def generate(self, data: ReportInputs) -> str:
        a, b = data.ir_a.name or "Algorithm A", data.ir_b.name or "Algorithm B"
        fa, fb = data.functional, data.similarity
        ca, cb = data.complexity_a, data.complexity_b

        lines: list[str] = []
        add = lines.append

        add("# AlgoAnalyzer — Algorithm Analysis Report")
        add("")
        add(f"**Comparison:** `{a}` vs `{b}`  ")
        add(f"**Functional similarity:** {fa.confidence * 100:.0f}% · **Conceptual similarity score:** "
            f"{fb.score:.1f}/100 ({fb.band})")
        add("")

        # 1. Overview -------------------------------------------------------
        add("## 1. Algorithm Overview")
        add("")
        add("| | Algorithm A | Algorithm B |")
        add("|---|---|---|")
        add(f"| Name | {a} | {b} |")
        add(f"| Input mode | {data.ir_a.mode.value} | {data.ir_b.mode.value} |")
        add(f"| Lines of code | {data.ir_a.line_count} | {data.ir_b.line_count} |")
        add(f"| Functions detected | {len(data.ir_a.functions)} | {len(data.ir_b.functions)} |")
        add(f"| Strategy | {ca.pattern} | {cb.pattern} |")
        if data.ir_a.primary:
            add(f"| Primary function | `{data.ir_a.primary.name}()` | `{data.ir_b.primary.name}()` |")
        add("")

        # 2. Functional comparison -------------------------------------------
        add("## 2. Functional Comparison")
        add("")
        add(f"**Verdict:** {fa.verdict} (confidence {fa.confidence * 100:.0f}%).")
        add("")
        add(f"- Purpose A: **{fa.purpose_a}** — Purpose B: **{fa.purpose_b}**")
        add(f"- {fa.input_analysis}")
        add(f"- {fa.output_analysis}")
        for reason in fa.reasoning:
            add(f"- {reason}")
        if data.benchmark.output_agreement is True:
            add(f"- ✅ Empirical check: both algorithms produced identical outputs on "
                f"{data.benchmark.agreement_samples} random test inputs.")
        elif data.benchmark.output_agreement is False:
            add(f"- ⚠️ Empirical check: outputs differed on at least one of "
                f"{data.benchmark.agreement_samples} random test inputs.")
        add("")

        # 3. Complexity comparison ---------------------------------------------
        add("## 3. Complexity Comparison")
        add("")
        add("| | Best | Average | Worst | Aux. Space |")
        add("|---|---|---|---|---|")
        add(f"| **{a}** | {ca.time.best.label} | {ca.time.average.label} | {ca.time.worst.label} | "
            f"{ca.space.auxiliary.label} |")
        add(f"| **{b}** | {cb.time.best.label} | {cb.time.average.label} | {cb.time.worst.label} | "
            f"{cb.space.auxiliary.label} |")
        add("")

        # 4. Benchmarks -----------------------------------------------------------
        add("## 4. Benchmark Results")
        add("")
        if data.benchmark.status in {"completed", "partial"} and data.benchmark.comparison:
            add("| n | A time (ms) | B time (ms) | A/B ratio | A mem (KB) | B mem (KB) |")
            add("|---:|---:|---:|---:|---:|---:|")
            mem_a = {p.n: p.memory_kb for p in data.benchmark.a.points if p.memory_kb is not None}
            mem_b = {p.n: p.memory_kb for p in data.benchmark.b.points if p.memory_kb is not None}
            for row in data.benchmark.comparison:
                n = row["n"]
                add(f"| {n} | {row['time_a_ms']:.3f} | {row['time_b_ms']:.3f} | "
                    f"{row['ratio'] if row['ratio'] else '—'} | "
                    f"{mem_a.get(n, '—') if mem_a.get(n) is not None else '—'} | "
                    f"{mem_b.get(n, '—') if mem_b.get(n) is not None else '—'} |")
        else:
            add("_Benchmarks were not available for this comparison._")
            add("")
            for note in data.benchmark.notes:
                add(f"- {note}")
        add("")

        # 5. Mathematical explanation ---------------------------------------------
        add("## 5. Mathematical Explanation")
        add("")
        add(f"### {a}")
        add("")
        if ca.recurrence:
            add(f"Recurrence: **{ca.recurrence}**")
            add("")
        for line in ca.explanations:
            add(f"- {line}")
        for line in ca.space.explanations:
            add(f"- {line}")
        add("")
        add(f"### {b}")
        add("")
        if cb.recurrence:
            add(f"Recurrence: **{cb.recurrence}**")
            add("")
        for line in cb.explanations:
            add(f"- {line}")
        for line in cb.space.explanations:
            add(f"- {line}")
        add("")

        # 6. AI summary ----------------------------------------------------------------
        add("## 6. AI Summary")
        add("")
        for paragraph in data.explanation.split("\n\n"):
            if paragraph.strip():
                add(paragraph.strip())
                add("")

        # 7. Final summary -----------------------------------------------------------------
        add("## 7. Final Summary")
        add("")
        add(self._final_summary(data))
        add("")
        add("---")
        add("_Generated by AlgoAnalyzer — automated algorithm analysis for education._")
        return "\n".join(lines)

    def _final_summary(self, data: ReportInputs) -> str:
        a, b = data.ir_a.name or "Algorithm A", data.ir_b.name or "Algorithm B"
        ca, cb = data.complexity_a, data.complexity_b
        parts: list[str] = []

        if data.functional.equivalent:
            parts.append(
                f"`{a}` and `{b}` solve the same class of problem "
                f"({data.functional.purpose_a}) with a conceptual similarity of "
                f"{data.similarity.score:.0f}%."
            )
        else:
            parts.append(
                f"`{a}` and `{b}` target different problems ({data.functional.purpose_a} vs "
                f"{data.functional.purpose_b}); similarity {data.similarity.score:.0f}%."
            )

        if ca.time.worst.rank < cb.time.worst.rank:
            parts.append(
                f"`{a}` has the better worst-case guarantee ({ca.time.worst.label} vs "
                f"{cb.time.worst.label})."
            )
        elif cb.time.worst.rank < ca.time.worst.rank:
            parts.append(
                f"`{b}` has the better worst-case guarantee ({cb.time.worst.label} vs "
                f"{ca.time.worst.label})."
            )
        else:
            parts.append(f"Both share the same worst-case bound ({ca.time.worst.label}).")

        if ca.space.auxiliary.rank < cb.space.auxiliary.rank:
            parts.append(f"`{a}` is more memory-efficient in auxiliary space "
                         f"({ca.space.auxiliary.label} vs {cb.space.auxiliary.label}).")
        elif cb.space.auxiliary.rank < ca.space.auxiliary.rank:
            parts.append(f"`{b}` is more memory-efficient in auxiliary space "
                         f"({cb.space.auxiliary.label} vs {ca.space.auxiliary.label}).")

        if data.benchmark.comparison:
            last = data.benchmark.comparison[-1]
            if last.get("ratio"):
                if last["ratio"] > 1.05:
                    parts.append(f"Empirically, `{a}` was ~{last['ratio']:.2f}× faster than `{b}` "
                                 f"at n = {last['n']}.")
                elif last["ratio"] < 0.95:
                    parts.append(f"Empirically, `{b}` was ~{1 / last['ratio']:.2f}× faster than `{a}` "
                                 f"at n = {last['n']}.")
                else:
                    parts.append(f"Empirically the algorithms performed similarly at n = {last['n']}.")

        return " ".join(parts)
