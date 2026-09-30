/**
 * Central application state: the two editor forms, example catalogue,
 * analysis lifecycle (loading / error / result) and history reload signal.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  AnalysisResult,
  ExamplePair,
  InputMode,
} from "../api/types";

export interface EditorForm {
  name: string;
  code: string;
  mode: InputMode;
}

export const DEFAULT_FORM_A: EditorForm = {
  name: "Merge Sort",
  mode: "python",
  code: `def merge_sort(arr):
    """Classic top-down merge sort: divide, conquer, merge."""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left_half = merge_sort(arr[:mid])
    right_half = merge_sort(arr[mid:])

    return merge(left_half, right_half)


def merge(left, right):
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
`,
};

export const DEFAULT_FORM_B: EditorForm = {
  name: "Quick Sort",
  mode: "python",
  code: `def quick_sort(arr, low=0, high=None):
    """In-place quick sort with Lomuto partitioning."""
    if high is None:
        high = len(arr) - 1

    if low < high:
        pivot_index = partition(arr, low, high)
        quick_sort(arr, low, pivot_index - 1)
        quick_sort(arr, pivot_index + 1, high)
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
`,
};

export function useAnalysis() {
  const [formA, setFormA] = useState<EditorForm>(DEFAULT_FORM_A);
  const [formB, setFormB] = useState<EditorForm>(DEFAULT_FORM_B);
  const [runBenchmarks, setRunBenchmarks] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [examples, setExamples] = useState<ExamplePair[]>([]);
  const [historyVersion, setHistoryVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .examples()
      .then((pairs) => {
        if (!cancelled) setExamples(pairs);
      })
      .catch(() => {
        /* examples are non-critical; the selector simply stays empty */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        algorithm_a: { name: formA.name || "Algorithm A", code: formA.code, mode: formA.mode },
        algorithm_b: { name: formB.name || "Algorithm B", code: formB.code, mode: formB.mode },
        options: { run_benchmarks: runBenchmarks, ai_provider: "heuristic" as const },
      };
      const analysis = await api.analyze(payload);
      setResult(analysis);
      setHistoryVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [formA, formB, runBenchmarks]);

  const loadExample = useCallback((pairId: string) => {
    const pair = examples.find((p) => p.id === pairId);
    if (!pair) return;
    setFormA({ name: pair.a.name, code: pair.a.code, mode: pair.a.mode });
    setFormB({ name: pair.b.name, code: pair.b.code, mode: pair.b.mode });
    setResult(null);
    setError(null);
  }, [examples]);

  const loadHistoryEntry = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const analysis = await api.getAnalysis(id);
      setResult(analysis);
      setFormA((f) => ({
        ...f,
        name: analysis.a.overview.name,
        mode: analysis.a.overview.mode,
      }));
      setFormB((f) => ({
        ...f,
        name: analysis.b.overview.name,
        mode: analysis.b.overview.mode,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load history entry");
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    formA,
    setFormA,
    formB,
    setFormB,
    runBenchmarks,
    setRunBenchmarks,
    loading,
    error,
    result,
    examples,
    analyze,
    loadExample,
    loadHistoryEntry,
    historyVersion,
  };
}
