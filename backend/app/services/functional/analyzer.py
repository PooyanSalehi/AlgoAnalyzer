"""Functional equivalence analysis.

Decides whether two algorithms solve the *same computational problem* by
comparing:

* **purpose category** — what problem domain the algorithm belongs to
  (sorting, searching, numeric computation, …), derived from semantic
  keyword hints and structural evidence;
* **input behaviour** — what the primary function consumes;
* **output behaviour** — what it returns (type/shape of the result);
* **operation patterns** — the vocabulary of operations and data
  structures used.

The verdict is expressed with an explicit confidence level and a list of
human-readable reasoning steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.complexity.analyzer import ComplexityReport
from app.services.parser.keywords import PURPOSE_KEYWORDS
from app.services.parser.models import AlgorithmIR, FunctionIR


@dataclass
class FunctionalReport:
    """Outcome of the functional-equivalence stage."""

    equivalent: bool
    verdict: str
    confidence: float
    purpose_a: str
    purpose_b: str
    input_analysis: str
    output_analysis: str
    operation_analysis: str
    reasoning: list[str] = field(default_factory=list)
    # Filled in later by the benchmark engine (empirical output comparison).
    empirical_output_match: bool | None = None
    empirical_samples: int = 0


# --------------------------------------------------------------------------- #
# Purpose classification
# --------------------------------------------------------------------------- #
def classify_purpose(ir: AlgorithmIR) -> str:
    """Assign the algorithm to a problem domain using hints + structure."""
    fn = ir.primary
    if fn is None:
        return "general computation"

    scores: dict[str, float] = {purpose: 0.0 for purpose in PURPOSE_KEYWORDS}
    for purpose, keywords in PURPOSE_KEYWORDS.items():
        scores[purpose] += 3.0 * len(fn.hints & keywords)

    # Structural evidence -------------------------------------------------
    builtins = set(fn.builtin_calls)
    methods = set(fn.method_calls)
    if "sorted" in builtins or "sort" in methods:
        scores["sorting"] += 5.0
    if fn.memoized:
        scores["dynamic programming"] += 4.0
    if fn.early_exit and ("index" in fn.hints or "find" in fn.hints):
        scores["searching"] += 3.0
    if fn.is_recursive and fn.recursion_shrink == "half":
        scores["searching"] += 0.5  # halving is typical for search, but also D&C
        scores["sorting"] += 0.5
    if {"deque", "heap"} & set(fn.data_structures) or {"bfs", "dfs", "graph"} & fn.hints:
        scores["graph traversal"] += 4.0
    if "string" in fn.data_structures or {"join", "split"} & methods:
        scores["string processing"] += 2.0
    if fn.max_loop_depth >= 2 and {"swap", "bubble", "insertion", "selection"} & fn.hints:
        scores["sorting"] += 3.0

    best = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
    return best if scores[best] > 0 else "general computation"


# --------------------------------------------------------------------------- #
# Description helpers
# --------------------------------------------------------------------------- #
def _describe_args(fn: FunctionIR | None) -> str:
    if fn is None or not fn.args:
        return "no explicit inputs"
    parts = [f"{a.name}: {a.kind}" + (f" (annotated {a.annotation})" if a.annotation else "")
             for a in fn.args]
    return ", ".join(parts)


def _describe_returns(fn: FunctionIR | None) -> str:
    if fn is None:
        return "unknown"
    if not fn.returns or fn.returns == ["None"]:
        return "nothing (side effects only / None)"
    return " / ".join(sorted(fn.returns))


def _compatible_output(a: FunctionIR | None, b: FunctionIR | None) -> bool:
    ra = set(a.returns) if a else set()
    rb = set(b.returns) if b else set()
    if not ra or not rb:
        return True  # unknown → cannot rule out
    if ra & rb:
        return True
    if "unknown" in ra or "unknown" in rb:
        return True
    # Both "produce" something but of different kinds.
    return False


class FunctionalAnalyzer:
    """Compares two algorithms from a behavioural perspective."""

    def compare(self, ir_a: AlgorithmIR, ir_b: AlgorithmIR,
                comp_a: ComplexityReport, comp_b: ComplexityReport,
                similarity_score: float) -> FunctionalReport:
        fn_a, fn_b = ir_a.primary, ir_b.primary
        purpose_a, purpose_b = classify_purpose(ir_a), classify_purpose(ir_b)

        same_purpose = purpose_a == purpose_b
        out_ok = _compatible_output(fn_a, fn_b)
        general = purpose_a == "general computation"

        equivalent = same_purpose and out_ok and (not general or similarity_score >= 55)

        reasoning: list[str] = []
        if same_purpose and not general:
            reasoning.append(
                f"Both algorithms are classified as solving the same class of problems: "
                f"**{purpose_a}** (keyword and structural evidence matched)."
            )
        elif same_purpose:
            reasoning.append(
                "Both descriptions match general-purpose computation; equivalence is judged "
                "primarily on structural similarity."
            )
        else:
            reasoning.append(
                f"Algorithm A appears to solve a **{purpose_a}** problem, while Algorithm B "
                f"appears to solve a **{purpose_b}** problem — different computational goals."
            )

        # Input behaviour ---------------------------------------------------
        kinds_a = {a.kind for a in fn_a.args} if fn_a else set()
        kinds_b = {b.kind for b in fn_b.args} if fn_b else set()
        if kinds_a & kinds_b:
            reasoning.append(
                f"Both consume compatible inputs ({', '.join(sorted(kinds_a & kinds_b))}); "
                "the primary parameter scales with the input size n."
            )
        else:
            reasoning.append("The input signatures differ in kind, which weakens equivalence.")

        # Output behaviour ----------------------------------------------------
        ret_a, ret_b = _describe_returns(fn_a), _describe_returns(fn_b)
        if out_ok:
            reasoning.append(f"Output behaviour is compatible: A returns [{ret_a}], B returns [{ret_b}].")
        else:
            reasoning.append(
                f"Output behaviour differs: A returns [{ret_a}] but B returns [{ret_b}] — "
                "the algorithms do not answer the same question."
            )

        # Operation patterns ---------------------------------------------------
        ops_a = set(fn_a.builtin_calls) | set(fn_a.method_calls) if fn_a else set()
        ops_b = set(fn_b.builtin_calls) | set(fn_b.method_calls) if fn_b else set()
        shared_ops = ops_a & ops_b
        op_analysis = (
            f"Shared operations: {', '.join(sorted(shared_ops)) or 'none'}. "
            f"A relies on {', '.join(sorted(ops_a - ops_b)) or 'nothing extra'}; "
            f"B adds {', '.join(sorted(ops_b - ops_a)) or 'nothing extra'}."
        )
        reasoning.append(op_analysis)

        # Strategy contrast -----------------------------------------------------
        if fn_a and fn_b:
            strategy_a = ("recursive " + (fn_a.recursion_shrink or "") if fn_a.is_recursive else "iterative")
            strategy_b = ("recursive " + (fn_b.recursion_shrink or "") if fn_b.is_recursive else "iterative")
            reasoning.append(
                f"Strategy: A is {strategy_a} ({comp_a.pattern}); B is {strategy_b} ({comp_b.pattern})."
            )

        confidence = min(0.99, max(similarity_score / 100.0, 0.5 if equivalent else 0.1))
        verdict = (
            "Likely functionally equivalent — same problem, compatible I/O"
            if equivalent
            else "Not functionally equivalent — different problems or incompatible I/O"
        )

        return FunctionalReport(
            equivalent=equivalent,
            verdict=verdict,
            confidence=round(confidence, 2),
            purpose_a=purpose_a,
            purpose_b=purpose_b,
            input_analysis=(
                f"Algorithm A inputs: {_describe_args(fn_a)}. "
                f"Algorithm B inputs: {_describe_args(fn_b)}."
            ),
            output_analysis=f"Algorithm A returns: {ret_a}. Algorithm B returns: {ret_b}.",
            operation_analysis=op_analysis,
            reasoning=reasoning,
        )
