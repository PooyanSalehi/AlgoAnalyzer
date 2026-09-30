"""Unit tests for the similarity engine and functional analyzer."""
from __future__ import annotations

from app.services.complexity.analyzer import ComplexityAnalyzer
from app.services.functional.analyzer import FunctionalAnalyzer, classify_purpose
from app.services.parser.facade import AlgorithmParser
from app.services.parser.models import InputMode
from app.services.similarity.engine import SimilarityEngine


def full(code: str):
    ir = AlgorithmParser().parse(code, "T", InputMode.PYTHON)
    return ir, ComplexityAnalyzer().analyze(ir)


MERGE_SORT = """
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge(merge_sort(arr[:mid]), merge_sort(arr[mid:]))

def merge(l, r):
    out = []
    i = j = 0
    while i < len(l) and j < len(r):
        if l[i] <= r[j]:
            out.append(l[i]); i += 1
        else:
            out.append(r[j]); j += 1
    return out
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
        if arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
"""


class TestPurposeClassification:
    def test_sorting(self):
        assert classify_purpose(full(MERGE_SORT)[0]) == "sorting"

    def test_searching(self):
        assert classify_purpose(full(BINARY_SEARCH)[0]) == "searching"

    def test_dynamic_programming(self):
        ir, _ = full("""
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
        assert classify_purpose(ir) == "dynamic programming"


class TestSimilarityEngine:
    def test_same_problem_high_similarity(self):
        ir_a, c_a = full(MERGE_SORT)
        ir_b, c_b = full(QUICK_SORT)
        report = SimilarityEngine().compare(ir_a, ir_b, c_a, c_b)
        assert report.score >= 85
        assert report.band == "Very similar"
        # Breakdown is transparent and weights sum to 100.
        assert sum(f.weight for f in report.features) == 100
        assert all(0.0 <= f.score <= 1.0 for f in report.features)

    def test_different_problems_low_similarity(self):
        ir_a, c_a = full(MERGE_SORT)
        ir_b, c_b = full(BINARY_SEARCH)
        report = SimilarityEngine().compare(ir_a, ir_b, c_a, c_b)
        assert report.score < 70

    def test_identical_algorithms_score_high(self):
        ir_a, c_a = full(MERGE_SORT)
        ir_b, c_b = full(MERGE_SORT)
        report = SimilarityEngine().compare(ir_a, ir_b, c_a, c_b)
        assert report.score >= 95


class TestFunctionalAnalyzer:
    def test_equivalent_sorts(self):
        ir_a, c_a = full(MERGE_SORT)
        ir_b, c_b = full(QUICK_SORT)
        report = FunctionalAnalyzer().compare(ir_a, ir_b, c_a, c_b, 90)
        assert report.equivalent is True
        assert report.purpose_a == report.purpose_b == "sorting"
        assert len(report.reasoning) >= 4

    def test_different_problems_not_equivalent(self):
        ir_a, c_a = full(MERGE_SORT)
        ir_b, c_b = full(BINARY_SEARCH)
        report = FunctionalAnalyzer().compare(ir_a, ir_b, c_a, c_b, 40)
        assert report.equivalent is False
        assert "different" in report.verdict.lower() or "Not" in report.verdict
