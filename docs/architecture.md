# Architecture

## System overview

AlgoAnalyzer is a three-tier web application:

```
┌──────────────────────────────── PRESENTATION TIER ────────────────────────────────┐
│  React 18 + TypeScript + Tailwind (Vite)                                          │
│                                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────────────────┐  │
│  │ Monaco       │  │ Language     │  │ Results dashboard                       │  │
│  │ editors (A,B)│  │ selector     │  │  • similarity gauge & breakdown         │  │
│  │ Python /     │  │ python /     │  │  • complexity table + growth charts     │  │
│  │ pseudocode / │  │ pseudocode / │  │  • benchmark time & memory charts       │  │
│  │ natural lang │  │ natural      │  │  • reasoning, AI explanation, report    │  │
│  └──────────────┘  └──────────────┘  └─────────────────────────────────────────┘  │
└─────────────────────────────────────┬──────────────────────────────────────────────┘
                                      │  REST /api (JSON)
┌─────────────────────────────────────▼──────────────────────────────────────────────┐
│                              APPLICATION TIER — FastAPI                             │
│                                                                                     │
│   api/routes ──► services/analysis_service (pipeline orchestrator)                  │
│        │                       │                                                    │
│        │        ┌──────────────┼───────────────┬────────────────┬────────────┐      │
│        │        ▼              ▼               ▼                ▼            ▼      │
│        │   ┌─────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ ┌─────────┐ │
│        │   │ Parser  │  │ Complexity │  │ Functional │  │ Similarity │ │Benchmark│ │
│        │   │ (AST→IR)│  │ Analyzer   │  │ Analyzer   │  │ Engine     │ │ Engine  │ │
│        │   └─────────┘  └────────────┘  └────────────┘  └────────────┘ └─────────┘ │
│        │        │              │               │               │            │      │
│        │        └──────────────┴───────┬───────┴───────────────┴────────────┘      │
│        │                               ▼                                           │
│        │                    ┌────────────────────┐   ┌──────────────────────┐      │
│        │                    │ Report Generator   │   │ AI Explanation Layer │      │
│        │                    │ (Markdown)         │   │ (pluggable strategy) │      │
│        │                    └────────────────────┘   └──────────────────────┘      │
│        │                                                                            │
│        │   Benchmark sandbox: isolated subprocesses (`python -I`), rlimits,         │
│        │   wall-clock timeouts, deterministic seeded inputs, tracemalloc.           │
└────────┼────────────────────────────────────────────────────────────────────────────┘
         │ SQLAlchemy 2.0 (async-free, session-per-request)
┌────────▼────────────────────────────────────────────────────────────────────────────┐
│  DATA TIER — PostgreSQL (production) / SQLite (zero-config development)             │
│  users · projects · algorithms · analysis_runs · reports                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Repository layout

```
AlgoAnalyzer/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── api/routes/      REST endpoints (analysis, meta/health/examples/CRUD)
│   │   ├── core/            settings (12-factor), domain errors
│   │   ├── db/              SQLAlchemy models, session, repositories
│   │   ├── schemas/         pydantic request/response contracts
│   │   ├── services/        the analysis pipeline (see below)
│   │   │   ├── parser/      Python AST · pseudocode · natural-language → IR
│   │   │   ├── complexity/  cost algebra, Master Theorem, recognizers
│   │   │   ├── functional/  purpose classification & equivalence verdict
│   │   │   ├── similarity/  weighted feature-vector scoring
│   │   │   ├── benchmark/   sandboxed empirical measurement
│   │   │   ├── reports/     Markdown report generator
│   │   │   └── ai/          explanation layer (strategy pattern)
│   │   └── data/            curated example catalogue
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/                React + TS + Tailwind + Monaco + Recharts
│   ├── src/api/             typed API client & contract mirrors
│   ├── src/components/      UI primitives, editors, result panels
│   ├── src/hooks/           application state (useAnalysis)
│   ├── src/lib/             complexity utilities (colours, growth models)
│   ├── src/pages/           Analyzer / History
│   ├── Dockerfile + nginx.conf
│   └── vite.config.ts       dev proxy /api → :8000
├── docs/                    this documentation
├── examples/                curated algorithm pairs
├── tests/                   backend unit & integration tests (pytest)
├── docker-compose.yml       db + backend + frontend
└── Makefile                 task runner
```

## Analysis pipeline

The orchestrator (`services/analysis_service.py`) runs a **pure dataflow** —
no stage touches the database or HTTP layer, which keeps every module
unit-testable in isolation:

```
                 ┌────────────┐
   code + mode ─►│   Parser   │─► AlgorithmIR × 2
                 └────────────┘      │
                         ┌───────────┴───────────┐
                         ▼                       ▼
                 ┌──────────────┐        ┌──────────────┐
                 │  Complexity  │        │  Complexity  │
                 │  Analyzer(A) │        │  Analyzer(B) │
                 └──────┬───────┘        └──────┬───────┘
                        └───────────┬───────────┘
                                    ▼
                          ┌───────────────────┐
                          │ Similarity Engine │  weighted feature vectors
                          └─────────┬─────────┘
                                    ▼
                         ┌────────────────────┐
              ┌─────────►│ Functional Analyzer│  consumes similarity score
              │          └─────────┬─────────┘
              │                    ▼
   ┌────────────────────┐  ┌────────────────────┐
   │  Benchmark Engine  │─►│ verdict refinement │  empirical output agreement
   │ (sandbox, A vs B)  │  └─────────┬──────────┘
   └────────────────────┘            ▼
                        ┌─────────────────────────┐
                        │ AI Explanation Layer    │  heuristic (default) / LLM
                        └────────────┬────────────┘
                                     ▼
                        ┌─────────────────────────┐
                        │ Report Generator        │  Markdown document
                        └─────────────────────────┘
```

Key design decisions:

* **Intermediate Representation (IR).** All parser backends normalise input
  into `AlgorithmIR` (functions, loops with bounds, recursion signatures,
  allocations, operations, semantic hints). Downstream services never see
  raw source code, so adding a new input language means adding one parser.
* **Cost algebra.** Complexity is computed symbolically as
  `Θ(n^deg · log n)` terms (see `docs/analysis-engine.md`), giving
  comparable, explainable results instead of opaque pattern matching.
* **Glass-box scoring.** Every similarity point is attributable to a named
  feature with a documented weight — essential for academic defensibility.
* **Empirical feedback loop.** The benchmark engine runs both algorithms on
  identical seeded inputs; if outputs match while keyword classification
  disagreed, execution evidence refines the equivalence verdict.
* **Graceful degradation.** Pseudocode and natural-language modes produce
  lower-confidence approximations instead of failing; Monaco falls back to a
  textarea when its CDN bundle cannot load; the LLM explainer falls back to
  the deterministic heuristic engine.

## Data model

```
users (1) ──── (n) projects (1) ──── (n) algorithms
                        │
                        └──── (n) analysis_runs ──── (n) reports
                                   │ references algorithm a & b
```

* **Algorithm** — a stored submission (name, mode, source) upserted by name
  per project so re-analysing the same algorithm does not duplicate rows.
* **AnalysisRun** — immutable record: raw request JSON, full result JSON,
  similarity score and verdict (denormalised for cheap history queries).
* **Report** — the generated Markdown document, served for download.

## Security notes

The benchmark engine executes user-submitted code. The first line of
defence is:

1. a **separate process** (`subprocess.run` with `python -I`),
2. **POSIX resource limits** (`RLIMIT_AS` 512 MB, `RLIMIT_CPU`),
3. a **hard wall-clock timeout** per driver,
4. a minimal environment and temporary working directory.

For a public production deployment this must be hardened further — run
workers inside ephemeral containers (gVisor/Firecracker), add rate limiting
and authentication. The service is structured so the sandbox can be swapped
without touching the analysis pipeline.
