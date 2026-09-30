import { useCallback, useEffect, useState } from "react";
import { History, RefreshCw, Search } from "lucide-react";
import { api } from "../api/client";
import type { AnalysisRunSummary } from "../api/types";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

/** Database-backed analysis history with one-click reload into the analyzer. */
export function HistoryPage({
  version,
  onLoad,
}: {
  version: number;
  onLoad: (id: number) => void;
}) {
  const [runs, setRuns] = useState<AnalysisRunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRuns(await api.listAnalyses(50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, version]);

  return (
    <div className="space-y-5">
      <Card
        title="Analysis History"
        subtitle="Every analysis is persisted with its report (PostgreSQL in production, SQLite in dev)"
        icon={<History className="h-4 w-4 text-ok" />}
        actions={
          <Button variant="ghost" size="sm" onClick={refresh} loading={loading}>
            {!loading && <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </Button>
        }
      >
        {error && <p className="text-sm text-bad">{error}</p>}

        {!error && runs.length === 0 && !loading && (
          <div className="flex flex-col items-center gap-2 py-10 text-ink-subtle">
            <Search className="h-6 w-6" />
            <p className="text-sm">No analyses yet — run your first comparison in the Analyzer tab.</p>
          </div>
        )}

        {runs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-xs uppercase tracking-wide text-ink-subtle">
                  <th className="pb-2 pr-4 font-medium">#</th>
                  <th className="pb-2 pr-4 font-medium">Date</th>
                  <th className="pb-2 pr-4 font-medium text-algoA">Algorithm A</th>
                  <th className="pb-2 pr-4 font-medium text-algoB">Algorithm B</th>
                  <th className="pb-2 pr-4 font-medium">Similarity</th>
                  <th className="pb-2 pr-4 font-medium">Verdict</th>
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-edge/60 last:border-0 hover:bg-raised/60">
                    <td className="py-2.5 pr-4 font-mono text-xs text-ink-subtle">{run.id}</td>
                    <td className="py-2.5 pr-4 text-xs text-ink-muted">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-4 text-ink">{run.algorithm_a_name}</td>
                    <td className="py-2.5 pr-4 text-ink">{run.algorithm_b_name}</td>
                    <td className="py-2.5 pr-4">
                      {run.similarity_score != null ? (
                        <Badge tone={run.similarity_score >= 85 ? "ok" : run.similarity_score >= 40 ? "warn" : "bad"}>
                          {run.similarity_score.toFixed(0)}%
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="max-w-[240px] truncate py-2.5 pr-4 text-xs text-ink-muted" title={run.functional_verdict ?? ""}>
                      {run.functional_verdict ?? "—"}
                    </td>
                    <td className="py-2.5">
                      <Button variant="outline" size="sm" onClick={() => onLoad(run.id)}>
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
