"""Integration tests for the REST API."""
from __future__ import annotations

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


def test_health(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_examples_endpoint(api_client):
    body = api_client.get("/api/examples").json()
    assert len(body) >= 5
    assert all({"id", "title", "a", "b"} <= set(pair) for pair in body)


def test_analyze_persists_and_returns_full_result(api_client):
    response = api_client.post("/api/analyze", json={
        "algorithm_a": {"name": "Merge Sort", "code": MERGE_SORT, "mode": "python"},
        "algorithm_b": {"name": "Quick Sort", "code": QUICK_SORT, "mode": "python"},
        "options": {"run_benchmarks": True},
    })
    assert response.status_code == 200
    result = response.json()

    # Structure of the response contract.
    assert result["analysis_id"] is not None
    for side in ("a", "b"):
        assert {"overview", "complexity"} <= set(result[side])
    assert len(result["complexity_table"]) == 5
    assert 0 <= result["similarity"]["score"] <= 100
    assert result["functional"]["verdict"]
    assert len(result["growth"]) >= 5
    assert result["report_markdown"].startswith("# AlgoAnalyzer")
    assert result["explanation"]

    # The textbook result for the flagship example.
    assert result["a"]["complexity"]["time"]["worst"] == "O(n log n)"
    assert result["b"]["complexity"]["time"]["worst"] == "O(n²)"
    assert result["a"]["complexity"]["space"]["auxiliary"] == "O(n)"
    assert result["b"]["complexity"]["space"]["auxiliary"] == "O(log n)"
    assert result["similarity"]["score"] >= 85


def test_history_endpoints(api_client):
    api_client.post("/api/analyze", json={
        "algorithm_a": {"name": "A", "code": MERGE_SORT},
        "algorithm_b": {"name": "B", "code": QUICK_SORT},
    })
    history = api_client.get("/api/analyses").json()
    assert len(history) == 1
    run_id = history[0]["id"]

    detail = api_client.get(f"/api/analyses/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["similarity"]["score"] >= 85

    report = api_client.get(f"/api/analyses/{run_id}/report")
    assert report.status_code == 200
    assert "## 3. Complexity Comparison" in report.json()["content"]


def test_syntax_error_returns_400(api_client):
    response = api_client.post("/api/analyze", json={
        "algorithm_a": {"code": "def broken(:", "mode": "python"},
        "algorithm_b": {"code": "def ok():\n    return 1", "mode": "python"},
    })
    assert response.status_code == 400
    assert "syntax" in response.json()["detail"].lower()


def test_missing_run_returns_404(api_client):
    assert api_client.get("/api/analyses/12345").status_code == 404


def test_projects_and_algorithms_crud(api_client):
    project = api_client.post("/api/projects", json={"name": "Semester Work"})
    assert project.status_code == 201

    algo = api_client.post("/api/algorithms",
                           json={"name": "heap_sort", "mode": "python", "code": "def heap_sort(a):\n    return a\n"})
    assert algo.status_code == 201

    listing = api_client.get("/api/algorithms").json()
    assert any(a["name"] == "heap_sort" for a in listing)

    delete = api_client.delete(f"/api/algorithms/{algo.json()['id']}")
    assert delete.status_code == 204


def test_openapi_docs_available(api_client):
    schema = api_client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/analyze" in paths
    assert "/api/analyses" in paths
