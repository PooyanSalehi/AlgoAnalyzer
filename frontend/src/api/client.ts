/**
 * Thin fetch wrapper around the AlgoAnalyzer REST API.
 *
 * All calls use relative `/api` paths: the Vite dev server and the nginx
 * production container both proxy them to the FastAPI backend, so the
 * browser never needs to know the backend origin.
 */
import type {
  AnalysisResult,
  AnalysisRunSummary,
  AnalyzeRequest,
  ExamplePair,
  HealthStatus,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthStatus>("/api/health"),

  analyze: (payload: AnalyzeRequest) =>
    request<AnalysisResult>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listAnalyses: (limit = 25) =>
    request<AnalysisRunSummary[]>(`/api/analyses?limit=${limit}`),

  getAnalysis: (id: number) => request<AnalysisResult>(`/api/analyses/${id}`),

  getReport: (id: number) =>
    request<{ content: string }>(`/api/analyses/${id}/report`),

  examples: () => request<ExamplePair[]>("/api/examples"),
};
