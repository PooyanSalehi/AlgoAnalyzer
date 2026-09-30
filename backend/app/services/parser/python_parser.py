"""Python source parser built on the standard-library ``ast`` module.

Extracts a structural fingerprint of every function definition:
loops (with nesting depth and iteration bounds), recursion (call sites,
branching factor, argument shrink factor), conditionals, early exits,
heap allocations, builtin/method calls, data structures, operations and
semantic keyword hints.

Everything is normalised into :class:`FunctionIR` objects, which the rest
of the pipeline consumes.
"""
from __future__ import annotations

import ast
from collections import Counter

from app.services.parser.keywords import ALL_PURPOSE_KEYWORDS, PURPOSE_KEYWORDS
from app.services.parser.models import (
    AlgorithmIR,
    AllocationInfo,
    ArgInfo,
    FunctionIR,
    InputMode,
    LoopBound,
    LoopInfo,
)

#: Builtins whose asymptotic cost is modelled by the complexity analyzer.
TRACKED_BUILTINS = {
    "len", "sorted", "sort", "sum", "min", "max", "abs", "pow", "range",
    "enumerate", "zip", "map", "filter", "reversed", "list", "set", "dict",
    "tuple", "any", "all", "join", "round", "divmod", "bin", "int", "float",
    "str", "bool",
}

TRACKED_METHODS = {
    "append", "extend", "insert", "pop", "remove", "sort", "reverse", "count",
    "index", "get", "items", "keys", "values", "setdefault", "add", "update",
    "heappush", "heappop", "push", "popleft", "appendleft", "join", "split",
}

_COMMON_ENTRY_NAMES = {"main", "solve", "run", "analyze", "algorithm", "sort", "search", "compute"}


def _name_of(node: ast.expr) -> str | None:
    """Return the plain identifier behind an expression, if any."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)  # Python >= 3.9
    except Exception:  # pragma: no cover - defensive
        return "<expr>"


class _FunctionAnalyzer:
    """Extracts a :class:`FunctionIR` from one ``ast.FunctionDef`` node."""

    def __init__(self, node: ast.FunctionDef, all_hints: set[str]):
        self.node = node
        self.module_hints = all_hints
        self.loop_depth = 0
        self.loops: list[LoopInfo] = []
        self.returns: list[str] = []
        self.allocations: list[AllocationInfo] = []
        self.builtins: Counter[str] = Counter()
        self.methods: Counter[str] = Counter()
        self.structures: set[str] = set()
        self.operations: Counter[str] = Counter()
        self.conditionals = 0
        self.early_exit = False
        self.recursive_calls: list[ast.Call] = []
        self.self_call_args: list[list[ast.expr]] = []
        self.memoized = "lru_cache" in _unparse(node).lower() or "functools.cache" in _unparse(node)
        self.assigned_types: dict[str, str] = {}  # var name -> inferred value kind
        self.hints: set[str] = set()
        self.args: list[ArgInfo] = []  # filled by analyze()
        # Variables assigned a geometric reduction, e.g. mid = len(arr) // 2.
        # Used to classify recursion shrink: merge_sort(arr[:mid]) halves the input.
        self.halving_vars: set[str] = set()

    # ------------------------------------------------------------------ args
    def _extract_args(self) -> list[ArgInfo]:
        args: list[ArgInfo] = []
        positional = list(self.node.args.posonlyargs) + list(self.node.args.args)
        defaults = list(self.node.args.defaults)
        offset = len(positional) - len(defaults)  # defaults align to the tail
        for i, a in enumerate(positional):
            annotation = _unparse(a.annotation) if a.annotation else None
            args.append(ArgInfo(
                name=a.arg,
                kind=self._classify_arg(a.arg, annotation),
                annotation=annotation,
                has_default=i >= offset,
            ))
        for a in self.node.args.kwonlyargs:
            annotation = _unparse(a.annotation) if a.annotation else None
            args.append(ArgInfo(
                name=a.arg,
                kind=self._classify_arg(a.arg, annotation),
                annotation=annotation,
                has_default=a.default is not None,
            ))
        return args

    def _classify_arg(self, name: str, annotation: str | None) -> str:
        ann = (annotation or "").lower()
        if "list" in ann or "tuple" in ann or "iterable" in ann or "sequence" in ann:
            return "iterable"
        if ann.startswith("int") or ann == "int":
            return "int"
        if "float" in ann or "num" in ann:
            return "number"
        if "str" in ann:
            return "string"
        if "graph" in ann or "adjacency" in ann:
            return "graph"
        if "bool" in ann:
            return "boolean"
        # Heuristic: singular variable names are sizes, plural/collection-like are containers.
        lowered = name.lower()
        if lowered in {"graph", "adjacency", "adj", "network", "g"}:
            return "graph"
        if lowered.endswith(("s", "list", "arr", "data", "items")) and len(lowered) > 2:
            return "iterable"
        if lowered in {"n", "size", "count", "num", "k", "m", "len", "length", "target",
                       "x", "i", "j", "low", "high", "lo", "hi", "left", "right", "mid",
                       "idx", "index", "start", "end", "first", "last"}:
            return "int"
        return "unknown"

    # ----------------------------------------------------------------- loops
    def _loop_bound(self, node: ast.For | ast.While) -> tuple[LoopBound, str]:
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and _name_of(it.func) == "range":
                stop = it.args[1] if len(it.args) >= 2 else (it.args[0] if it.args else None)
                if isinstance(stop, ast.Constant):
                    return LoopBound.CONSTANT, f"fixed {len(it.args)}-arg range bound ({_unparse(stop)})"
                if stop is not None and self._is_size_expr(stop):
                    return LoopBound.N, f"iterates over range({_unparse(stop)})"
                return LoopBound.N, f"range({_unparse(it)})"
            if isinstance(it, ast.Call) and _name_of(it.func) in {"enumerate", "zip", "reversed", "sorted"}:
                return LoopBound.N, f"iterates over {_name_of(it.func)}(...)"
            return LoopBound.N, "iterates directly over a collection"
        # while loop: look for geometric index updates (i *= 2, i //= 2, i >>= 1 ...)
        if self._halving_while(node):
            return LoopBound.LOG, "loop index multiplies/divides by a constant each iteration"
        return LoopBound.UNKNOWN, "data-dependent while condition (worst case assumed linear)"

    def _is_size_expr(self, node: ast.AST) -> bool:
        """True for expressions whose value scales with the input size (n)."""
        if isinstance(node, ast.Name):
            return True  # params are size-like unless proven constant
        if isinstance(node, ast.Call) and _name_of(node.func) == "len":
            return True
        if isinstance(node, ast.BinOp):
            return self._is_size_expr(node.left) or self._is_size_expr(node.right)
        return False

    def _halving_while(self, node: ast.While) -> bool:
        test_names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        for sub in ast.walk(node):
            if isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Name) and sub.target.id in test_names:
                if isinstance(sub.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.RShift, ast.LShift)):
                    return True
            if isinstance(sub, ast.Assign):
                for tgt in sub.targets:
                    if isinstance(tgt, ast.Name) and tgt.id in test_names:
                        if isinstance(sub.value, ast.BinOp) and isinstance(
                            sub.value.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.RShift, ast.LShift)
                        ):
                            return True
        return False

    # --------------------------------------------------------------- visits
    def _visit(self, node: ast.AST, inside_loop: bool = False, depth: int = 0) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                self.loop_depth += 1
                bound, note = self._loop_bound(child)
                self.loops.append(
                    LoopInfo(
                        kind="for" if isinstance(child, (ast.For, ast.AsyncFor)) else "while",
                        depth=self.loop_depth,
                        bound=bound,
                        line=getattr(child, "lineno", 0),
                        note=note,
                    )
                )
                self._visit(child, inside_loop=True)
                self.loop_depth -= 1
            elif isinstance(child, (ast.If, ast.IfExp)):
                self.conditionals += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Return):
                if child.value is not None:
                    self.returns.append(self._value_kind(child.value))
                    if inside_loop:
                        self.early_exit = True
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Call):
                self._visit_call(child)
                self._visit(child, inside_loop)
            elif isinstance(child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                kind = {"ListComp": "list", "SetComp": "set", "GeneratorExp": "list",
                        "DictComp": "dict"}[type(child).__name__]
                self.allocations.append(
                    AllocationInfo(kind=kind, size="linear",
                                   note=f"{kind} comprehension built from an n-sized input")
                )
                self.structures.add(kind)
                self.operations["comprehension"] += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.List):
                self.allocations.append(AllocationInfo(kind="list", size="constant", note="literal list"))
                self.structures.add("list")
                self._visit(child, inside_loop)
            elif isinstance(child, (ast.Dict, ast.DictComp)):
                self.allocations.append(AllocationInfo(kind="dict", size="unknown", note="dict literal"))
                self.structures.add("dict")
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Set):
                self.structures.add("set")
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Subscript) and isinstance(child.slice, ast.Slice):
                self.allocations.append(
                    AllocationInfo(kind="slice", size="linear", note=f"slice {_unparse(child)} copies data")
                )
                self._visit(child, inside_loop)
            elif isinstance(child, ast.BinOp):
                self.operations[type(child.op).__name__] += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Compare):
                self.operations[type(child.ops[0]).__name__] += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Subscript):
                self.operations["IndexAccess"] += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.Assign):
                self._record_assignment(child)
                self._visit(child, inside_loop)
            elif isinstance(child, ast.AugAssign):
                self.operations[type(child.op).__name__] += 1
                self._visit(child, inside_loop)
            elif isinstance(child, ast.FunctionDef):
                continue  # nested defs are analysed separately
            else:
                self._visit(child, inside_loop)

    def _visit_call(self, call: ast.Call) -> None:
        fname = _name_of(call.func)
        if fname == self.node.name:
            self.recursive_calls.append(call)
            self.self_call_args.append(list(call.args))
        elif fname in TRACKED_BUILTINS:
            self.builtins[fname] += 1
            if fname in {"sorted", "sort"}:
                self.structures.add("list")
                self.hints.update(PURPOSE_KEYWORDS["sorting"])
            if fname in {"list", "set", "dict", "tuple"}:
                self.structures.add(fname)
        elif fname is None and isinstance(call.func, ast.Attribute):
            if call.func.attr in TRACKED_METHODS:
                self.methods[call.func.attr] += 1
                if call.func.attr in {"append", "extend", "insert"}:
                    self.structures.add("list")
                if call.func.attr in {"get", "setdefault", "items", "keys", "values"}:
                    self.structures.add("dict")
                if call.func.attr == "add":
                    self.structures.add("set")
                if call.func.attr in {"heappush", "heappop"}:
                    self.structures.add("heap")
                if call.func.attr in {"popleft", "appendleft"}:
                    self.structures.add("deque")

    def _record_assignment(self, node: ast.Assign) -> None:
        kind = self._value_kind(node.value)
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                self.assigned_types[tgt.id] = kind
                # mid = (low + high) // 2 or mid = len(arr) // 2 → halving variable
                if isinstance(node.value, ast.BinOp) and isinstance(
                    node.value.op, (ast.FloorDiv, ast.RShift, ast.Div)
                ):
                    self.halving_vars.add(tgt.id)
        # `cache = {}` / `memo = {}` → memoisation table.
        if isinstance(node.value, (ast.Dict, ast.DictComp)):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id.lower() in {"cache", "memo", "memo_", "table", "dp"}:
                    self.memoized = True
                    self.allocations.append(
                        AllocationInfo(kind="dict", size="linear", note=f"'{tgt.id}' memoisation table")
                    )

    def _value_kind(self, node: ast.AST) -> str:
        if isinstance(node, (ast.ListComp,)):
            return "list"
        if isinstance(node, ast.DictComp):
            return "dict"
        if isinstance(node, ast.SetComp):
            return "set"
        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "boolean"
            if isinstance(node.value, (int, float)):
                return "number"
            if isinstance(node.value, str):
                return "string"
            return "unknown"
        if isinstance(node, ast.BoolOp) or (
            isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)
        ):
            return "boolean"
        if isinstance(node, ast.Compare):
            return "boolean"
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Add):
                # str + str / list + list concatenation counts as that type.
                if self._value_kind(node.left) in {"string", "list"}:
                    return self._value_kind(node.left)
            return "number"
        if isinstance(node, ast.Call):
            fname = _name_of(node.func)
            if fname == "sorted":
                return "list"
            if fname in {"len", "sum", "abs", "min", "max", "pow", "round", "int", "float"}:
                return "number"
            if fname in {"list", "set", "tuple"}:
                return fname
            if fname == "dict":
                return "dict"
            if fname in {"str", "join"}:
                return "string"
            if isinstance(node.func, ast.Attribute):
                return self._value_kind(node.func.value) if self._value_kind(node.func.value) in {
                    "list", "dict", "set", "string", "tuple"} else "unknown"
            return "unknown"
        if isinstance(node, ast.Subscript):
            return self._value_kind(node.value) if self._value_kind(node.value) in {
                "list", "dict", "set", "string", "tuple"} else "unknown"
        if isinstance(node, ast.Name):
            if node.id in self.assigned_types:
                return self.assigned_types[node.id]
            # Fall back to the declared parameter kind.
            for arg in self.args:
                if arg.name == node.id:
                    return {"iterable": "list", "int": "number", "number": "number",
                            "string": "string", "boolean": "boolean"}.get(arg.kind, "unknown")
            return "unknown"
        return "unknown"

    # ------------------------------------------------------------- recursion
    def _classify_recursion(self) -> tuple[bool, int, str | None]:
        """Detect self-recursion, its branching factor and shrink pattern."""
        if not self.recursive_calls:
            return False, 0, None
        shrinks: list[str] = []
        for args in self.self_call_args:
            shrinks.extend(self._shrink_of_arg(a) for a in args)
        real = [s for s in shrinks if s]
        if not real:
            pattern = "unknown"
        elif all(s == "half" for s in real):
            pattern = "half"
        elif any(s == "half" for s in real):
            pattern = "half"
        else:
            pattern = "linear"
        # Branching = max simultaneous self-calls (capped for sanity).
        return True, min(len(self.recursive_calls), 8), pattern

    def _shrink_of_arg(self, arg: ast.AST) -> str | None:
        """Classify how a recursive call shrinks the problem size."""
        if isinstance(arg, ast.BinOp):
            left_name = _name_of(arg.left)
            # mid - 1 / mid + 1 where mid was computed by halving → half shrink
            if left_name and left_name in self.halving_vars:
                return "half"
            # n - 1 / n - k  → linear shrink
            if isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant):
                return "linear"
            # n // 2, n >> 1, n / 2 → halving
            if isinstance(arg.op, (ast.FloorDiv, ast.RShift, ast.Div)):
                if isinstance(arg.right, ast.Constant) and isinstance(arg.right.value, (int, float)):
                    denom = arg.right.value
                    if denom == 2:
                        return "half"
                    if denom > 2:
                        return "quarter"
                return "half"
        if isinstance(arg, ast.Subscript) and isinstance(arg.slice, ast.Slice):
            # arr[:n//2] / arr[mid:] style halving via slicing
            for part in (arg.slice.lower, arg.slice.upper, arg.slice.step):
                if isinstance(part, ast.BinOp) and isinstance(part.op, (ast.FloorDiv, ast.RShift)):
                    return "half"
                part_name = _name_of(part)
                if part_name and part_name in self.halving_vars:
                    return "half"
            return "linear"  # a slice is at least a constant-size reduction
        if isinstance(arg, ast.Call):
            fname = _name_of(arg.func)
            if fname == "len":
                return "linear"
        return None

    # ------------------------------------------------------------------ main
    def analyze(self) -> FunctionIR:
        self.args = self._extract_args()
        self._visit(self.node)

        source_text = _unparse(self.node).lower()
        token_pool = set()
        for token in self.node.name.replace("_", " ").split():
            token_pool.add(token)
        for sub in ast.walk(self.node):
            if isinstance(sub, ast.Name):
                token_pool.update(sub.id.lower().split("_"))
            elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                token_pool.update(sub.value.lower().split())
        self.hints = {t for t in token_pool if t in ALL_PURPOSE_KEYWORDS}
        if not self.hints:  # fall back to module-level context
            self.hints = {h for h in self.module_hints if h in source_text}

        is_rec, branching, shrink = self._classify_recursion()

        has_size_param = any(
            a.kind in {"iterable", "int"} for a in self.args
        ) and len(self.args) > 0

        # Operating on an iterable parameter is itself data-structure usage.
        if any(a.kind == "iterable" for a in self.args):
            self.structures.add("list")

        return FunctionIR(
            name=self.node.name,
            args=self.args,
            returns=sorted(set(self.returns)) or ["None"],
            loops=self.loops,
            max_loop_depth=max((l.depth for l in self.loops), default=0),
            is_recursive=is_rec,
            recursive_call_count=len(self.recursive_calls),
            recursion_shrink=shrink,
            recursion_branching=branching,
            memoized=self.memoized or self._detect_cache_guard(),
            conditionals=self.conditionals,
            early_exit=self.early_exit,
            allocations=self.allocations,
            builtin_calls=sorted(self.builtins.elements()),
            method_calls=sorted(self.methods.elements()),
            data_structures=sorted(self.structures),
            operations=dict(self.operations),
            hints=self.hints,
            has_size_parameter=has_size_param,
            ast_node=self.node,
        )

    def _detect_cache_guard(self) -> bool:
        """Detect the classic ``if key in cache: return cache[key]`` pattern."""
        for sub in ast.walk(self.node):
            if isinstance(sub, ast.Compare) and any(isinstance(op, ast.In) for op in sub.ops):
                left = _unparse(sub.left).lower()
                if any(k in left for k in ("cache", "memo")):
                    return True
                for comp in sub.comparators:
                    if any(k in _unparse(comp).lower() for k in ("cache", "memo")):
                        return True
        return False


class PythonParser:
    """Parses Python source code into :class:`AlgorithmIR`."""

    def parse(self, source: str, name: str = "Algorithm") -> AlgorithmIR:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:  # re-raised as a domain error by the service layer
            from app.core.errors import ParseError

            raise ParseError(
                f"Python syntax error at line {exc.lineno}, column {exc.offset}: {exc.msg}"
            ) from exc

        imports = [
            _unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
        ]

        functions: list[FunctionIR] = []
        hints_module: set[str] = set()
        lowered = source.lower()
        for keyword_set in PURPOSE_KEYWORDS.values():
            hints_module.update(k for k in keyword_set if k in lowered)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(_FunctionAnalyzer(node, hints_module).analyze())

        local_functions = {f.name: f for f in functions}
        self._propagate_return_types(functions, local_functions)

        primary = self._select_primary(functions)
        line_count = len([l for l in source.splitlines() if l.strip()])

        if primary is None and tree.body:
            # Module-level script (no def) — wrap module body as a pseudo function.
            primary = FunctionIR(
                name="<module>",
                returns=["unknown"],
                hints=hints_module,
                notes=["No function definitions found; module-level code analysed as a whole."],
                ast_node=tree,
            )
            functions.append(primary)
            local_functions[primary.name] = primary

        return AlgorithmIR(
            name=name,
            mode=InputMode.PYTHON,
            source=source,
            functions=functions,
            primary=primary,
            imports=imports,
            line_count=line_count,
            parse_ok=True,
            warnings=[],
            confidence=1.0,
            local_functions=local_functions,
        )

    @staticmethod
    def _propagate_return_types(functions: list[FunctionIR],
                                local_functions: dict[str, FunctionIR]) -> None:
        """If a function returns ``helper(...)``, adopt the helper's return types."""
        changed = True
        while changed:  # fixed-point iteration for chains of helpers
            changed = False
            for fn in functions:
                if "unknown" not in fn.returns or fn.ast_node is None:
                    continue
                for sub in ast.walk(fn.ast_node):
                    if isinstance(sub, ast.Call):
                        callee = local_functions.get(_name_of(sub.func) or "")
                        if callee and callee is not fn:
                            callee_kinds = set(callee.returns) - {"unknown"}
                            if callee_kinds and not callee_kinds <= set(fn.returns):
                                fn.returns = sorted(
                                    (set(fn.returns) - {"unknown"}) | callee_kinds
                                )
                                changed = True

    def _select_primary(self, functions: list[FunctionIR]) -> FunctionIR | None:
        """Heuristically choose the 'entry point' function for complexity analysis."""
        candidates = [f for f in functions if not f.name.startswith("_")]
        if not candidates:
            candidates = functions
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        def score(f: FunctionIR) -> int:
            s = 0
            if f.name.split("_")[0] in _COMMON_ENTRY_NAMES:
                s += 3
            if f.is_recursive:
                s += 2
            if f.has_size_parameter:
                s += 2
            if "helper" in f.name or "swap" in f.name or "partition" in f.name or "merge" == f.name.split("_")[-1]:
                s -= 3
            s += min(f.max_loop_depth, 3)
            s += (1 if f.conditionals else 0)
            return s

        return max(candidates, key=score)
