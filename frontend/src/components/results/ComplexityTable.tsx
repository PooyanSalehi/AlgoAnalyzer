import { MemoryStick, Timer } from "lucide-react";
import { Card } from "../ui/Card";
import { ComplexityBadge } from "../ui/Badge";
import type { AnalysisResult } from "../../api/types";

/**
 * The headline comparison table: best / average / worst time and
 * auxiliary / total space, side by side with coloured badges.
 */
export function ComplexityTable({ result }: { result: AnalysisResult }) {
  const nameA = result.a.overview.name;
  const nameB = result.b.overview.name;

  const timeRows = result.complexity_table.filter((r) => r.metric.startsWith("Time"));
  const spaceRows = result.complexity_table.filter((r) => r.metric.startsWith("Space"));

  const renderTable = (rows: { metric: string; a: string; b: string }[], title: string, icon: React.ReactNode) => (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-sm">
        <thead>
          <tr className="border-b border-edge text-xs uppercase tracking-wide text-ink-subtle">
            <th className="pb-2 pr-4 font-medium">{title}</th>
            <th className="pb-2 pr-4 font-medium text-algoA">
              <span className="inline-flex items-center gap-1.5">{icon}{nameA}</span>
            </th>
            <th className="pb-2 font-medium text-algoB">
              <span className="inline-flex items-center gap-1.5">{icon}{nameB}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.metric} className="border-b border-edge/60 last:border-0">
              <td className="py-2.5 pr-4 text-ink-muted">{row.metric.replace("Time — ", "").replace("Space — ", "")}</td>
              <td className="py-2.5 pr-4"><ComplexityBadge label={row.a} /></td>
              <td className="py-2.5"><ComplexityBadge label={row.b} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <Card
      title="Complexity Comparison"
      subtitle="Asymptotic bounds derived from loop algebra, recurrence solving and pattern recognition"
      icon={<Timer className="h-4 w-4 text-ok" />}
    >
      <div className="grid gap-8 lg:grid-cols-2">
        {renderTable(timeRows, "Time", <span className="h-1.5 w-1.5 rounded-full bg-algoA" />)}
        {renderTable(spaceRows, "Space", <span className="h-1.5 w-1.5 rounded-full bg-algoB" />)}
      </div>
      <div className="mt-4 grid gap-4 border-t border-edge pt-4 lg:grid-cols-2">
        <RecurrenceBlock
          name={nameA}
          pattern={result.a.complexity.time.pattern}
          recurrence={result.a.complexity.time.recurrence}
        />
        <RecurrenceBlock
          name={nameB}
          pattern={result.b.complexity.time.pattern}
          recurrence={result.b.complexity.time.recurrence}
        />
      </div>
    </Card>
  );
}

function RecurrenceBlock({
  name,
  pattern,
  recurrence,
}: {
  name: string;
  pattern: string;
  recurrence: string | null;
}) {
  return (
    <div className="rounded-lg border border-edge bg-canvas p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">{name}</p>
      <p className="mt-1 text-sm text-ink-muted">{pattern}</p>
      {recurrence && (
        <p className="mt-2 rounded bg-raised px-2 py-1 font-mono text-xs text-algoA">
          {recurrence}
        </p>
      )}
    </div>
  );
}

/** Compact at-a-glance strip used above the fold. */
export function ComplexityAtAGlance({ result }: { result: AnalysisResult }) {
  const cells = [
    { label: "Worst time", a: result.a.complexity.time.worst, b: result.b.complexity.time.worst },
    { label: "Average time", a: result.a.complexity.time.average, b: result.b.complexity.time.average },
    { label: "Aux. space", a: result.a.complexity.space.auxiliary, b: result.b.complexity.space.auxiliary },
  ];
  return (
    <Card
      title="At a Glance"
      icon={<MemoryStick className="h-4 w-4 text-ok" />}
      subtitle="Headline complexity of both algorithms"
    >
      <div className="space-y-3">
        {cells.map((cell) => (
          <div key={cell.label} className="grid grid-cols-[1fr_auto_auto] items-center gap-3">
            <span className="text-xs text-ink-subtle">{cell.label}</span>
            <ComplexityBadge label={cell.a} />
            <ComplexityBadge label={cell.b} />
          </div>
        ))}
      </div>
    </Card>
  );
}
