"""Conceptual similarity engine.

Computes a weighted, explainable similarity score (0–100) between two
algorithms by comparing normalised feature vectors extracted by the
parser:

============  ==========================  =====
Feature       Signal                     Weight
============  ==========================  =====
Purpose       problem-domain category     25
Output        return-type signature       15
Input         parameter signature         10
Recursion     recursive structure         10
Loops         nesting topology            10
Data struct.  containers used             10
Operations    builtin/method vocabulary   10
Complexity    asymptotic class match      10
============  ==========================  =====

Every feature contributes an individually scored entry, so the UI can
show *why* the algorithms received their score (glass-box scoring).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.complexity.analyzer import ComplexityReport
from app.services.parser.models import AlgorithmIR, FunctionIR


@dataclass
class FeatureScore:
    """One row of the similarity breakdown."""

    feature: str
    score: float      # 0..1
    weight: float     # contribution weight (sums to 100)
    detail: str


@dataclass
class SimilarityReport:
    """Aggregate similarity output."""

    score: float                  # 0..100
    band: str
    summary: str
    features: list[FeatureScore]


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class SimilarityEngine:
    """Weighted feature-vector comparison of two parsed algorithms."""

    WEIGHTS = {
        "purpose": 25.0,
        "output_signature": 15.0,
        "input_signature": 10.0,
        "recursion_structure": 10.0,
        "loop_topology": 10.0,
        "data_structures": 10.0,
        "operations": 10.0,
        "complexity_class": 10.0,
    }

    def compare(self, ir_a: AlgorithmIR, ir_b: AlgorithmIR,
                comp_a: ComplexityReport, comp_b: ComplexityReport) -> SimilarityReport:
        fn_a, fn_b = ir_a.primary, ir_b.primary
        features: list[FeatureScore] = []

        # --- purpose -----------------------------------------------------
        from app.services.functional.analyzer import classify_purpose

        purpose_a, purpose_b = classify_purpose(ir_a), classify_purpose(ir_b)
        purpose_score = 1.0 if purpose_a == purpose_b else 0.0
        features.append(FeatureScore(
            "purpose", purpose_score, self.WEIGHTS["purpose"],
            f"A: {purpose_a} · B: {purpose_b}",
        ))

        # --- output signature ---------------------------------------------
        ret_a = set(fn_a.returns) if fn_a else set()
        ret_b = set(fn_b.returns) if fn_b else set()
        if "unknown" in ret_a or "unknown" in ret_b:
            out_score = 0.5 + 0.5 * _jaccard(ret_a - {"unknown"}, ret_b - {"unknown"})
        else:
            out_score = _jaccard(ret_a, ret_b)
        features.append(FeatureScore(
            "output_signature", out_score, self.WEIGHTS["output_signature"],
            f"A returns {sorted(ret_a) or 'nothing'} · B returns {sorted(ret_b) or 'nothing'}",
        ))

        # --- input signature ------------------------------------------------
        def required_kinds(fn: FunctionIR | None) -> list[str]:
            if fn is None:
                return []
            req = [a.kind for a in fn.args if not a.has_default]
            return req if req else [a.kind for a in fn.args]

        kinds_a, kinds_b = required_kinds(fn_a), required_kinds(fn_b)
        primary_match = bool(kinds_a and kinds_b and kinds_a[0] == kinds_b[0])
        in_score = (0.7 + 0.3 * _jaccard(set(kinds_a), set(kinds_b))) if primary_match \
            else _jaccard(set(kinds_a), set(kinds_b))
        features.append(FeatureScore(
            "input_signature", in_score, self.WEIGHTS["input_signature"],
            f"A takes ({', '.join(kinds_a) or '—'}) · B takes ({', '.join(kinds_b) or '—'})",
        ))

        # --- recursion -----------------------------------------------------
        if fn_a and fn_b and fn_a.is_recursive and fn_b.is_recursive:
            rec_score = 1.0 if fn_a.recursion_shrink == fn_b.recursion_shrink else 0.85
            detail = (f"both recursive (shrink: {fn_a.recursion_shrink} vs {fn_b.recursion_shrink})")
        elif fn_a and fn_b and not fn_a.is_recursive and not fn_b.is_recursive:
            rec_score, detail = 0.9, "both iterative"
        else:
            rec_score, detail = 0.2, "one recursive, one iterative"
        features.append(FeatureScore(
            "recursion_structure", rec_score, self.WEIGHTS["recursion_structure"], detail
        ))

        # --- loop topology -----------------------------------------------------
        d_a = fn_a.max_loop_depth if fn_a else 0
        d_b = fn_b.max_loop_depth if fn_b else 0
        c_a = len(fn_a.loops) if fn_a else 0
        c_b = len(fn_b.loops) if fn_b else 0
        loop_score = max(0.0, 1.0 - (abs(d_a - d_b) * 0.5 + abs(c_a - c_b) / 4.0))
        features.append(FeatureScore(
            "loop_topology", loop_score, self.WEIGHTS["loop_topology"],
            f"A: depth {d_a}, {c_a} loop(s) · B: depth {d_b}, {c_b} loop(s)",
        ))

        # --- data structures ----------------------------------------------------
        ds_a = set(fn_a.data_structures) if fn_a else set()
        ds_b = set(fn_b.data_structures) if fn_b else set()
        ds_score = _jaccard(ds_a, ds_b)
        features.append(FeatureScore(
            "data_structures", ds_score, self.WEIGHTS["data_structures"],
            f"A: {sorted(ds_a) or '—'} · B: {sorted(ds_b) or '—'}",
        ))

        # --- operations ------------------------------------------------------------
        def vocabulary(ir: AlgorithmIR) -> set[str]:
            words: set[str] = set()
            for f in ir.functions:
                words |= set(f.builtin_calls) | set(f.method_calls) | set(f.operations)
            return words

        ops_a, ops_b = vocabulary(ir_a), vocabulary(ir_b)
        # Overlap coefficient: shared vocabulary relative to the smaller set.
        denom = min(len(ops_a), len(ops_b))
        ops_score = len(ops_a & ops_b) / denom if denom else 1.0
        features.append(FeatureScore(
            "operations", ops_score, self.WEIGHTS["operations"],
            f"{len(ops_a & ops_b)} shared of {len(ops_a | ops_b)} distinct operations",
        ))

        # --- complexity class --------------------------------------------------------
        avg_match = comp_a.time.average.key == comp_b.time.average.key
        worst_match = comp_a.time.worst.key == comp_b.time.worst.key
        best_match = comp_a.time.best.key == comp_b.time.best.key
        cx_score = 0.5 * avg_match + 0.35 * worst_match + 0.15 * best_match
        features.append(FeatureScore(
            "complexity_class", cx_score, self.WEIGHTS["complexity_class"],
            f"best {comp_a.time.best.label} vs {comp_b.time.best.label}; "
            f"avg {comp_a.time.average.label} vs {comp_b.time.average.label}; "
            f"worst {comp_a.time.worst.label} vs {comp_b.time.worst.label}",
        ))

        # --- aggregate ---------------------------------------------------------------
        score = sum(f.score * f.weight for f in features)
        if score >= 85:
            band = "Very similar"
        elif score >= 70:
            band = "Moderately similar"
        elif score >= 40:
            band = "Weakly similar"
        else:
            band = "Dissimilar"

        summary = (
            f"The algorithms share {score:.0f}% of their conceptual footprint "
            f"({band.lower()})."
            if purpose_score
            else f"The algorithms target different problem domains ({purpose_a} vs {purpose_b})."
        )

        return SimilarityReport(score=round(score, 1), band=band, summary=summary, features=features)
