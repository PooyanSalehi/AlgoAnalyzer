# REST API Reference

Base URL (development): `http://localhost:8000` · Interactive docs:
`/docs` (Swagger UI) and `/redoc`.

All request/response bodies are JSON. Errors use the FastAPI convention:
`{"detail": "message"}` with status 400 (bad input), 404 (missing resource)
or 500 (unexpected).

---

## POST `/api/analyze`

Runs the full pipeline on two algorithms, persists the run + report and
returns the complete analysis.

### Request

```json
{
  "algorithm_a": {
    "name": "Merge Sort",
    "code": "def merge_sort(arr): ...",
    "mode": "python"
  },
  "algorithm_b": {
    "name": "Quick Sort",
    "code": "def quick_sort(arr): ...",
    "mode": "python"
  },
  "options": {
    "run_benchmarks": true,
    "ai_provider": "heuristic"
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `algorithm_a/b.name` | string? | display name (defaults to "Algorithm A/B") |
| `algorithm_a/b.code` | string | Python source, pseudocode or natural language (1–100 000 chars) |
| `algorithm_a/b.mode` | enum | `python` · `pseudocode` · `natural` |
| `options.run_benchmarks` | bool | default `true`; skipped automatically for non-Python input |
| `options.ai_provider` | enum | `heuristic` (offline) · `openai` (needs `OPENAI_API_KEY`, falls back gracefully) |

### Response (`AnalysisResult`)

| Field | Contents |
|---|---|
| `analysis_id` | id of the persisted run (`null` if persistence failed) |
| `created_at` | ISO timestamp |
| `a`, `b` | `{ overview, complexity }` per algorithm |
| `a.overview` | parsed structure: functions, loops, recursion, allocations, hints, purpose, confidence, warnings |
| `a.complexity.time` | `best/average/worst` labels + ranks, detected `pattern`, `recurrence`, mathematical `explanations[]` |
| `a.complexity.space` | `auxiliary`, `total`, `recursion_depth`, `explanations[]` |
| `complexity_table` | 5 ready-to-render rows (time best/avg/worst, space aux/total) |
| `similarity` | `score` (0–100), `band`, `summary`, per-`features[]` breakdown (score, weight, detail) |
| `functional` | `equivalent`, `verdict`, `confidence`, purposes, I/O analyses, `reasoning[]`, empirical match |
| `benchmark` | per-algorithm `points[]` (n, time_ms, memory_kb), `comparison[]` rows, `output_agreement`, `notes[]`, `status` |
| `growth` | theoretical worst-case operation counts for charting |
| `growth_labels` | complexity labels used for the growth series |
| `explanation` | AI-layer prose (Markdown) |
| `explanation_provider` | `heuristic` \| `openai` |
| `report_markdown` | the full generated report |
| `warnings` | analysis caveats (e.g. approximation mode) |

### Example

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"algorithm_a":{"name":"Merge Sort","code":"def merge_sort(a):\n    if len(a)<=1: return a\n    m=len(a)//2\n    return merge_sort(a[:m])+merge_sort(a[m:])\n","mode":"python"},"algorithm_b":{"name":"Quick Sort","code":"def quick_sort(a):\n    if len(a)<=1: return a\n    p=a[0]\n    return quick_sort([x for x in a[1:] if x<p])+[p]+quick_sort([x for x in a[1:] if x>=p])\n","mode":"python"},"options":{"run_benchmarks":true}}'
```

---

## GET `/api/analyses?limit=25`

Analysis history (most recent first). Returns:

```json
[{
  "id": 1,
  "created_at": "2026-09-30T21:00:00Z",
  "algorithm_a_name": "Merge Sort",
  "algorithm_b_name": "Quick Sort",
  "similarity_score": 93.3,
  "functional_verdict": "Likely functionally equivalent — same problem, compatible I/O"
}]
```

## GET `/api/analyses/{id}`

Replays a stored analysis — returns the same `AnalysisResult` shape as
`POST /api/analyze` (404 if unknown).

## GET `/api/analyses/{id}/report`

The stored Markdown report: `{ id, analysis_run_id, format, content, created_at }`.

---

## GET `/api/examples`

Curated example comparisons (id, title, description, both algorithms).
Used by the frontend's example selector.

## GET `/api/health`

`{ status, app, version, database }` — used by the header status pill.

---

## Projects & algorithms (CRUD)

| Method & path | Purpose |
|---|---|
| `GET /api/projects` | list workspaces with counts |
| `POST /api/projects` | `{ name, description? }` → created project |
| `GET /api/algorithms?project_id=` | stored algorithms (optionally filtered) |
| `POST /api/algorithms` | upsert `{ name, mode, code }` into the default project |
| `DELETE /api/algorithms/{id}` | remove a stored algorithm |

---

## Error semantics

* **400** — unparseable Python (`Python syntax error at line …`), or an
  invalid calling convention for benchmarks (reported as `status: "skipped"`
  inside a 200 response instead whenever the rest of the analysis can run).
* **404** — unknown analysis run / algorithm / report.
* **422** — request schema violation (pydantic validation).
