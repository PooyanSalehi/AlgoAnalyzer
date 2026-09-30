"""Complexity classes and a small polynomial-logarithmic cost algebra.

A cost term is modelled as ``Θ(n^deg · log^k n)`` with ``k ∈ {0, 1}`` and
``deg`` a non-negative real. This is expressive enough for the classic
families (O(1), O(log n), O(n), O(n log n), O(n²), O(n³), …) while
remaining trivially comparable — which is exactly what the Master Theorem
implementation needs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import total_ordering

#: Exponential growth is capped in chart series so values stay finite.
_EXP_CAP = 200.0


@total_ordering
@dataclass(frozen=True)
class ComplexityClass:
    """An asymptotic complexity class with a chart-friendly growth model."""

    key: str
    label: str
    rank: int          # ordering: 1 = best (O(1)) … 10 = worst (O(n!))
    description: str = ""

    def __lt__(self, other: "ComplexityClass") -> bool:
        """Order classes by asymptotic growth (smaller rank = better)."""
        return self.rank < other.rank

    def growth(self, n: float) -> float:
        """Estimated operation count for input size ``n`` (used by charts)."""
        n = max(float(n), 1.0)
        if self.key == "constant":
            return 1.0
        if self.key == "log_n":
            return math.log2(n)
        if self.key == "sqrt_n":
            return math.sqrt(n)
        if self.key == "linear":
            return n
        if self.key == "n_log_n":
            return n * math.log2(n)
        if self.key == "quadratic":
            return n * n
        if self.key == "n_2_log_n":
            return n * n * math.log2(n)
        if self.key == "cubic":
            return n ** 3
        if self.key.startswith("n_pow_"):
            return n ** float(self.key.rsplit("_", 1)[-1])
        if self.key == "exponential":
            return 2.0 ** min(n, _EXP_CAP)
        if self.key == "factorial":
            return math.gamma(min(n, 20.0) + 1.0)
        return n


#: Canonical registry of complexity classes ordered from best to worst.
COMPLEXITY_CLASSES: dict[str, ComplexityClass] = {
    c.key: c
    for c in [
        ComplexityClass("constant", "O(1)", 1, "Constant — independent of input size"),
        ComplexityClass("log_n", "O(log n)", 2, "Logarithmic — halves the problem each step"),
        ComplexityClass("sqrt_n", "O(√n)", 3, "Root — sub-linear"),
        ComplexityClass("linear", "O(n)", 4, "Linear — scans the input once"),
        ComplexityClass("n_log_n", "O(n log n)", 5, "Linearithmic — typical for divide & conquer"),
        ComplexityClass("quadratic", "O(n²)", 6, "Quadratic — nested scans over the input"),
        ComplexityClass("n_2_log_n", "O(n² log n)", 7, "Quadratic-logarithmic"),
        ComplexityClass("cubic", "O(n³)", 8, "Cubic — triple nested scans"),
        ComplexityClass("exponential", "O(2ⁿ)", 9, "Exponential — grows by repeated branching"),
        ComplexityClass("factorial", "O(n!)", 10, "Factorial — brute-force permutations"),
    ]
}

# Rank for ad-hoc classes (e.g. O(n^1.58) from the Master Theorem).
_ADHOC_BASE_RANK = 5


@dataclass(frozen=True)
class Cost:
    """Θ(n^deg · log n if ``log`` else 1) — the internal cost algebra term."""

    deg: float = 0.0
    log: bool = False

    # -- algebra ------------------------------------------------------------
    def mul(self, other: "Cost") -> "Cost":
        """Multiply two factors (degrees add, log flags or together)."""
        return Cost(deg=self.deg + other.deg, log=self.log or other.log)

    @staticmethod
    def maximum(a: "Cost", b: "Cost") -> "Cost":
        """Sequence composition: total cost is the dominant term."""
        return a if a.rank >= b.rank else b

    # -- ordering -----------------------------------------------------------
    @property
    def rank(self) -> float:
        return self.deg + (0.5 if self.log else 0.0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Cost) and self.deg == other.deg and self.log == other.log

    def __lt__(self, other: "Cost") -> bool:
        return self.rank < other.rank

    # -- conversion ----------------------------------------------------------
    def to_class(self) -> ComplexityClass:
        """Map a cost term onto the canonical complexity-class registry."""
        deg, log = round(self.deg * 2) / 2, self.log
        if deg == 0 and not log:
            return COMPLEXITY_CLASSES["constant"]
        if deg == 0 and log:
            return COMPLEXITY_CLASSES["log_n"]
        if deg == 0.5:
            return COMPLEXITY_CLASSES["sqrt_n"]
        if deg == 1 and not log:
            return COMPLEXITY_CLASSES["linear"]
        if deg == 1 and log:
            return COMPLEXITY_CLASSES["n_log_n"]
        if deg == 2 and not log:
            return COMPLEXITY_CLASSES["quadratic"]
        if deg == 2 and log:
            return COMPLEXITY_CLASSES["n_2_log_n"]
        if deg == 3:
            return COMPLEXITY_CLASSES["cubic"]
        if deg.is_integer() and deg > 3:
            key = f"n_pow_{int(deg)}"
            return ComplexityClass(key, f"O(n^{int(deg)})", _ADHOC_BASE_RANK + deg - 5)
        if deg > 0:
            key = f"n_pow_{deg:g}"
            return ComplexityClass(key, f"O(n^{deg:g})", _ADHOC_BASE_RANK + deg - 5)
        return COMPLEXITY_CLASSES["constant"]

    def label(self) -> str:
        return self.to_class().label

    def theta_label(self) -> str:
        """Same as :meth:`label` but with Θ notation (for recurrences)."""
        return "Θ" + self.to_class().label[1:]


def class_for(key: str) -> ComplexityClass:
    """Look up a class by key, falling back to a linear placeholder."""
    return COMPLEXITY_CLASSES.get(key, COMPLEXITY_CLASSES["linear"])


#: Cost shortcuts used throughout the analyzer.
COST_0 = Cost(0, False)
COST_LOG = Cost(0, True)
COST_N = Cost(1, False)
COST_N_LOG = Cost(1, True)

#: Asymptotic cost of tracked builtins (degree, log) as a function of the
#: size of their (primary) argument.
BUILTIN_COSTS: dict[str, Cost] = {
    "len": COST_0,
    "abs": COST_0,
    "round": COST_0,
    "min": COST_N,      # single-argument min/max/sum scan the collection
    "max": COST_N,
    "sum": COST_N,
    "any": COST_N,
    "all": COST_N,
    "sorted": COST_N_LOG,
    "sort": COST_N_LOG,
    "reversed": COST_N,
    "list": COST_N,
    "set": COST_N,
    "dict": COST_N,
    "tuple": COST_N,
    "enumerate": COST_N,
    "zip": COST_N,
    "map": COST_N,
    "filter": COST_N,
    "range": COST_0,
    "pow": COST_0,
    "join": COST_N,
}
