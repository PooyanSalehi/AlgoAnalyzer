"""Deterministic, template-driven natural-language explanations.

The heuristic explainer converts the structured analysis result into
fluent prose without any external dependency, guaranteeing reproducible
output — an important property for grading and academic demos.
"""
from __future__ import annotations

from app.services.reports.generator import ReportInputs


class HeuristicExplainer:
    """Rule-based text generation from the analysis result."""

    name = "heuristic"

    def explain(self, data: ReportInputs) -> str:
        a = data.ir_a.name or "Algorithm A"
        b = data.ir_b.name or "Algorithm B"
        ca, cb = data.complexity_a, data.complexity_b
        fa, sim = data.functional, data.similarity
        bench = data.benchmark

        paragraphs: list[str] = []

        # --- paragraph 1: what the algorithms are ---------------------------
        p1 = (
            f"**{a}** is a {ca.pattern} algorithm with best/average/worst-case time complexity of "
            f"{ca.time.best.label} / {ca.time.average.label} / {ca.time.worst.label} and "
            f"{ca.space.auxiliary.label} auxiliary space. "
            f"**{b}** is a {cb.pattern} algorithm running in "
            f"{cb.time.best.label} / {cb.time.average.label} / {cb.time.worst.label} time with "
            f"{cb.space.auxiliary.label} auxiliary space."
        )
        paragraphs.append(p1)

        # --- paragraph 2: functional relationship -------------------------------
        if fa.equivalent:
            p2 = (
                f"Both algorithms solve the same computational problem ({fa.purpose_a}) and return "
                f"compatible outputs, which is reflected in a conceptual similarity score of "
                f"{sim.score:.0f}% ({sim.band.lower()}). "
            )
            if bench.output_agreement is True:
                p2 += (
                    f"An empirical cross-check confirmed that both produce identical results on "
                    f"{bench.agreement_samples} random inputs. "
                )
            p2 += "They differ in *how* they reach the solution, not in *what* they compute."
        else:
            p2 = (
                f"The algorithms address different problems: {a} appears to be a "
                f"{fa.purpose_a} algorithm, while {b} is best classified as {fa.purpose_b} "
                f"(similarity {sim.score:.0f}%). Their input/output behaviours do not line up, "
                "so they are not interchangeable."
            )
        paragraphs.append(p2)

        # --- paragraph 3: complexity trade-off --------------------------------------
        p3_parts: list[str] = []
        if ca.time.worst.rank < cb.time.worst.rank:
            p3_parts.append(
                f"{a} has the stronger worst-case guarantee ({ca.time.worst.label} versus "
                f"{cb.time.worst.label}); it remains predictable on adversarial or degenerate "
                "inputs, which matters on large datasets."
            )
        elif cb.time.worst.rank < ca.time.worst.rank:
            p3_parts.append(
                f"{b} has the stronger worst-case guarantee ({cb.time.worst.label} versus "
                f"{ca.time.worst.label}); {a} may degrade badly on specific inputs."
            )
        else:
            p3_parts.append(
                f"Neither algorithm dominates the other asymptotically — both are bounded by "
                f"{ca.time.worst.label} in the worst case."
            )
        if ca.space.auxiliary.rank < cb.space.auxiliary.rank:
            p3_parts.append(
                f"In terms of memory, {a} is leaner ({ca.space.auxiliary.label} versus "
                f"{cb.space.auxiliary.label} auxiliary space)."
            )
        elif cb.space.auxiliary.rank < ca.space.auxiliary.rank:
            p3_parts.append(
                f"In terms of memory, {b} is leaner ({cb.space.auxiliary.label} versus "
                f"{ca.space.auxiliary.label} auxiliary space)."
            )
        if ca.recurrence:
            p3_parts.append(f"Mathematically, {a} follows the recurrence {ca.recurrence}.")
        if cb.recurrence:
            p3_parts.append(f"{b} follows {cb.recurrence}.")
        paragraphs.append(" ".join(p3_parts))

        # --- paragraph 4: empirical evidence ----------------------------------------
        if bench.comparison:
            last = bench.comparison[-1]
            if last.get("ratio"):
                if last["ratio"] > 1.05:
                    p4 = (
                        f"Empirically, on inputs of size n = {last['n']}, {a} completed in "
                        f"{last['time_a_ms']:.3f} ms versus {last['time_b_ms']:.3f} ms for {b} — "
                        f"roughly {last['ratio']:.2f}× faster, matching the theoretical prediction."
                    )
                elif last["ratio"] < 0.95:
                    p4 = (
                        f"Empirically, on inputs of size n = {last['n']}, {b} completed in "
                        f"{last['time_b_ms']:.3f} ms versus {last['time_a_ms']:.3f} ms for {a} — "
                        f"roughly {1 / last['ratio']:.2f}× faster, thanks to lower constant factors."
                    )
                else:
                    p4 = (
                        f"At n = {last['n']} both algorithms ran in comparable wall-clock time "
                        f"({last['time_a_ms']:.3f} ms vs {last['time_b_ms']:.3f} ms)."
                    )
                p4 += (
                    " Note that constant factors and cache behaviour dominate at small n; "
                    "asymptotic differences become visible as n grows."
                )
                paragraphs.append(p4)

        # --- paragraph 5: recommendation -----------------------------------------------
        if fa.equivalent:
            better = a if ca.time.worst.rank <= cb.time.worst.rank else b
            other = b if better == a else a
            p5 = (
                f"Recommendation: for large or adversarial inputs prefer **{better}** because it "
                f"offers the more stable complexity profile"
            )
            if (data.complexity_b if better == a else data.complexity_a).space.auxiliary.rank < \
                    (ca if better == a else cb).space.auxiliary.rank:
                p5 += f", while {other} is preferable when memory is the scarcer resource"
            p5 += "."
            paragraphs.append(p5)

        return "\n\n".join(paragraphs)
