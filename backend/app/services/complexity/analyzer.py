"""Complexity analysis engine.

Architecture
------------
1. **Iterative cost** of every function is computed from the AST with a
   small cost algebra ``Θ(n^deg · log n)``: sequence → max, nesting →
   multiplication, builtin calls contribute their asymptotic cost
   (``sorted`` → n log n, ``sum`` → n, …). Local helper functions are
   inlined through the module call graph.
2. **Recurrences** derived from detected recursion (branching factor,
   shrink factor) are solved with the Master Theorem, or with the
   linear-recursion rule ``T(n) = T(n-1) + f(n) = Θ(n·f(n))``.
3. **Pattern recognizers** refine the generic result for well-known
   algorithm families (quick sort, adaptive sorts, graph traversal) and
   produce their textbook explanations.
4. Best / average / worst cases are derived from data-dependence signals
   (early exits, adaptive loops, pivot degeneration).

The result is a :class:`ComplexityReport` with mathematically worded
explanations suitable for academic presentation.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field

from app.services.complexity.classes import (
    BUILTIN_COSTS,
    COST_0,
    COST_LOG,
    COST_N,
    COST_N_LOG,
    COMPLEXITY_CLASSES,
)
from app.services.parser.models import AlgorithmIR, FunctionIR, LoopBound

# Re-exported for convenience.
from app.services.complexity.classes import ComplexityClass, Cost  # noqa: F401


def _cls(key: str) -> ComplexityClass:
    return COMPLEXITY_CLASSES[key]


# --------------------------------------------------------------------------- #
# Report models
# --------------------------------------------------------------------------- #
@dataclass
class CaseComplexity:
    """Time complexity per input case."""

    best: ComplexityClass
    average: ComplexityClass
    worst: ComplexityClass


@dataclass
class SpaceReport:
    """Memory usage analysis."""

    auxiliary: ComplexityClass          # extra memory beyond the input
    total: ComplexityClass              # including the input itself
    recursion_depth: ComplexityClass | None = None
    explanations: list[str] = field(default_factory=list)


@dataclass
class ComplexityReport:
    """Full complexity analysis of one algorithm."""

    time: CaseComplexity
    space: SpaceReport
    pattern: str = "iterative"
    recurrence: str | None = None
    explanations: list[str] = field(default_factory=list)
    confidence: float = 1.0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover
        return "<expr>"


METHOD_COSTS: dict[str, Cost] = {
    "sort": BUILTIN_COSTS["sort"],
    "extend": COST_N,
    "join": COST_N,
    "append": COST_0,
    "pop": COST_0,
    "popleft": COST_0,
    "get": COST_0,
    "add": COST_0,
    "insert": COST_0,
    "remove": COST_N,
    "index": COST_N,
    "count": COST_N,
    "reverse": COST_N,
    "items": COST_N,
}


class ComplexityAnalyzer:
    """Computes best/average/worst time complexity and space complexity."""

    # ------------------------------------------------------------------ cost
    def _compute_local_costs(self, ir: AlgorithmIR) -> dict[str, Cost]:
        """Iterative cost of every local function (self-recursion excluded)."""
        costs: dict[str, Cost] = {}
        for fn in ir.functions:
            if fn.ast_node is None or fn.name in costs:
                continue
            costs[fn.name] = self._function_cost(fn.ast_node, fn.name, ir, costs, set())
        return costs

    def _function_cost(
        self,
        node: ast.AST,
        owner: str,
        ir: AlgorithmIR,
        costs: dict[str, Cost],
        visiting: set[str],
    ) -> Cost:
        """Cost of a function body: max over its statements."""
        body = node.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else node
        total = COST_0
        for stmt in body:
            total = Cost.maximum(total, self._stmt_cost(stmt, owner, ir, costs, visiting))
        return total

    def _stmt_cost(
        self,
        stmt: ast.AST,
        owner: str,
        ir: AlgorithmIR,
        costs: dict[str, Cost],
        visiting: set[str],
    ) -> Cost:
        if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            bound = self._loop_bound_cost(stmt)
            body = COST_0
            for inner in stmt.body:
                body = Cost.maximum(body, self._stmt_cost(inner, owner, ir, costs, visiting))
            for inner in stmt.orelse:
                body = Cost.maximum(body, self._stmt_cost(inner, owner, ir, costs, visiting))
            return bound.mul(body)
        if isinstance(stmt, ast.If):
            body = COST_0
            for inner in stmt.body + stmt.orelse:
                body = Cost.maximum(body, self._stmt_cost(inner, owner, ir, costs, visiting))
            return Cost.maximum(COST_0, body)
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Expr)):
            value = stmt.value if hasattr(stmt, "value") and stmt.value is not None else None
            return self._expr_cost(value, owner, ir, costs, visiting) if value is not None else COST_0
        if isinstance(stmt, (ast.With, ast.AsyncWith, ast.Try, ast.TryStar)):
            body = COST_0
            for inner in ast.iter_child_nodes(stmt):
                if isinstance(inner, ast.stmt):
                    body = Cost.maximum(body, self._stmt_cost(inner, owner, ir, costs, visiting))
            return body
        if isinstance(stmt, ast.FunctionDef):
            return COST_0  # nested definitions are free to define
        # Fallback: recurse into child statements.
        body = COST_0
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.stmt):
                body = Cost.maximum(body, self._stmt_cost(child, owner, ir, costs, visiting))
        return body

    def _loop_bound_cost(self, node: ast.For | ast.While) -> Cost:
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and _name(it.func) == "range":
                stop = it.args[1] if len(it.args) >= 2 else (it.args[0] if it.args else None)
                if isinstance(stop, ast.Constant):
                    return COST_0
                return COST_N
            return COST_N  # iterating a collection
        # while: halving pattern → log, otherwise worst-case linear
        return COST_LOG if self._is_halving_while(node) else COST_N

    def _is_halving_while(self, node: ast.While) -> bool:
        """Detect search-space halving inside a while loop."""
        test_vars = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        geometric = False
        mid_var: str | None = None
        for sub in ast.walk(node):
            if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name):
                if sub.target.id in test_vars and isinstance(
                    sub.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.RShift)
                ):
                    geometric = True
            if isinstance(sub, ast.Assign):
                for tgt in sub.targets:
                    if isinstance(tgt, ast.Name) and isinstance(sub.value, ast.BinOp) and isinstance(
                        sub.value.op, (ast.FloorDiv, ast.RShift, ast.Div)
                    ):
                        # mid = (low + high) // 2 style
                        mid_var = tgt.id
                    if (
                        isinstance(tgt, ast.Name)
                        and mid_var
                        and isinstance(sub.value, ast.Name)
                        and sub.value.id == mid_var
                        and tgt.id in test_vars
                    ):
                        geometric = True
                    if (
                        isinstance(tgt, ast.Name)
                        and mid_var
                        and isinstance(sub.value, ast.BinOp)
                        and isinstance(sub.value.op, (ast.Add, ast.Sub))
                        and isinstance(sub.value.left, ast.Name)
                        and sub.value.left.id == mid_var
                        and tgt.id in test_vars
                    ):
                        geometric = True  # low = mid + 1 / high = mid - 1
        return geometric

    def _expr_cost(
        self,
        expr: ast.AST | None,
        owner: str,
        ir: AlgorithmIR,
        costs: dict[str, Cost],
        visiting: set[str],
    ) -> Cost:
        if expr is None:
            return COST_0

        if isinstance(expr, ast.Call):
            return self._call_cost(expr, owner, ir, costs, visiting)

        if isinstance(expr, ast.Subscript) and isinstance(expr.slice, ast.Slice):
            return COST_N  # slicing copies the sequence

        if isinstance(expr, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            total = COST_0
            for gen in expr.generators:
                total = total.mul(COST_N)
            for child in ast.iter_child_nodes(expr):
                if isinstance(child, ast.expr):
                    total = Cost.maximum(total, self._expr_cost(child, owner, ir, costs, visiting))
            return total

        if isinstance(expr, ast.Compare):
            # `x in collection` performs a linear membership scan on lists/tuples
            # (O(1) on sets/dicts, detected through cache-like variable names).
            for op, comp in zip(expr.ops, expr.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    comp_name = _name(comp)
                    if comp_name and any(k in comp_name.lower() for k in ("cache", "memo", "seen", "visited")):
                        continue
                    return COST_N
            return COST_0

        if isinstance(expr, ast.BoolOp):
            total = COST_0
            for v in expr.values:
                total = Cost.maximum(total, self._expr_cost(v, owner, ir, costs, visiting))
            return total

        if isinstance(expr, ast.IfExp):
            return Cost.maximum(
                self._expr_cost(expr.body, owner, ir, costs, visiting),
                self._expr_cost(expr.orelse, owner, ir, costs, visiting),
            )

        if isinstance(expr, ast.BinOp):
            return Cost.maximum(
                self._expr_cost(expr.left, owner, ir, costs, visiting),
                self._expr_cost(expr.right, owner, ir, costs, visiting),
            )

        # Generic expression: scan children for calls / comprehensions.
        total = COST_0
        for child in ast.iter_child_nodes(expr):
            if isinstance(child, ast.expr):
                total = Cost.maximum(total, self._expr_cost(child, owner, ir, costs, visiting))
        return total

    def _call_cost(
        self,
        call: ast.Call,
        owner: str,
        ir: AlgorithmIR,
        costs: dict[str, Cost],
        visiting: set[str],
    ) -> Cost:
        fname = _name(call.func)
        args_cost = COST_0
        for arg in call.args + [kw.value for kw in call.keywords]:
            args_cost = Cost.maximum(args_cost, self._expr_cost(arg, owner, ir, costs, visiting))

        if fname == owner:
            # Self-recursive call: the recurrence solver handles the call itself;
            # only the argument evaluation cost (e.g. slicing) is counted here.
            return args_cost

        if fname in BUILTIN_COSTS:
            return Cost.maximum(BUILTIN_COSTS[fname], args_cost)

        if fname in ir.local_functions and fname not in visiting:
            visiting = visiting | {fname}
            local = self._function_cost(
                ir.local_functions[fname].ast_node, fname, ir, costs, visiting
            )
            return Cost.maximum(local, args_cost)

        if isinstance(call.func, ast.Attribute) and call.func.attr in METHOD_COSTS:
            return Cost.maximum(METHOD_COSTS[call.func.attr], args_cost)

        # Unknown external call: assume O(1) and flag nothing (documented limitation).
        return args_cost

    # ------------------------------------------------------------- recursion
    def _self_call_signatures(self, fn: FunctionIR) -> list[tuple[str, str]]:
        """For each self-recursive call, (op, base-variable) of its shrinking arg."""
        if fn.ast_node is None:
            return []
        sigs: list[tuple[str, str]] = []
        for sub in ast.walk(fn.ast_node):
            if isinstance(sub, ast.Call) and _name(sub.func) == fn.name:
                for arg in sub.args:
                    if isinstance(arg, ast.BinOp) and isinstance(
                        arg.op, (ast.Add, ast.Sub)
                    ) and _name(arg.left) is not None:
                        sigs.append((type(arg.op).__name__, _name(arg.left)))
        return sigs

    def _multi_recursion_kind(self, fn: FunctionIR) -> str:
        """Classify multi-branch recursion: disjoint partitions vs overlapping."""
        sigs = self._self_call_signatures(fn)
        if not sigs:
            return "unknown"
        ops = {op for op, _ in sigs}
        bases = {base for _, base in sigs}
        if "Add" in ops and "Sub" in ops and len(bases) <= 2:
            # pivot-1 / pivot+1 style: subproblems partition the input.
            return "partition"
        if len(bases) == 1 and ops == {"Sub"}:
            # n-1 / n-2 style: overlapping subproblems.
            return "overlapping"
        return "unknown"

    def _master_theorem(self, a: int, b: float, f: Cost) -> tuple[Cost, str]:
        """Solve T(n) = a·T(n/b) + Θ(f(n)) returning (total, explanation)."""
        c = math.log(a, b) if a > 1 else 0.0
        crit = Cost(round(c * 2) / 2, False)
        if f.rank < c - 0.25:
            total, case = crit, 1
        elif abs(f.rank - c) <= 0.25:
            total, case = Cost(round(c * 2) / 2, True), 2
        else:
            total, case = f, 3
        explanation = (
            f"Master Theorem: T(n) = {a}·T(n/{b:g}) + {f.theta_label()} with "
            f"log_{b:g}({a}) = {c:.2f}; f(n) {'<' if case == 1 else ('≈' if case == 2 else '>')} "
            f"n^{c:.2f} → Case {case} → T(n) = {total.theta_label()}."
        )
        return total, explanation

    # ----------------------------------------------------------------- space
    def _space_report(self, fn: FunctionIR, ir: AlgorithmIR, stack: Cost) -> SpaceReport:
        explanations: list[str] = []
        alloc = COST_0
        for allocation in fn.allocations:
            if allocation.size == "linear":
                alloc = Cost.maximum(alloc, COST_N)
            elif allocation.size == "unknown":
                if allocation.kind == "dict" and fn.memoized:
                    alloc = Cost.maximum(alloc, COST_N)
                else:
                    alloc = Cost.maximum(alloc, COST_N)
            # constant allocations are dominated by COST_0
        if fn.max_loop_depth >= 1 and any(a.kind == "list" and a.size == "linear" for a in fn.allocations):
            explanations.append(
                "A linear-size auxiliary collection is allocated (result buffer / merge buffer), "
                "contributing Θ(n) auxiliary space."
            )
        if fn.memoized:
            explanations.append(
                "A memoisation table stores one entry per distinct state → Θ(n) additional space "
                "(amortised across calls)."
            )

        stack_class = stack.to_class() if fn.is_recursive else None
        if fn.is_recursive:
            explanations.append(
                f"Recursion depth is {stack.theta_label()}; each frame holds O(1) locals, so the "
                f"call stack contributes {stack.theta_label()} space."
            )

        aux = Cost.maximum(alloc, stack if fn.is_recursive else COST_0)
        input_is_collection = any(a.kind == "iterable" for a in fn.args)
        total = Cost.maximum(aux, COST_N) if input_is_collection else aux
        if input_is_collection and aux.rank < 1:
            explanations.append(
                "The algorithm operates in place: auxiliary memory is O(1) beyond the Θ(n) input."
            )
        return SpaceReport(
            auxiliary=aux.to_class(),
            total=total.to_class(),
            recursion_depth=stack_class,
            explanations=explanations,
        )

    # ---------------------------------------------------------------- analyze
    def analyze(self, ir: AlgorithmIR) -> ComplexityReport:
        fn = ir.primary
        if fn is None:
            return ComplexityReport(
                time=CaseComplexity(_cls("linear"), _cls("linear"), _cls("linear")),
                space=SpaceReport(_cls("constant"), _cls("linear"), None,
                                  ["No analysable structure found; assumed linear."]),
                confidence=ir.confidence,
            )

        local_costs = self._compute_local_costs(ir)
        f = local_costs.get(fn.name, COST_0)
        if fn.ast_node is None:
            # Heuristic backends (pseudocode / natural language) have no AST:
            # derive the per-call work from the extracted loop structure.
            f = self._cost_from_loop_infos(fn)

        # --- explicitly stated complexity (natural-language mode) ---------------
        if fn.estimated_time:
            def lookup(k: str) -> ComplexityClass:
                return COMPLEXITY_CLASSES.get(k, COMPLEXITY_CLASSES["linear"])

            return ComplexityReport(
                time=CaseComplexity(
                    lookup(fn.estimated_time.get("best", "linear")),
                    lookup(fn.estimated_time.get("average", "linear")),
                    lookup(fn.estimated_time.get("worst", "linear")),
                ),
                space=self._space_report(fn, ir, COST_LOG if fn.is_recursive else COST_0),
                pattern="as described (natural-language estimate)",
                recurrence=None,
                explanations=[
                    "The complexity was extracted from an explicit statement in the natural-language "
                    "description; structural analysis alone cannot fully verify it.",
                ],
                confidence=ir.confidence,
            )

        # --- recognizers first -------------------------------------------------
        for recognizer in (_recognize_quick_sort, _recognize_adaptive_sort, _recognize_graph_traversal):
            report = recognizer(fn, ir, f, local_costs, self)
            if report is not None:
                report.confidence = ir.confidence
                return report

        explanations: list[str] = []
        loop_notes = self._loop_explanations(fn)
        explanations.extend(loop_notes)

        # --- recursion analysis ----------------------------------------------
        if fn.is_recursive:
            kind = self._multi_recursion_kind(fn)
            if fn.memoized:
                worst = COST_N.mul(f)
                average = best = worst
                pattern = "dynamic programming (memoised recursion)"
                explanations.append(
                    "Recursion with memoisation: each distinct state is computed once, so the "
                    f"Θ(n) states dominate → T(n) = Θ(n) · {f.theta_label()} = {worst.theta_label()}."
                )
                recurrence = f"T(n) = {f.theta_label()} per state, Θ(n) states"
                stack = COST_N
            elif fn.recursion_shrink == "half":
                a = max(fn.recursion_branching, 1)
                worst, master = self._master_theorem(a, 2.0, f)
                explanations.append(master)
                best = average = worst  # divide & conquer is input-order independent
                pattern = "divide-and-conquer"
                shrink_note = (
                    f"The function calls itself {a} time(s) on half the input "
                    "(n/2 via mid-point slicing or n//2)."
                )
                explanations.insert(0, shrink_note)
                recurrence = f"T(n) = {a}·T(n/2) + {f.theta_label()}"
                stack = COST_LOG
            elif fn.recursion_branching >= 2 and kind == "overlapping":
                worst_class = _cls("exponential")
                # Growth is driven by n alone (not data order), so all cases
                # are exponential beyond the trivial base case.
                best = average = None  # sentinel: reuse worst_class below
                pattern = "branching recursion with overlapping subproblems"
                fib_note = (
                    "Each call spawns multiple recursive calls on slightly smaller inputs whose "
                    "subproblems overlap, so the call tree grows exponentially: T(n) = T(n-1) + "
                    f"T(n-2) + {f.theta_label()} → Θ(φⁿ) ≈ Θ(1.618ⁿ) in the Fibonacci case."
                    if {"fib", "fibonacci"} & fn.hints
                    else "Overlapping recursive subproblems recompute shared states → exponential "
                         f"call-tree growth (≈ Θ({max(fn.recursion_branching, 2)}ⁿ))."
                )
                explanations.insert(0, fib_note)
                recurrence = f"T(n) = {fn.recursion_branching}·T(n-k) + {f.theta_label()}"
                space = self._space_report(fn, ir, COST_N)
                return ComplexityReport(
                    time=CaseComplexity(worst_class, worst_class, worst_class),
                    space=space,
                    pattern=pattern,
                    recurrence=recurrence,
                    explanations=explanations,
                    confidence=ir.confidence,
                )
            elif fn.recursion_branching >= 2 and kind in {"partition", "unknown"}:
                # Quick-sort-like shape handled generically: balanced on average,
                # degenerate in the worst case.
                average = Cost.maximum(f, COST_N_LOG)
                worst = f.mul(COST_N)
                best = average
                pattern = "divide-and-conquer with data-dependent splits"
                explanations.insert(
                    0,
                    "Two recursive calls partition the input into disjoint parts. With balanced "
                    f"splits T(n) = 2·T(n/2) + {f.theta_label()} → {average.theta_label()} on average.",
                )
                explanations.append(
                    "In the worst case each split is maximally unbalanced (a 0 : n-1 partition), "
                    f"giving T(n) = T(n-1) + {f.theta_label()} → {worst.theta_label()}."
                )
                recurrence = f"T(n) = 2·T(n/2) + {f.theta_label()}, worst T(n) = T(n-1) + {f.theta_label()}"
                stack = COST_LOG
            else:
                # Linear recursion: T(n) = T(n-1) + f(n)
                worst = Cost(f.deg + 1, f.log)
                best = average = worst
                pattern = "linear recursion"
                explanations.insert(
                    0,
                    f"The function recurses once on a reduced input (n-1): "
                    f"T(n) = T(n-1) + {f.theta_label()} = Θ(n · {f.label()}) = {worst.theta_label()}.",
                )
                recurrence = f"T(n) = T(n-1) + {f.theta_label()}"
                stack = COST_N
        else:
            worst = f
            best = f
            # Data-dependent early exit inside a single loop → O(1) best case.
            if fn.early_exit and fn.max_loop_depth == 1 and f.rank >= 1:
                best = COST_0
                explanations.append(
                    "The loop returns as soon as a condition on the data holds → best case O(1) "
                    "(match found immediately); the expected and worst cases remain Θ(n)."
                )
            average = worst
            if f.rank < 1:
                pattern = "constant-time structure"
            elif f.rank == 1:
                pattern = "single pass"
            elif f.rank <= 1.5:
                pattern = "linearithmic (sort-like) pass"
            else:
                pattern = "nested iteration" if fn.max_loop_depth >= 2 else "heavy per-element work"
            stack = COST_0

        space = self._space_report(fn, ir, stack if fn.is_recursive else COST_0)
        return ComplexityReport(
            time=CaseComplexity(best.to_class(), average.to_class(), worst.to_class()),
            space=space,
            pattern=pattern,
            recurrence=recurrence if fn.is_recursive else None,
            explanations=explanations,
            confidence=ir.confidence,
        )

    @staticmethod
    def _cost_from_loop_infos(fn: FunctionIR) -> Cost:
        """Approximate iterative cost from LoopInfo records (no AST available)."""
        if not fn.loops:
            return COST_0
        bounds_by_depth: dict[int, Cost] = {}
        table = {LoopBound.N.value: COST_N, LoopBound.LOG.value: COST_LOG,
                 LoopBound.CONSTANT.value: COST_0, LoopBound.UNKNOWN.value: COST_N}
        for loop in fn.loops:
            raw = loop.bound.value if isinstance(loop.bound, LoopBound) else loop.bound
            cost = table.get(raw, COST_N)
            current = bounds_by_depth.get(loop.depth)
            bounds_by_depth[loop.depth] = cost if current is None else Cost.maximum(current, cost)
        total = COST_0
        for depth in range(1, fn.max_loop_depth + 1):
            total = total.mul(bounds_by_depth.get(depth, COST_N))
        return total

    def _loop_explanations(self, fn: FunctionIR) -> list[str]:
        """Human-readable summary of the loop structure that drives the cost."""
        notes: list[str] = []
        if not fn.loops:
            return notes
        deepest = fn.max_loop_depth
        if deepest >= 2:
            notes.append(
                f"Nested loops detected: {len(fn.loops)} loop(s) with a maximum nesting depth of "
                f"{deepest}; each level multiplies the work by a factor of n → Θ(n^{deepest})."
            )
        elif deepest == 1:
            bounds = {l.bound.value for l in fn.loops}
            if "log" in bounds:
                notes.append(
                    "A single loop whose index grows geometrically (doubles/halves) → Θ(log n) iterations."
                )
            elif "constant" in bounds and bounds <= {"constant"}:
                notes.append("Only constant-bounded loops were detected → Θ(1) iteration count.")
            else:
                notes.append("A single loop scans the input once → Θ(n) iterations.")
        if fn.conditionals:
            notes.append(
                f"{fn.conditionals} conditional branch(es) add O(1) comparisons per iteration."
            )
        return notes


# --------------------------------------------------------------------------- #
# Pattern recognizers
# --------------------------------------------------------------------------- #
def _recognize_quick_sort(
    fn: FunctionIR, ir: AlgorithmIR, f: Cost, costs: dict[str, Cost], analyzer: ComplexityAnalyzer
) -> ComplexityReport | None:
    """Quick sort family: partition + two recursive calls on disjoint parts."""
    structural = fn.is_recursive and fn.recursion_branching >= 2 and analyzer._multi_recursion_kind(fn) == "partition"
    named = fn.is_recursive and ({"quick", "quicksort", "partition", "pivot"} & fn.hints)
    if not (structural or named):
        return None

    avg = Cost.maximum(f, COST_N_LOG)
    worst = f.mul(COST_N)
    builds_new_lists = any(a.kind in {"list", "slice"} and a.size == "linear" for a in fn.allocations)
    stack = COST_LOG
    explanations = [
        "Quick sort pattern detected: an O(n) partitioning pass around a pivot, followed by two "
        "recursive calls on the disjoint sub-parts.",
        f"Average case: balanced splits give T(n) = 2·T(n/2) + {f.theta_label()} → Θ(n log n) "
        "(Master Theorem, Case 2).",
        f"Worst case: if the pivot is consistently the smallest/largest element (e.g. already-sorted "
        f"input with a naive pivot), partitions degenerate to 0 : n-1 and T(n) = T(n-1) + {f.theta_label()} "
        f"→ {worst.theta_label()}.",
    ]
    if builds_new_lists:
        space = SpaceReport(
            auxiliary=_cls("linear"),
            total=_cls("linear"),
            recursion_depth=_cls("log_n"),
            explanations=explanations + [
                "This variant builds new lists for the partitions → Θ(n) auxiliary space per level."
            ],
        )
    else:
        space = SpaceReport(
            auxiliary=_cls("log_n"),
            total=_cls("linear"),
            recursion_depth=_cls("log_n"),
            explanations=explanations + [
                "Partitioning is done in place (swaps only) → auxiliary memory is just the recursion "
                "stack, Θ(log n) on average (Θ(n) in the degenerate worst case)."
            ],
        )
    return ComplexityReport(
        time=CaseComplexity(avg.to_class(), avg.to_class(), worst.to_class()),
        space=space,
        pattern="divide-and-conquer (partition-based)",
        recurrence=f"T(n) = 2·T(n/2) + {f.theta_label()}, worst T(n) = T(n-1) + {f.theta_label()}",
        explanations=explanations,
        confidence=ir.confidence,
    )


def _recognize_adaptive_sort(
    fn: FunctionIR, ir: AlgorithmIR, f: Cost, costs: dict[str, Cost], analyzer: ComplexityAnalyzer
) -> ComplexityReport | None:
    """Bubble/insertion-style sorts: Θ(n²) worst, Θ(n) best on sorted input."""
    if not ({"bubble", "insertion", "selection"} & fn.hints) and "swapped" not in ir.source.lower():
        return None
    if fn.is_recursive or fn.max_loop_depth < 2:
        return None
    if f.rank < 1.75:  # not quadratic-ish
        return None

    source = ir.source.lower()
    adaptive = "swapped" in source or any(l.kind == "while" and l.depth >= 2 for l in fn.loops)
    selection = "selection" in fn.hints or "min_idx" in source.replace(" ", "_")
    best = f if (not adaptive or selection) else COST_N

    explanations = [
        f"Two nested loops over the input → Θ(n²) comparisons in the worst case "
        f"(Σᵢ (n-i) ≈ n²/2 = Θ(n²)).",
    ]
    if adaptive and not selection:
        explanations.append(
            "The inner loop terminates early when the data is already ordered (swap flag / shifted "
            "key) → best case Θ(n) on sorted input."
        )
    else:
        explanations.append(
            "Both loops run their full length regardless of the data → Θ(n²) in every case "
            "(the algorithm is not adaptive)."
        )
    avg = f if (not adaptive or selection) else f
    return ComplexityReport(
        time=CaseComplexity(best.to_class(), avg.to_class(), f.to_class()),
        space=SpaceReport(
            auxiliary=_cls("constant"),
            total=_cls("linear"),
            explanations=["Sorting is performed in place through swaps → O(1) auxiliary space."],
        ),
        pattern="exchange sort (nested iteration)",
        recurrence=None,
        explanations=explanations,
        confidence=ir.confidence,
    )


def _recognize_graph_traversal(
    fn: FunctionIR, ir: AlgorithmIR, f: Cost, costs: dict[str, Cost], analyzer: ComplexityAnalyzer
) -> ComplexityReport | None:
    """BFS/DFS style traversal: every vertex and edge is processed once."""
    hints = fn.hints | {h for h in ir.source.lower().split() }
    graph_hints = {"graph", "bfs", "dfs", "visited", "adjacency", "neighbors", "neighbours", "vertex", "dijkstra"}
    if not (graph_hints & hints):
        return None
    uses_queue = {"queue", "deque", "popleft", "appendleft", "stack"} & set(fn.data_structures) | (
        {"queue", "stack", "deque"} & fn.hints
    )
    if not uses_queue and not fn.loops:
        return None

    graph_class = ComplexityClass("v_plus_e", "O(V + E)", 5,
                                  "Linear in the size of the graph")
    explanations = [
        "Graph traversal pattern detected: a queue/stack visits every vertex once (guarded by a "
        "visited set) and scans every outgoing edge exactly once.",
        "Total work = Θ(|V|) dequeues + Θ(|E|) edge inspections → Θ(V + E); with n = |V| + |E| "
        "this is linear in the input size.",
        "The visited set stores one entry per vertex → Θ(V) auxiliary space; the frontier holds at "
        "most Θ(V) vertices.",
    ]
    return ComplexityReport(
        time=CaseComplexity(graph_class, graph_class, graph_class),
        space=SpaceReport(_cls("linear"), _cls("linear"), None, explanations),
        pattern="graph traversal",
        recurrence=None,
        explanations=explanations,
        confidence=ir.confidence,
    )
