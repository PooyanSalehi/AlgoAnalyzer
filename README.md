# ◈ AlgoAnalyzer

**An intelligent platform that analyses and compares two algorithms from multiple perspectives — functional equivalence, asymptotic complexity, empirical performance and conceptual similarity.**

Built as a university-level software engineering project: a production-style
full-stack application (FastAPI · React · TypeScript · PostgreSQL) with a
documented, academically explainable analysis engine.

```
Merge Sort  vs  Quick Sort
─────────────────────────────────────────────────────────────
Functional similarity:  93% — Very similar (both sort a list)
Time   best / avg / worst      Space (auxiliary)
A      O(n log n) / O(n log n) / O(n log n)      O(n)
B      O(n log n) / O(n log n) / O(n²)           O(log n)
Math:  A: T(n)=2·T(n/2)+Θ(n)  → Master Theorem Case 2 → Θ(n log n)
       B: balanced splits average n log n; degenerate pivots → Θ(n²)
```

---

## Table of contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Usage guide](#usage-guide)
6. [API documentation](#api-documentation)
7. [Testing](#testing)
8. [Project structure](#project-structure)
9. [Future improvements](#future-improvements)
10. [License](#license)

---

## Introduction

Comparing two algorithms is a core skill of computer science, yet it is
usually done by hand: inspect code, guess the recurrence, maybe time both
implementations with ad-hoc scripts. **AlgoAnalyzer automates the whole
process** behind a modern developer dashboard:

* **Functional equivalence** — do both algorithms solve the *same
  computational problem*? Purpose classification, input/output behaviour,
  operation patterns, an explainable similarity score, and an *empirical*
  cross-check that runs both algorithms on identical inputs.
* **Complexity analysis** — best / average / worst time complexity and
  auxiliary space, derived from the AST through a symbolic cost algebra,
  recurrence solving (Master Theorem) and pattern recognition — always with
  the mathematical reasoning shown.
* **Empirical benchmarking** — sandboxed execution with generated test
  inputs measuring wall-clock time and peak memory across input sizes.
* **Reporting** — a professional seven-section Markdown report, generated
  per analysis and stored in the database.

Three input modes are supported: **Python source**, **pseudocode** and
**natural-language descriptions** (approximate, clearly flagged as such).

## Features

### Analysis engine
- Python AST parser → loops (with bounds), recursion (branching + shrink), conditionals, allocations, data structures, operations, semantic hints
- Cost algebra `Θ(n^deg · log n)` with sequence/nesting composition and builtin cost modelling
- Recurrence solving: Master Theorem (Cases 1–3), linear-recursion unrolling, memoised recursion, overlapping-subproblem (exponential) detection
- Pattern recognizers: quick sort, adaptive sorts (bubble/insertion), graph traversal (V+E), delegated Timsort
- Best/average/worst-case derivation from data dependence (early exits, swap flags, pivot degeneration)
- Purpose classification + functional-equivalence verdict with reasoning trail
- Weighted, glass-box similarity scoring (8 features, 100 points, individually explained)
- Sandboxed benchmark engine: subprocess isolation, resource limits, timeouts, seeded inputs, best-of-3 timing, `tracemalloc` memory, output-agreement verification
- Modular AI explanation layer (deterministic heuristic engine by default; optional LLM provider with graceful fallback)
- Markdown report generator (7 sections) stored in the database

### Platform
- React + TypeScript + Tailwind dashboard, GitHub/VS Code-inspired dark theme
- Two Monaco editors (VS Code editor) with per-algorithm language selection
- Interactive charts (Recharts): theoretical growth curves on log scale with reference classes, execution time, memory usage
- Similarity gauge + per-feature breakdown bars, complexity comparison tables, reasoning panels
- Analysis history backed by the database, reloadable with one click
- Report download (`.md`)
- REST API with OpenAPI/Swagger docs
- PostgreSQL in production, zero-config SQLite for development
- Docker Compose for the full stack, GitHub Actions CI

## Architecture

```
┌──────────────────────────── PRESENTATION ─────────────────────────────┐
│  React 18 + TypeScript + Tailwind · Monaco editors · Recharts        │
└─────────────────────────────────┬─────────────────────────────────────┘
                          REST /api (JSON)
┌─────────────────────────────────▼─────────────────────────────────────┐
│                        FastAPI APPLICATION                            │
│  routes ─► AnalysisService (pure orchestrator)                        │
│              │                                                        │
│   ┌──────────┴─────────┬───────────────┬─────────────┬────────────┐   │
│   │ Parser (AST→IR)    │ Complexity    │ Functional  │ Similarity │   │
│   │ python/pseudo/NL   │ Analyzer      │ Analyzer    │ Engine     │   │
│   └────────────────────┴───────────────┴─────────────┴────────────┘   │
│              │            Benchmark Engine (sandbox) │                │
│              └────────► Report Generator ◄── AI Explanation Layer     │
└──────────────────────────────┬────────────────────────────────────────┘
                    SQLAlchemy 2.0 (session per request)
┌──────────────────────────────▼────────────────────────────────────────┐
│  PostgreSQL — users · projects · algorithms · analysis_runs · reports │
└────────────────────────────────────────────────────────────────────────┘
```

Detailed documentation:

- [`docs/architecture.md`](docs/architecture.md) — full system design, data model, security notes
- [`docs/analysis-engine.md`](docs/analysis-engine.md) — how every analysis stage works (the academic explanation)
- [`docs/api.md`](docs/api.md) — complete REST API reference

## Installation

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ (20 recommended) |
| PostgreSQL | 16 (optional — SQLite works out of the box) |
| Docker | any recent version (for the containerised setup) |

### Option A — local development (zero-config, SQLite)

```bash
git clone <repository-url>
cd AlgoAnalyzer

# 1. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # or: pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api → :8000)
```

The Vite dev server proxies `/api` to the backend, so no CORS setup is
needed. The backend creates the SQLite database and tables automatically on
first start.

### Option B — Docker Compose (PostgreSQL + backend + frontend)

```bash
docker compose up --build
# frontend  → http://localhost:3000
# backend   → http://localhost:8000/docs
# postgres  → localhost:5432 (algo/algo)
```

### Environment configuration

Copy [`.env.example`](.env.example) to `.env` (backend) and/or
`frontend/.env`. Key variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./algodata.db` | SQLAlchemy URL (`postgresql+psycopg://…` in production) |
| `CORS_ORIGINS` | `["*"]` | allowed origins (no cookies are used) |
| `AI_PROVIDER` | `heuristic` | `heuristic` (offline) or `openai` |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-4o-mini` | LLM explanation provider |
| `BENCHMARK_ENABLED` | `true` | toggle empirical benchmarks |
| `BENCHMARK_TIMEOUT_SECONDS` | `30` | sandbox wall-clock limit |
| `BENCHMARK_MAX_MEMORY_MB` | `512` | sandbox address-space limit |
| `VITE_API_BASE` | *(relative)* | absolute backend origin, if needed |

## Usage guide

1. **Open the dashboard** (`http://localhost:5173` dev, `:3000` Docker).
2. **Enter algorithms** in the two Monaco editors (A = reference, B =
   challenger). For each editor choose the input mode: *Python*,
   *Pseudocode* or *Natural language*.
3. **Or load an example** — the toolbar selector ships curated pairs
   (Merge vs Quick Sort, Binary vs Linear Search, naive vs memoised
   Fibonacci, adaptive sorts, a graph algorithm, and pseudocode /
   natural-language demos).
4. **Click “Analyze & Compare”**. The pipeline runs: parsing → complexity
   → similarity → functional → benchmarks → explanation → report.
5. **Read the dashboard**:
   - *Similarity gauge* — conceptual similarity score and band, with the
     per-feature breakdown showing exactly where points came from.
   - *Functional equivalence* — verdict, purposes, I/O analysis, full
     reasoning, and the empirical output-agreement check.
   - *Complexity comparison* — best/average/worst time and auxiliary/total
     space with colour-coded badges and the detected recurrences.
   - *Growth chart* — theoretical operation counts (log scale) against
     reference classes O(1) … O(2ⁿ).
   - *Benchmarks* — measured execution time and memory vs input size, plus
     the raw values table and speedup ratios.
   - *Parsed structure* — the evidence: loops with bounds, recursion
     signatures, allocations, math reasoning per algorithm.
   - *AI explanation* — plain-language interpretation.
   - *Report* — the full Markdown report, downloadable as `.md`.
6. **History tab** — every analysis is stored; reopen any past run.

### Example curl call

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"algorithm_a":{"name":"Merge Sort","code":"def merge_sort(a):\n    if len(a)<=1: return a\n    m=len(a)//2\n    return merge_sort(a[:m])+merge_sort(a[m:])\n","mode":"python"},
       "algorithm_b":{"name":"Quick Sort","code":"def quick_sort(a):\n    if len(a)<=1: return a\n    p=a[0]\n    return quick_sort([x for x in a[1:] if x<p])+[p]+quick_sort([x for x in a[1:] if x>=p])\n","mode":"python"},
       "options":{"run_benchmarks":true}}'
```

## API documentation

Interactive docs are generated automatically: **`/docs`** (Swagger UI) and
**`/redoc`**. A human-readable reference with request/response schemas
lives in [`docs/api.md`](docs/api.md). Summary:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyze` | run the full analysis pipeline on two algorithms |
| `GET` | `/api/analyses` | analysis history |
| `GET` | `/api/analyses/{id}` | replay a stored analysis |
| `GET` | `/api/analyses/{id}/report` | fetch the Markdown report |
| `GET` | `/api/examples` | curated example comparisons |
| `GET/POST` | `/api/projects` | list / create projects |
| `GET/POST/DELETE` | `/api/algorithms` | algorithm CRUD |
| `GET` | `/api/health` | service health |

## Testing

```bash
# Backend — 62 unit & integration tests (parser, complexity, similarity,
# functional, benchmark sandbox, API, reports, heuristic parsers)
cd backend && .venv/bin/python -m pytest ../tests

# Frontend — vitest unit tests (complexity utilities)
cd frontend && npm run test

# Type-check + production build
cd frontend && npm run build
```

Or simply `make test`. CI runs the same suites on Python 3.11/3.12 and
Node 20 ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project structure

```
AlgoAnalyzer/
├── backend/                  FastAPI service (Python 3.11+)
│   ├── app/
│   │   ├── api/routes/       analysis · meta (health, examples, CRUD)
│   │   ├── core/             settings, domain errors
│   │   ├── db/               models · session · repositories
│   │   ├── schemas/          pydantic contracts
│   │   ├── services/         parser · complexity · functional · similarity
│   │   │                     benchmark · reports · ai
│   │   └── data/             example catalogue
│   └── Dockerfile
├── frontend/                 React 18 + TypeScript + Vite
│   ├── src/api/              typed client + contract types
│   ├── src/components/       editors, charts, panels, UI primitives
│   ├── src/hooks/            useAnalysis (application state)
│   ├── src/lib/              complexity utilities (+ tests)
│   ├── src/pages/            Analyzer · History
│   └── Dockerfile + nginx.conf
├── docs/                     architecture · api · analysis-engine
├── examples/                 curated algorithms (python/pseudo/NL)
├── tests/                    backend test suite (pytest)
├── docker-compose.yml        postgres + backend + frontend
├── Makefile                  dev task runner
└── .github/workflows/ci.yml  continuous integration
```

## Future improvements

- **Language coverage** — the parser is a pluggable backend; a Tree-sitter
  based parser would add C/C++/Java/JavaScript with the same IR.
- **Authentication & multi-tenancy** — JWT auth with per-user projects
  (the data model already supports it) and rate limiting.
- **Alembic migrations** — replace `create_all()` for production schema
  evolution.
- **Hardened sandbox** — run benchmarks inside ephemeral containers
  (gVisor/Firecracker) with CPU accounting for untrusted multi-user
  deployments.
- **Statistical benchmarking** — CIs via more repetitions, cache-flushed
  runs, and curve fitting to empirically *verify* the predicted complexity
  class.
- **Interprocedural analysis** — cross-function recursion and call-graph
  cost propagation beyond same-module helpers.
- **Amortised & probabilistic structures** — modelling of dynamic arrays,
  hash-table resizing, skip lists.
- **Export formats** — PDF/LaTeX reports, shareable permalinks.
- **Realtime collaboration** — shared sessions for classroom use.

## License

Released under the [MIT License](LICENSE).
