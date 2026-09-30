"""Pseudocode and natural-language parser backends.

Pseudocode is processed with a lightweight line-based structural scanner
(indentation + keyword driven) that produces the same IR as the Python
parser, so all downstream analysis stages work unchanged.

Natural-language descriptions are mapped onto the IR through a keyword
model. The resulting analysis is explicitly marked as *low confidence*
and the UI displays a corresponding disclaimer.
"""
from __future__ import annotations

import re

from app.services.parser.keywords import (
    LOOP_KEYWORDS,
    MEMORY_KEYWORDS,
    PURPOSE_KEYWORDS,
    RECURSION_KEYWORDS,
)
from app.services.parser.models import (
    AlgorithmIR,
    AllocationInfo,
    ArgInfo,
    FunctionIR,
    InputMode,
    LoopBound,
    LoopInfo,
)

_PSEUDO_FUNC = re.compile(r"^\s*(?:function|procedure|algorithm)\s+([A-Za-z_]\w*)", re.IGNORECASE)
_PSEUDO_FOR = re.compile(r"^\s*for\s+(.+)", re.IGNORECASE)
_PSEUDO_WHILE = re.compile(r"^\s*while\s+(.+)", re.IGNORECASE)
_PSEUDO_IF = re.compile(r"^\s*if\s+(.+)", re.IGNORECASE)
_PSEUDO_RETURN = re.compile(r"^\s*(?:return|output)\s+(.*)", re.IGNORECASE)
_PSEUDO_END = re.compile(r"^\s*end\b.*", re.IGNORECASE)

_HALVING = re.compile(r"(i\s*=\s*i\s*[*/]\s*2|halve|divide.*(in half|by 2)|half)", re.IGNORECASE)
_CONSTANT_BOUND = re.compile(r"\bto\s+(\d+)\b", re.IGNORECASE)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _looks_constant(for_line: str) -> bool:
    return bool(_CONSTANT_BOUND.search(for_line))


def _shrink_from_text(text: str) -> str | None:
    if re.search(r"(n\s*-\s*1|decrement|reduce by one|n-1)", text, re.IGNORECASE):
        return "linear"
    if re.search(r"(n\s*/\s*2|n\s*//\s*2|half|halve|divide.*2|mid)", text, re.IGNORECASE):
        return "half"
    return None


_COMPLEXITY_MENTION: list[tuple[str, str]] = [
    (r"n\s*log\s*n|nlogn|linearithmic", "n_log_n"),
    (r"n\s*[²\^2]|n\s+squared|quadratic", "quadratic"),
    (r"n\s*[³\^3]|cubic", "cubic"),
    (r"2\s*[\^nⁿ]|exponential", "exponential"),
    (r"log\s*n|logarithmic", "log_n"),
    (r"\bconstant\s+time|o\s*\(\s*1\s*\)", "constant"),
]


def _stated_complexity(text: str) -> dict[str, str] | None:
    """Extract an explicitly stated complexity from free text, if any.

    Sentences mentioning "worst"/"degrades" bind to the worst case; sentences
    mentioning "average"/"typically" bind to the average case; an unqualified
    statement applies to all three cases.
    """
    sentences = re.split(r"[.!?;\n]|\b(?:but|however|although|whereas)\b", text.lower())
    result: dict[str, str] = {}
    for sentence in sentences:
        if not sentence.strip():
            continue
        for pattern, key in _COMPLEXITY_MENTION:
            if re.search(pattern, sentence):
                if re.search(r"worst|degrad|adversarial", sentence):
                    result["worst"] = key
                elif re.search(r"average|typical|expected", sentence):
                    result["average"] = key
                elif re.search(r"best", sentence):
                    result["best"] = key
                else:
                    result.setdefault("best", key)
                    result.setdefault("average", key)
                    result.setdefault("worst", key)
                break
    if not result:
        return None
    fill = result.get("average") or result.get("worst") or result.get("best")
    for case in ("best", "average", "worst"):
        result.setdefault(case, fill)
    return result


class PseudocodeParser:
    """Line-based structural parser for pseudocode notation."""

    def parse(self, source: str, name: str = "Algorithm") -> AlgorithmIR:
        lines = source.splitlines()
        loops: list[LoopInfo] = []
        returns: list[str] = []
        allocations: list[AllocationInfo] = []
        conditionals = 0
        early_exit = False
        hints: set[str] = set()
        depth_stack: list[int] = []

        fn_name = "algorithm"
        for line in lines:
            m = _PSEUDO_FUNC.match(line)
            if m:
                fn_name = m.group(1)
                break

        lowered_all = source.lower()
        for keyword_set in PURPOSE_KEYWORDS.values():
            hints.update(k for k in keyword_set if k in lowered_all)

        for lineno, raw in enumerate(lines, start=1):
            line = raw.split("#")[0].split("//")[0]
            if not line.strip():
                continue
            if _PSEUDO_END.match(line):
                if depth_stack:
                    depth_stack.pop()
                continue
            if re.search(r"\b(empty array|new array|auxiliary array|allocate|create array)\b",
                         line, re.IGNORECASE):
                allocations.append(AllocationInfo(kind="list", size="linear",
                                                  note="auxiliary array allocated"))
            if _PSEUDO_FOR.match(line) or _PSEUDO_WHILE.match(line):
                text = line.strip()
                is_for = bool(_PSEUDO_FOR.match(line))
                if _HALVING.search(text):
                    bound, note = LoopBound.LOG, "index doubles/halves each iteration"
                elif is_for and _looks_constant(text):
                    bound, note = LoopBound.CONSTANT, "constant loop bound"
                else:
                    bound, note = LoopBound.N, "iterates over the input size n"
                depth = len(depth_stack) + 1
                loops.append(LoopInfo(kind="for" if is_for else "while", depth=depth,
                                      bound=bound, line=lineno, note=note))
                depth_stack.append(_indent_of(raw))
                if re.search(r"\b(new array|create array|allocate|auxiliary array)\b", text, re.IGNORECASE):
                    allocations.append(AllocationInfo(kind="list", size="linear",
                                                      note="auxiliary array allocated in loop"))
            elif _PSEUDO_IF.match(line):
                conditionals += 1
                depth_stack.append(_indent_of(raw))
            elif _PSEUDO_RETURN.match(line):
                ret = _PSEUDO_RETURN.match(line).group(1).strip().lower()
                if any(k in ret for k in ("true", "false")):
                    returns.append("boolean")
                elif re.search(r"\b(array|list|sorted array|result list)\b", ret):
                    returns.append("list")
                elif re.match(r"^-?\d+$", ret):
                    returns.append("number")
                else:
                    returns.append("unknown")
                if depth_stack:
                    early_exit = True

        # Recursion: the algorithm's own name being invoked inside its body.
        body = "\n".join(lines)
        call_re = re.compile(rf"\b{re.escape(fn_name)}\s*\(", re.IGNORECASE)
        call_sites = [l for l in body.splitlines() if call_re.search(l) and not _PSEUDO_FUNC.match(l)]
        is_recursive = len(call_sites) >= 1
        # Count simultaneous sibling calls (same indentation) as branching.
        branching = min(len(call_sites), 8) if is_recursive else 0
        shrink = _shrink_from_text(body) if is_recursive else None

        args = self._guess_args(source)

        estimated = _stated_complexity(body)

        fn = FunctionIR(
            name=fn_name,
            args=args,
            returns=sorted(set(returns)) or ["unknown"],
            loops=loops,
            max_loop_depth=max((l.depth for l in loops), default=0),
            is_recursive=is_recursive,
            recursive_call_count=len(call_sites),
            recursion_shrink=shrink,
            recursion_branching=max(branching, 1),
            memoized=bool(re.search(r"\b(cache|memo)", body, re.IGNORECASE)),
            conditionals=conditionals,
            early_exit=early_exit,
            allocations=allocations,
            builtin_calls=[],
            method_calls=[],
            data_structures=sorted({k for k in MEMORY_KEYWORDS if k in lowered_all}) or ["list"],
            operations={},
            hints=hints,
            has_size_parameter=bool(args),
            notes=["Analysed by the pseudocode structural scanner (approximate)."],
            estimated_time=estimated,
        )
        return AlgorithmIR(
            name=name,
            mode=InputMode.PSEUDOCODE,
            source=source,
            functions=[fn],
            primary=fn,
            line_count=len([l for l in lines if l.strip()]),
            parse_ok=True,
            warnings=["Pseudocode analysis is structural and approximate; benchmarks are unavailable."],
            confidence=0.7,
        )

    def _guess_args(self, source: str) -> list[ArgInfo]:
        m = _PSEUDO_FUNC.search(source)
        if not m:
            return [ArgInfo(name="input", kind="iterable")]
        header = m.group(0)
        params = re.search(r"\(([^)]*)\)", header)
        if not params:
            return [ArgInfo(name="input", kind="iterable")]
        out: list[ArgInfo] = []
        for p in params.group(1).split(","):
            p = p.strip().split(":")[0].strip()
            if not p:
                continue
            kind = "iterable" if p.lower().endswith(("s", "arr", "list", "array")) else "int"
            out.append(ArgInfo(name=p, kind=kind))
        return out or [ArgInfo(name="input", kind="iterable")]


class NaturalLanguageParser:
    """Keyword-model parser for natural language algorithm descriptions."""

    def parse(self, source: str, name: str = "Algorithm") -> AlgorithmIR:
        text = source.lower()
        hints: set[str] = set()
        for keyword_set in PURPOSE_KEYWORDS.values():
            hints.update(k for k in keyword_set if k in text)

        # Purpose category with the strongest keyword evidence.
        best_purpose, best_hits = "general computation", 0
        for purpose, keywords in PURPOSE_KEYWORDS.items():
            hits = sum(1 for k in keywords if k in text)
            if hits > best_hits:
                best_purpose, best_hits = purpose, hits

        is_recursive = any(k in text for k in RECURSION_KEYWORDS) or "recursi" in text
        mentions_loops = any(k in text for k in LOOP_KEYWORDS)
        mentions_divide = "divide" in text and "conquer" in text or "split" in text or "halv" in text
        mentions_merge = "merge" in text
        mentions_memory = [k for k in MEMORY_KEYWORDS if k in text]
        # "in place" / "little extra memory" wording → constant auxiliary space.
        in_place = any(phrase in text for phrase in (
            "in place", "in-place", "little extra memory", "constant extra",
            "constant memory", "without extra"))
        if in_place:
            mentions_memory = []

        loops: list[LoopInfo] = []
        if mentions_loops:
            loops.append(LoopInfo(kind="for", depth=1, bound=LoopBound.N, line=0,
                                  note="loop mentioned in description"))
        if "nested" in text or "for each" in text and "for each" in text.split("for each")[1]:
            loops.append(LoopInfo(kind="for", depth=2, bound=LoopBound.N, line=0,
                                  note="nested loops mentioned"))

        shrink = None
        if is_recursive:
            shrink = _shrink_from_text(text)

        fn = FunctionIR(
            name=(name or "algorithm").lower().replace(" ", "_"),
            args=[ArgInfo(name="input", kind="iterable" if best_purpose in {
                "sorting", "searching", "data transformation", "graph traversal"} else "int")],
            returns=["list"] if best_purpose in {"sorting", "data transformation"} else ["unknown"],
            loops=loops,
            max_loop_depth=max((l.depth for l in loops), default=0),
            is_recursive=is_recursive,
            recursive_call_count=2 if is_recursive and mentions_divide else (1 if is_recursive else 0),
            recursion_shrink=shrink,
            recursion_branching=2 if is_recursive and mentions_divide else 1,
            memoized=any(k in text for k in ("memo", "cache", "store the results")),
            conditionals=1 if "if" in text else 0,
            early_exit=False,
            allocations=[AllocationInfo(kind="list", size="linear", note="array usage described")]
            if mentions_memory else [],
            builtin_calls=[],
            method_calls=[],
            data_structures=sorted(set(mentions_memory)) or ["list"],
            operations={},
            hints=hints,
            has_size_parameter=True,
            estimated_time=_stated_complexity(text),
            notes=[
                "Natural-language input: analysis is derived from a keyword model and is indicative only.",
                f"Detected purpose category: {best_purpose}.",
            ],
        )
        return AlgorithmIR(
            name=name,
            mode=InputMode.NATURAL,
            source=source,
            functions=[fn],
            primary=fn,
            line_count=len([l for l in source.splitlines() if l.strip()]),
            parse_ok=True,
            warnings=[
                "Natural-language mode produces an approximate, keyword-driven analysis with low confidence.",
                "Empirical benchmarks are unavailable for natural-language input.",
            ],
            confidence=0.45,
        )
