# The Analysis Engine — How It Works

This document explains the theory behind each pipeline stage, in the order
data flows through the system. It is written to be presented academically.

## 1. Parsing to the Intermediate Representation

### Python (`services/parser/python_parser.py`)

The source is compiled with Python's own `ast` module. For every function
definition the analyser extracts:

| Feature | Detection |
|---|---|
| **Loops** | `for`/`while` nodes with nesting depth and a *bound classification*: `n` (`range(len(x))`, iterating a collection), `constant` (`range(10)`), `log` (index doubles/halves — geometric progressions, binary-search style `mid` updates), `unknown` (data-dependent `while`, treated as linear worst-case) |
| **Recursion** | call sites whose callee equals the enclosing function; per-call *shrink classification* (`n-1` → linear, `n//2`, `mid±1`, `arr[:mid]` → half via a "halving variable" dataflow), plus a branching factor |
| **Memoisation** | `functools.cache/lru_cache` decorators, `cache = {}` tables, `if k in cache:` guards |
| **Early exits** | value-returning `return` inside a loop (drives best-case analysis) |
| **Allocations** | comprehensions, list/dict/set literals, **slicing** (`arr[:mid]` copies → Θ(n)), memo tables |
| **Types** | best-effort argument/return kind inference (annotations, name heuristics, local call-graph return-type propagation) |
| **Hints** | identifiers/docstrings matched against per-domain keyword sets (sorting, searching, DP, graph, …) |

The **primary (entry) function** is chosen by scoring candidates (recursion,
size-parameter, entry-like names, penalised helpers), and module-level
scripts are wrapped as a pseudo-function.

### Pseudocode (`heuristic_parsers.py`)

A line-based structural scanner: indentation stack → loop nesting;
`FOR i FROM a TO b` bounds (constant vs `n`); `FUNCTION` headers give the
recursion callee; explicitly stated complexities are honoured. Marked
`confidence = 0.7` and surfaced to the user as approximate.

### Natural language (`heuristic_parsers.py`)

A keyword model maps the description onto the same IR (purpose, recursion,
loops, memory) and extracts **explicitly stated complexity** from sentences
("degrades to n squared" → worst case O(n²)). Marked `confidence = 0.45`;
benchmarks are unavailable.

## 2. Complexity Analysis (`services/complexity/`)

### 2.1 Cost algebra

Every code fragment is reduced to a term

```
Cost = Θ(n^deg · log n)          deg ∈ ℝ≥0, log ∈ {0, 1}
```

with the composition rules:

* **sequence** `S1; S2` → `max(C1, C2)` (dominant term),
* **nesting** (loop around body) → `C_bound ⊗ C_body` (degrees add, logs or),
* **builtins** carry a table cost: `sorted → n log n`, `sum/min/max → n`,
  `len/append → 1`, `x in list → n`, `x in cache-like dict → 1`, slicing → `n`.

Local helpers are **inlined through the module call graph**, so
`merge_sort` correctly absorbs the linear merge cost of its `merge` helper.

### 2.2 Recurrence solving

If the primary function is recursive, its structure yields a recurrence
solved with the **Master Theorem**:

```
T(n) = a·T(n/b) + Θ(f(n)),   c = log_b a

Case 1  f(n) = O(n^(c-ε))        → T(n) = Θ(n^c)
Case 2  f(n) = Θ(n^c)            → T(n) = Θ(n^c · log n)
Case 3  f(n) = Ω(n^(c+ε))        → T(n) = Θ(f(n))
```

Examples produced by the engine:

* **Merge sort** — `a = 2, b = 2, f = Θ(n)` (merge loop + slice copies) ⇒
  `c = 1` ⇒ Case 2 ⇒ **Θ(n log n)**.
* **Recursive binary search** — `a = 1, b = 2, f = Θ(1)` ⇒ Case 2 with
  `c = 0` ⇒ **Θ(log n)**.
* **Naive Fibonacci** — branching `a = 2` with *linear* shrink and
  overlapping subproblems (`n-1`, `n-2` share states) ⇒ the call tree is
  exponential ⇒ **Θ(φⁿ) ≈ Θ(1.618ⁿ)**.
* **Memoised Fibonacci** — each of the n states computed once ⇒
  **Θ(n)** time, Θ(n) table space.

Linear recursion (`a = 1, b = 1`) is solved by unrolling:
`T(n) = T(n-1) + f(n) = Θ(n·f(n))`.

### 2.3 Pattern recognizers

A small library of recognizers refines the generic result for textbook
families and supplies their standard explanations:

* **Quick sort** (in-place or list-building): average Θ(n log n) via
  balanced splits, worst Θ(n²) via pivot degeneration, auxiliary Θ(log n)
  (recursion stack) or Θ(n) for the functional variant.
* **Adaptive sorts** (bubble with swap flag, insertion with shifting key):
  best Θ(n) on sorted input, worst Θ(n²); *selection sort* is correctly
  reported as non-adaptive.
* **Graph traversal** (BFS/DFS): Θ(V + E) with a visited set and queue.
* **Delegation**: `sorted()`/`.sort()` → Θ(n log n) (Timsort).

### 2.4 Best / average / worst cases

* Data-dependent early exit in a single loop → best O(1) (linear search).
* Adaptive nested loops → best Θ(n) (bubble/insertion).
* Pivot-based partition recursion → worst Θ(n²), average Θ(n log n).
* Input-order-independent algorithms (merge sort, binary search) → all
  cases equal, with an explicit note.

### 2.5 Space analysis

Auxiliary space = `max(allocations, recursion stack)`:

* slice/ comprehension buffers → Θ(n) (merge sort),
* memo tables → Θ(states),
* recursion depth → Θ(log n) for halving, Θ(n) for linear recursion,
* in-place algorithms → Θ(1) beyond the input.

## 3. Functional Equivalence (`services/functional/`)

Each algorithm is classified into a **purpose category** (sorting,
searching, numeric computation, dynamic programming, graph traversal,
string processing, data transformation) using keyword evidence boosted by
structural evidence (`sorted()` calls, memoisation, early exits, deque
usage, …). Two algorithms are *functionally equivalent* when:

1. their purpose categories match,
2. their output kinds are compatible, and
3. (for general computation) structural similarity is high enough.

The verdict lists its full reasoning trail, and — when benchmarks ran —
**empirical output agreement** on shared random inputs can override the
keyword-based classification (e.g. naive vs memoised Fibonacci computes the
same function despite different technique labels).

## 4. Similarity Engine (`services/similarity/`)

A weighted feature-vector comparison, fully explainable:

| # | Feature | Signal | Weight |
|---|---|---|---|
| 1 | Purpose | domain category equality | 25 |
| 2 | Output signature | return-type Jaccard | 15 |
| 3 | Input signature | required-parameter match | 10 |
| 4 | Recursion structure | recursive/iterative + shrink | 10 |
| 5 | Loop topology | depth & count distance | 10 |
| 6 | Data structures | container Jaccard | 10 |
| 7 | Operations | vocabulary overlap coefficient | 10 |
| 8 | Complexity class | best/avg/worst match (0.15/0.5/0.35) | 10 |

Score bands: ≥ 85 *Very similar*, 70–84 *Moderate*, 40–69 *Weak*, < 40
*Dissimilar*. Reference results: merge vs quick sort ≈ 93, bubble vs
insertion ≈ 99, merge vs BFS ≈ 25.

## 5. Benchmark Engine (`services/benchmark/`)

1. **Calling-convention inference** from the parsed signature —
   `[list]`, `[list, target]` (search), `[list, low, high]`, `[n]`,
   `[graph, start]`; optional parameters are left to their defaults.
2. **Input generation** — seeded RNG; *sorted distinct* data when both
   algorithms are search-flavoured (binary search precondition); random
   adjacency maps for graph algorithms.
3. **Size ladder selection by detected worst case** — up to n = 5000 for
   linearithmic algorithms, n = 2000 for quadratic, tiny n ≤ 18 for
   exponential; escalation stops early once a run exceeds ~1 s.
4. **Sandboxed measurement** — isolated `python -I` subprocess, RLIMIT_AS
   512 MB, CPU + wall-clock timeouts, best-of-3 timings via
   `perf_counter`, peak memory via `tracemalloc` on a separate run.
5. **Output-agreement check** — both algorithms on identical inputs
   (n = 40, 5 seeds; n = 12 for exponential pairs) feeding the functional
   verdict.

## 6. AI Explanation Layer (`services/ai/`)

A strategy-pattern interface (`Explainer.explain(ReportInputs) -> str`):

* **HeuristicExplainer** (default) — deterministic template-based prose
  generated from the structured result: reproducible, offline, gradable.
* **OpenAIExplainer** — optional LLM-backed generation (compact JSON of the
  analysis is sent); any failure falls back to the heuristic engine.

Adding a provider = implementing the protocol + registering it in the
factory. Nothing else in the platform changes.

## 7. Report Generator (`services/reports/`)

Assembles a seven-section Markdown document: overview, functional
comparison, complexity comparison table, benchmark table, mathematical
explanations (recurrences + Master Theorem cases), AI summary and a final
conclusion with an empirical speedup ratio. Reports are persisted with
every analysis run and downloadable from the UI.
