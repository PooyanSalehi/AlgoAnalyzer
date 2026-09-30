"""Curated example algorithms served by ``GET /api/examples``.

The examples double as teaching material: each pair highlights a different
analysis scenario (equal complexity, differing worst cases, naive vs
memoised recursion, adaptive sorts, non-Python input modes).
"""
from __future__ import annotations

MERGE_SORT = '''\
def merge_sort(arr):
    """Classic top-down merge sort: divide, conquer, merge."""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left_half = merge_sort(arr[:mid])
    right_half = merge_sort(arr[mid:])

    return merge(left_half, right_half)


def merge(left, right):
    """Merge two sorted lists into one sorted list."""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
'''

QUICK_SORT = '''\
def quick_sort(arr, low=0, high=None):
    """In-place quick sort with Lomuto partitioning."""
    if high is None:
        high = len(arr) - 1

    if low < high:
        pivot_index = partition(arr, low, high)
        quick_sort(arr, low, pivot_index - 1)
        quick_sort(arr, pivot_index + 1, high)
    return arr


def partition(arr, low, high):
    """Partition around the last element; returns the pivot's final index."""
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1
'''

BUBBLE_SORT = '''\
def bubble_sort(arr):
    """Bubble sort with an early-exit flag for sorted input."""
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
'''

INSERTION_SORT = '''\
def insertion_sort(arr):
    """Insertion sort: grow a sorted prefix, shifting elements right."""
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
'''

SELECTION_SORT = '''\
def selection_sort(arr):
    """Selection sort: repeatedly select the minimum into a sorted prefix."""
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
'''

BINARY_SEARCH = '''\
def binary_search(arr, target):
    """Iterative binary search on a sorted array; returns index or -1."""
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
'''

LINEAR_SEARCH = '''\
def linear_search(arr, target):
    """Scan the array left to right; returns first index of target or -1."""
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
'''

FIB_RECURSIVE = '''\
def fibonacci(n):
    """Naive recursive Fibonacci — recomputes overlapping subproblems."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
'''

FIB_MEMOIZED = '''\
def fibonacci_memo(n, cache=None):
    """Top-down dynamic programming with memoisation."""
    if cache is None:
        cache = {}
    if n in cache:
        return cache[n]
    if n <= 1:
        return n
    cache[n] = fibonacci_memo(n - 1, cache) + fibonacci_memo(n - 2, cache)
    return cache[n]
'''

GRAPH_BFS = '''\
from collections import deque


def bfs(graph, start):
    """Breadth-first traversal of a graph from a start vertex."""
    visited = set([start])
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order
'''

PSEUDO_MERGE_SORT = '''\
FUNCTION MergeSort(A)
    IF length(A) <= 1 THEN
        RETURN A
    END IF
    mid <- length(A) / 2
    left <- MergeSort(A[1..mid])
    right <- MergeSort(A[mid+1..length(A)])
    RETURN Merge(left, right)
END FUNCTION

FUNCTION Merge(L, R)
    result <- empty array
    WHILE L not empty AND R not empty DO
        IF L[1] <= R[1] THEN
            append L[1] to result, remove L[1]
        ELSE
            append R[1] to result, remove R[1]
        END IF
    END WHILE
    append remaining elements of L to result
    append remaining elements of R to result
    RETURN result
END FUNCTION
'''

PSEUDO_BUBBLE_SORT = '''\
FUNCTION BubbleSort(A)
    n <- length(A)
    FOR i FROM 0 TO n-1 DO
        FOR j FROM 0 TO n-i-2 DO
            IF A[j] > A[j+1] THEN
                swap A[j] and A[j+1]
            END IF
        END FOR
    END FOR
    RETURN A
END FUNCTION
'''

NL_MERGE = (
    "Merge sort is a divide-and-conquer algorithm. It recursively splits the array into two "
    "halves until each piece has one element, then merges the sorted halves back together by "
    "repeatedly comparing their front elements. It always runs in n log n time and needs a "
    "temporary array of size n during merging."
)

NL_QUICK = (
    "Quick sort picks a pivot element and partitions the array so that smaller elements come "
    "before it and larger ones after, then recursively sorts the two partitions in place. On "
    "average it runs in n log n time, but if the pivot is always the smallest or largest "
    "element it degrades to n squared. It uses little extra memory."
)

EXAMPLE_PAIRS = [
    {
        "id": "merge-vs-quick",
        "title": "Merge Sort vs Quick Sort",
        "description": "The classic trade-off: guaranteed Θ(n log n) with O(n) space "
                       "against in-place O(log n) space with an O(n²) worst case.",
        "a": {"name": "Merge Sort", "code": MERGE_SORT, "mode": "python"},
        "b": {"name": "Quick Sort", "code": QUICK_SORT, "mode": "python"},
    },
    {
        "id": "binary-vs-linear-search",
        "title": "Binary Search vs Linear Search",
        "description": "O(log n) on sorted data against a single O(n) scan — including "
                       "the early-exit best case of linear search.",
        "a": {"name": "Binary Search", "code": BINARY_SEARCH, "mode": "python"},
        "b": {"name": "Linear Search", "code": LINEAR_SEARCH, "mode": "python"},
    },
    {
        "id": "naive-vs-memo-fib",
        "title": "Naive vs Memoized Fibonacci",
        "description": "Overlapping subproblems make the naive version exponential (Θ(φⁿ)); "
                       "memoisation collapses it to Θ(n).",
        "a": {"name": "Fibonacci (recursive)", "code": FIB_RECURSIVE, "mode": "python"},
        "b": {"name": "Fibonacci (memoized)", "code": FIB_MEMOIZED, "mode": "python"},
    },
    {
        "id": "bubble-vs-insertion",
        "title": "Bubble Sort vs Insertion Sort",
        "description": "Two adaptive Θ(n²) sorts — both drop to Θ(n) on already-sorted input.",
        "a": {"name": "Bubble Sort", "code": BUBBLE_SORT, "mode": "python"},
        "b": {"name": "Insertion Sort", "code": INSERTION_SORT, "mode": "python"},
    },
    {
        "id": "merge-vs-bfs",
        "title": "Merge Sort vs BFS (different problems)",
        "description": "A sorting algorithm against a graph traversal — an example of a "
                       "low-similarity, non-equivalent comparison.",
        "a": {"name": "Merge Sort", "code": MERGE_SORT, "mode": "python"},
        "b": {"name": "Graph BFS", "code": GRAPH_BFS, "mode": "python"},
    },
    {
        "id": "pseudocode-sorting",
        "title": "Pseudocode: Merge Sort vs Bubble Sort",
        "description": "Demonstrates the pseudocode input mode with the structural "
                       "line-based parser.",
        "a": {"name": "Merge Sort (pseudocode)", "code": PSEUDO_MERGE_SORT, "mode": "pseudocode"},
        "b": {"name": "Bubble Sort (pseudocode)", "code": PSEUDO_BUBBLE_SORT, "mode": "pseudocode"},
    },
    {
        "id": "natural-language",
        "title": "Natural language: Merge vs Quick Sort",
        "description": "Demonstrates the natural-language input mode (keyword-driven, "
                       "approximate analysis, no benchmarks).",
        "a": {"name": "Merge Sort (description)", "code": NL_MERGE, "mode": "natural"},
        "b": {"name": "Quick Sort (description)", "code": NL_QUICK, "mode": "natural"},
    },
]
