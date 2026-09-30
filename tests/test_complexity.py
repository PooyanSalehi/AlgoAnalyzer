"""Unit tests for the complexity analyzer (the academic core)."""
from __future__ import annotations

import pytest

from app.services.complexity.analyzer import ComplexityAnalyzer
from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import InputMode

MERGE_SORT = """
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:]); result.extend(right[j:])
    return result
"""

QUICK_SORT = """
def quick_sort(arr, low=0, high=None):
    if high is None:
        high = len(arr) - 1
    if low < high:
        p = partition(arr, low, high)
        quick_sort(arr, low, p - 1)
        quick_sort(arr, p + 1, high)
    return arr

def partition(arr, low, high):
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1
"""

BINARY_SEARCH = """
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""

LINEAR_SEARCH = """
def linear_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
"""

BUBBLE_SORT = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr
"""

SELECTION_SORT = """
def selection_sort(arr):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
"""

NAIVE_FIB = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

MEMO_FIB = """
def fibonacci_memo(n, cache=None):
    if cache is None:
        cache = {}
    if n in cache:
        return cache[n]
    if n <= 1:
        return n
    cache[n] = fibonacci_memo(n - 1, cache) + fibonacci_memo(n - 2, cache)
    return cache[n]
"""

MATRIX_MULTIPLY = """
def multiply(a, b):
    n = len(a)
    result = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result[i][j] += a[i][k] * b[k][j]
    return result
"""


def analyze(code: str):
    ir = AlgorithmParser().parse(code, "T", InputMode.PYTHON)
    return ComplexityAnalyzer().analyze(ir)


class TestClassicAlgorithms:
    def test_merge_sort(self):
        report = analyze(MERGE_SORT)
        assert report.time.best.label == "O(n log n)"
        assert report.time.average.label == "O(n log n)"
        assert report.time.worst.label == "O(n log n)"
        assert report.space.auxiliary.label == "O(n)"
        assert report.recurrence is not None and "2" in report.recurrence
        assert any("Master Theorem" in e for e in report.explanations)

    def test_quick_sort(self):
        report = analyze(QUICK_SORT)
        assert report.time.best.label == "O(n log n)"
        assert report.time.average.label == "O(n log n)"
        assert report.time.worst.label == "O(n²)"
        assert report.space.auxiliary.label == "O(log n)"

    def test_binary_search(self):
        report = analyze(BINARY_SEARCH)
        assert report.time.worst.label == "O(log n)"
        assert report.space.auxiliary.label == "O(1)"

    def test_linear_search_best_case(self):
        report = analyze(LINEAR_SEARCH)
        assert report.time.best.label == "O(1)"       # match on first element
        assert report.time.average.label == "O(n)"
        assert report.time.worst.label == "O(n)"

    def test_bubble_sort_adaptive(self):
        report = analyze(BUBBLE_SORT)
        assert report.time.best.label == "O(n)"       # sorted input → early exit
        assert report.time.worst.label == "O(n²)"
        assert report.space.auxiliary.label == "O(1)"

    def test_selection_sort_not_adaptive(self):
        report = analyze(SELECTION_SORT)
        assert report.time.best.label == "O(n²)"      # always scans both loops
        assert report.time.worst.label == "O(n²)"

    def test_naive_fibonacci_exponential(self):
        report = analyze(NAIVE_FIB)
        assert report.time.worst.label == "O(2ⁿ)"
        assert report.time.best.label == "O(2ⁿ)"

    def test_memoized_fibonacci_linear(self):
        report = analyze(MEMO_FIB)
        assert report.time.worst.label == "O(n)"
        assert report.space.auxiliary.label == "O(n)"

    def test_matrix_multiplication_cubic(self):
        report = analyze(MATRIX_MULTIPLY)
        assert report.time.worst.label == "O(n³)"


class TestCostAlgebra:
    def test_sequential_loops_are_max_not_sum(self):
        report = analyze("""
def two_pass(arr):
    for x in arr:
        y = x + 1
    for z in arr:
        y = z + 2
    return y
""")
        assert report.time.worst.label == "O(n)"  # n + n = O(n)

    def test_builtin_sorted_contributes_n_log_n(self):
        report = analyze("def sort_it(arr):\n    return sorted(arr)\n")
        assert report.time.worst.label == "O(n log n)"

    def test_membership_scan_on_list(self):
        report = analyze("""
def contains(arr, x):
    return x in arr
""")
        assert report.time.worst.label == "O(n)"

    def test_slicing_costs_linear(self):
        report = analyze("""
def halve(arr):
    mid = len(arr) // 2
    return arr[:mid] + arr[mid:]
""")
        assert report.time.worst.label == "O(n)"


class TestExplanations:
    def test_mathematical_wording_present(self):
        report = analyze(MERGE_SORT)
        text = " ".join(report.explanations)
        assert "T(n)" in text or "Master" in text
        assert any("Θ" in e for e in report.explanations)
