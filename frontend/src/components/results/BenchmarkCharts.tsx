import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Gauge, MemoryStick } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { formatKb, formatMs } from "../../lib/complexity";
import type { AnalysisResult } from "../../api/types";

const tooltipStyle = {
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 10,
  fontSize: 12,
} as const;

/** Measured execution time vs input size for both algorithms. */
function TimeChart({ result }: { result: AnalysisResult }) {
  const nameA = result.a.overview.name;
  const nameB = result.b.overview.name;
  const data = (result.benchmark.comparison.length
    ? result.benchmark.comparison.map((row) => ({
        n: row.n,
        [nameA]: row.time_a_ms,
        [nameB]: row.time_b_ms,
      }))
    : result.benchmark.a.points
        .map((pa, i) => ({
          n: pa.n,
          [nameA]: pa.time_ms,
          [nameB]: result.benchmark.b.points[i]?.time_ms ?? null,
        }))
  ).filter((row) => row[nameA] != null || row[nameB] != null);

  return (
    <Card
      title="Execution Time"
      subtitle="Best of 3 runs per input size (sandboxed subprocess, deterministic inputs)"
      icon={<Gauge className="h-4 w-4 text-ok" />}
      className="min-w-0"
    >
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#21262d" strokeDasharray="3 3" />
            <XAxis dataKey="n" stroke="#6e7681" tick={{ fontSize: 11, fontFamily: "ui-monospace" }} />
            <YAxis
              stroke="#6e7681"
              tick={{ fontSize: 11, fontFamily: "ui-monospace" }}
              tickFormatter={(v: number) => `${v}ms`}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatMs(Number(v))} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey={nameA} stroke="#58a6ff" strokeWidth={2.5} dot={{ r: 3 }} />
            <Line type="monotone" dataKey={nameB} stroke="#bc8cff" strokeWidth={2.5} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

/** Measured peak memory (tracemalloc) vs input size. */
function MemoryChart({ result }: { result: AnalysisResult }) {
  const nameA = result.a.overview.name;
  const nameB = result.b.overview.name;
  const sizes = Array.from(
    new Set([
      ...result.benchmark.a.points.map((p) => p.n),
      ...result.benchmark.b.points.map((p) => p.n),
    ]),
  ).sort((x, y) => x - y);

  const data = sizes.map((n) => ({
    n,
    [nameA]: result.benchmark.a.points.find((p) => p.n === n)?.memory_kb ?? null,
    [nameB]: result.benchmark.b.points.find((p) => p.n === n)?.memory_kb ?? null,
  }));

  return (
    <Card
      title="Memory Usage"
      subtitle="Peak traced allocations per run (auxiliary memory only)"
      icon={<MemoryStick className="h-4 w-4 text-ok" />}
      className="min-w-0"
    >
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 14, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#21262d" strokeDasharray="3 3" />
            <XAxis dataKey="n" stroke="#6e7681" tick={{ fontSize: 11, fontFamily: "ui-monospace" }} />
            <YAxis
              stroke="#6e7681"
              tick={{ fontSize: 11, fontFamily: "ui-monospace" }}
              tickFormatter={(v: number) => formatKb(v).replace(" ", "")}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatKb(Number(v))} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey={nameA} stroke="#58a6ff" strokeWidth={2.5} dot={{ r: 3 }} />
            <Line type="monotone" dataKey={nameB} stroke="#bc8cff" strokeWidth={2.5} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

/** Numeric benchmark table + agreement badge. */
function BenchmarkTable({ result }: { result: AnalysisResult }) {
  const nameA = result.a.overview.name;
  const nameB = result.b.overview.name;
  const memA = new Map(
    result.benchmark.a.points.filter((p) => p.memory_kb != null).map((p) => [p.n, p.memory_kb]),
  );
  const memB = new Map(
    result.benchmark.b.points.filter((p) => p.memory_kb != null).map((p) => [p.n, p.memory_kb]),
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <thead>
          <tr className="border-b border-edge text-xs uppercase tracking-wide text-ink-subtle">
            <th className="pb-2 pr-4 font-medium">n</th>
            <th className="pb-2 pr-4 font-medium text-algoA">{nameA} time</th>
            <th className="pb-2 pr-4 font-medium text-algoB">{nameB} time</th>
            <th className="pb-2 pr-4 font-medium">ratio A/B</th>
            <th className="pb-2 pr-4 font-medium text-algoA">{nameA} mem</th>
            <th className="pb-2 font-medium text-algoB">{nameB} mem</th>
          </tr>
        </thead>
        <tbody className="font-mono text-[13px]">
          {result.benchmark.comparison.map((row) => (
            <tr key={row.n} className="border-b border-edge/60 last:border-0">
              <td className="py-2 pr-4 text-ink-muted">{row.n}</td>
              <td className="py-2 pr-4 text-ink">{formatMs(row.time_a_ms)}</td>
              <td className="py-2 pr-4 text-ink">{formatMs(row.time_b_ms)}</td>
              <td className="py-2 pr-4 text-ink-muted">
                {row.ratio != null ? `${row.ratio.toFixed(2)}×` : "—"}
              </td>
              <td className="py-2 pr-4 text-ink-muted">{formatKb(memA.get(row.n) ?? null)}</td>
              <td className="py-2 text-ink-muted">{formatKb(memB.get(row.n) ?? null)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BenchmarkSection({ result }: { result: AnalysisResult }) {
  const bench = result.benchmark;
  const anyPoints =
    bench.a.points.some((p) => p.time_ms != null) || bench.b.points.some((p) => p.time_ms != null);

  if (!anyPoints) {
    return (
      <Card
        title="Empirical Benchmarks"
        subtitle="Sandboxed execution measurements"
        icon={<Gauge className="h-4 w-4 text-ok" />}
      >
        <div className="space-y-2 text-sm text-ink-muted">
          <p className="flex items-center gap-2">
            <Badge tone="warn">skipped</Badge>
            Benchmarks are unavailable for this comparison.
          </p>
          <ul className="list-disc space-y-1 pl-5 text-xs text-ink-subtle">
            {bench.a.notes.map((n, i) => <li key={`a-${i}`}>{n}</li>)}
            {bench.b.notes.map((n, i) => <li key={`b-${i}`}>{n}</li>)}
          </ul>
        </div>
      </Card>
    );
  }

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <TimeChart result={result} />
      <MemoryChart result={result} />
      <div className="xl:col-span-2">
        <Card
          title="Measured Values"
          subtitle="Raw benchmark output — times are the best of 3 repetitions"
          icon={<Gauge className="h-4 w-4 text-ok" />}
          actions={
            bench.output_agreement != null ? (
              <Badge tone={bench.output_agreement ? "ok" : "warn"}>
                {bench.output_agreement
                  ? `✓ identical outputs on ${bench.agreement_samples} shared inputs`
                  : `⚠ outputs differed on ${bench.agreement_samples} shared inputs`}
              </Badge>
            ) : undefined
          }
        >
          <BenchmarkTable result={result} />
          <p className="mt-3 text-xs text-ink-subtle">
            {bench.notes.map((n, i) => <span key={i} className="mr-3">{n}</span>)}
          </p>
        </Card>
      </div>
    </div>
  );
}
