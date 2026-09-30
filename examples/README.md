# Example Algorithms

Curated algorithm pairs used by the platform's **Load example comparison…**
selector (served from `GET /api/examples` and embedded in
`backend/app/data/examples.py`).

Each Python file is directly executable and analyser-ready — paste it into
either Monaco editor, or load the preconfigured pairs from the UI.

## Recommended comparison pairs

| Pair | What it demonstrates |
|---|---|
| `merge_sort.py` vs `quick_sort.py` | Equal average case, different worst case and auxiliary space (the classic trade-off) |
| `binary_search.py` vs `linear_search.py` | O(log n) on sorted data vs an O(n) scan with an O(1) best case |
| `fibonacci_recursive.py` vs `fibonacci_memoized.py` | Overlapping subproblems → Θ(φⁿ), fixed by memoisation → Θ(n) |
| `bubble_sort.py` vs `insertion_sort.py` | Two adaptive quadratic sorts, both Θ(n) on sorted input |
| `merge_sort.py` vs `graph_bfs.py` | Different problem domains → low similarity, not equivalent |
| `pseudocode_*.txt` | The pseudocode input mode (structural line-based parser) |
| `natural_language_*.txt` | The natural-language input mode (keyword model, low confidence) |

## Try from the command line

```bash
curl -s -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "$(python3 - <<'EOF'
import json, pathlib
def algo(path, name):
    return {"name": name, "code": pathlib.Path(path).read_text(), "mode": "python"}
print(json.dumps({
    "algorithm_a": algo("examples/merge_sort.py", "Merge Sort"),
    "algorithm_b": algo("examples/quick_sort.py", "Quick Sort"),
    "options": {"run_benchmarks": True},
}))
EOF
)" | python3 -m json.tool | head -40
```
