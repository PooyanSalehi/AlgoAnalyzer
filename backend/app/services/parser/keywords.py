"""Shared keyword tables used for semantic classification.

The same hint sets are consumed by the parser (feature extraction), the
functional analyzer (purpose classification) and the similarity engine,
guaranteeing a single source of truth for "what does this algorithm do".
"""
from __future__ import annotations

PURPOSE_KEYWORDS: dict[str, set[str]] = {
    "sorting": {
        "sort", "sorted", "merge", "partition", "pivot", "quicksort", "quick_sort",
        "mergesort", "merge_sort", "bubble", "insertion", "selection", "heapsort",
        "heap_sort", "radix", "bucket", "ascending", "descending", "order", "swap",
        "timsort", "arrange", "reorder",
    },
    "searching": {
        "search", "find", "lookup", "index", "locate", "binary_search", "linear_search",
        "binarysearch", "linearsearch", "target", "contains", "member", "present",
        "key_found", "found",
    },
    "numeric computation": {
        "fib", "fibonacci", "factorial", "prime", "primes", "gcd", "lcm", "power",
        "pow", "sqrt", "square", "exp", "log", "sum", "product", "multiply", "add",
        "divide", "mod", "modular", "exponent", "arithmetic", "compute", "calculate",
        "digit", "palindrome_number", "collatz", "triangle", "series",
    },
    "dynamic programming": {
        "memo", "memoize", "memoized", "memoization", "cache", "dp", "tabulation",
        "bottom_up", "top_down", "subproblem", "optimal_substructure", "lcs",
        "knapsack", "edit_distance", "coin_change", "matrix_chain",
    },
    "graph traversal": {
        "graph", "bfs", "dfs", "breadth", "depth_first", "dijkstra", "bellman",
        "floyd", "warshall", "kruskal", "prim", "topological", "topo", "adjacency",
        "neighbors", "neighbours", "visited", "vertex", "vertices", "edge", "edges",
        "queue", "deque", "shortest_path", "path",
    },
    "string processing": {
        "string", "str", "char", "character", "substring", "prefix", "suffix",
        "palindrome", "anagram", "reverse", "concat", "split", "join", "regex",
        "match", "pattern", "text",
    },
    "data transformation": {
        "map", "filter", "reduce", "transform", "convert", "parse", "serialize",
        "encode", "decode", "compress", "hash", "aggregate", "group", "unique",
        "distinct", "count", "frequency", "statistics", "normalize",
    },
}

ALL_PURPOSE_KEYWORDS: set[str] = set().union(*PURPOSE_KEYWORDS.values())

RECURSION_KEYWORDS = {"recursive", "recursion", "calls itself", "self-call", "divide and conquer",
                      "divide-and-conquer", "recursively"}
LOOP_KEYWORDS = {"loop", "iterate", "iteration", "for each", "repeat", "while", "traverse",
                 "scan", "cycle"}
MEMORY_KEYWORDS = {"array", "list", "dictionary", "dict", "set", "stack", "queue", "buffer",
                   "allocate", "memory", "copy", "slice", "matrix", "table"}
