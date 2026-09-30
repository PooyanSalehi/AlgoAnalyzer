"""Intermediate Representation (IR) shared by every analysis stage.

All parser backends (Python AST, pseudocode, natural language) normalise
their input into :class:`AlgorithmIR`. Downstream services (complexity,
functional, similarity, benchmark) only ever consume the IR, which keeps
the pipeline decoupled from the input format.

The IR is intentionally serialisable: it is embedded in the API response as
the "algorithm overview" section that the frontend renders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InputMode(str, Enum):
    """Supported input formats for algorithm submissions."""

    PYTHON = "python"
    PSEUDOCODE = "pseudocode"
    NATURAL = "natural"


class LoopBound(str, Enum):
    """Classification of how many iterations a loop performs (as a function of n)."""

    N = "n"              # runs n times (e.g. range(len(x)))
    CONSTANT = "constant"  # fixed number of iterations
    LOG = "log"          # index doubles/halves each iteration
    UNKNOWN = "unknown"  # data dependent; assume linear worst case


@dataclass
class ArgInfo:
    """A function parameter with a best-effort inferred type."""

    name: str
    kind: str = "unknown"  # iterable | int | number | string | boolean | unknown
    annotation: str | None = None
    has_default: bool = False  # optional parameters can be omitted when benchmarking


@dataclass
class LoopInfo:
    """One loop occurrence inside a function body."""

    kind: str          # "for" | "while"
    depth: int         # 1-based nesting depth
    bound: LoopBound
    line: int
    note: str = ""


@dataclass
class AllocationInfo:
    """A heap allocation site relevant for auxiliary-space analysis."""

    kind: str          # list | dict | set | slice | string | tuple
    size: str          # constant | linear | unknown
    note: str = ""


@dataclass
class FunctionIR:
    """Structural fingerprint of a single function definition."""

    name: str
    args: list[ArgInfo] = field(default_factory=list)
    returns: list[str] = field(default_factory=list)     # list | number | boolean | string | dict | None | unknown
    loops: list[LoopInfo] = field(default_factory=list)
    max_loop_depth: int = 0
    is_recursive: bool = False
    recursive_call_count: int = 0
    recursion_shrink: str | None = None                  # linear | half | quarter | unknown
    recursion_branching: int = 1                         # number of self-calls per invocation
    memoized: bool = False
    conditionals: int = 0
    early_exit: bool = False
    allocations: list[AllocationInfo] = field(default_factory=list)
    builtin_calls: list[str] = field(default_factory=list)
    method_calls: list[str] = field(default_factory=list)
    data_structures: list[str] = field(default_factory=list)
    operations: dict[str, int] = field(default_factory=dict)
    hints: set[str] = field(default_factory=set)         # semantic keyword hints (sort, search, ...)
    has_size_parameter: bool = False                     # at least one arg looks like the "n"
    notes: list[str] = field(default_factory=list)
    # Optional per-case complexity estimate asserted by a heuristic backend
    # (natural-language mode). Keys: best/average/worst → class keys.
    estimated_time: dict[str, str] | None = None

    # Transient handle on the original AST node (never serialised).
    ast_node: Any = field(default=None, repr=False, compare=False)


@dataclass
class AlgorithmIR:
    """Full parsed representation of one algorithm submission."""

    name: str
    mode: InputMode
    source: str
    functions: list[FunctionIR] = field(default_factory=list)
    primary: FunctionIR | None = None
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    parse_ok: bool = True
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0  # < 1.0 for heuristic backends (pseudocode / natural language)

    # Local function lookup table (name -> FunctionIR) for call-graph cost inlining.
    local_functions: dict[str, FunctionIR] = field(default_factory=dict, repr=False)
