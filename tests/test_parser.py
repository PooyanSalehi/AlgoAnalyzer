"""Unit tests for the Python AST parser."""
from __future__ import annotations

from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import InputMode


def parse(code: str):
    return AlgorithmParser().parse(code, "Test", InputMode.PYTHON)


def test_loops_nesting_and_bounds():
    ir = parse("""
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""")
    fn = ir.primary
    assert fn.name == "bubble_sort"
    assert fn.max_loop_depth == 2
    assert len(fn.loops) == 2
    assert all(l.bound.value == "n" for l in fn.loops)


def test_constant_loop_bound():
    ir = parse("def f(arr):\n    for i in range(10):\n        print(arr[i])\n")
    assert ir.primary.loops[0].bound.value == "constant"


def test_halving_while_loop():
    ir = parse("""
def double_until(n):
    i = 1
    while i < n:
        i = i * 2
    return i
""")
    assert ir.primary.loops[0].bound.value == "log"


def test_recursion_detection_merge_sort():
    ir = parse("""
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge_sort(arr[:mid]) + merge_sort(arr[mid:])
""")
    fn = ir.primary
    assert fn.is_recursive
    assert fn.recursive_call_count == 2
    assert fn.recursion_shrink == "half"
    assert fn.recursion_branching == 2


def test_recursion_detection_linear():
    ir = parse("def fact(n):\n    if n <= 1:\n        return 1\n    return n * fact(n - 1)\n")
    fn = ir.primary
    assert fn.is_recursive
    assert fn.recursion_shrink == "linear"
    assert fn.recursion_branching == 1


def test_memoization_detection():
    ir = parse("""
def fib(n, cache=None):
    if cache is None:
        cache = {}
    if n in cache:
        return cache[n]
    if n <= 1:
        return n
    cache[n] = fib(n - 1, cache) + fib(n - 2, cache)
    return cache[n]
""")
    assert ir.primary.memoized is True


def test_return_type_inference_and_propagation():
    ir = parse("""
def sort_all(arr):
    return helper(arr)

def helper(x):
    return sorted(x)
""")
    primary = ir.primary
    assert primary.name == "sort_all"
    assert "list" in primary.returns  # propagated from helper


def test_early_exit_detection():
    ir = parse("""
def find(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
""")
    assert ir.primary.early_exit is True


def test_data_structures_and_hints():
    ir = parse("""
def process(items):
    seen = set()
    table = {}
    for x in items:
        seen.add(x)
        table[x] = x * 2
    return table
""")
    fn = ir.primary
    assert "set" in fn.data_structures
    assert "dict" in fn.data_structures
    assert "list" in fn.data_structures  # from the iterable parameter


def test_syntax_error_raises_parse_error():
    import pytest
    from app.core.errors import ParseError

    with pytest.raises(ParseError):
        parse("def broken(:")


def test_module_without_functions():
    ir = parse("x = [3, 1, 2]\nx.sort()\n")
    assert ir.primary is not None
    assert ir.primary.name == "<module>"


def test_args_with_defaults_marked():
    ir = parse("def quick_sort(arr, low=0, high=None):\n    return arr\n")
    kinds = {a.name: a.has_default for a in ir.primary.args}
    assert kinds == {"arr": False, "low": True, "high": True}
