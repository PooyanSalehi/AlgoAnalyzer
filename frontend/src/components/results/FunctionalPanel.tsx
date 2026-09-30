import { CheckCircle2, GitCompareArrows, Lightbulb, XCircle } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import type { AnalysisResult } from "../../api/types";

/**
 * Functional equivalence panel: verdict, purpose chips, I/O analysis and
 * the reasoning trail produced by the functional analyzer.
 */
export function FunctionalPanel({ result }: { result: AnalysisResult }) {
  const functional = result.functional;
  return (
    <Card
      title="Functional Equivalence"
      subtitle="Do both algorithms solve the same computational problem?"
      icon={<GitCompareArrows className="h-4 w-4 text-ok" />}
      actions={
        <Badge tone={functional.equivalent ? "ok" : "bad"}>
          {functional.equivalent ? "EQUIVALENT" : "NOT EQUIVALENT"}
        </Badge>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-algoA/40 bg-algoA/10 px-3 py-1 font-medium text-algoA">
            A · {functional.purpose_a}
          </span>
          <span className="text-ink-subtle">vs</span>
          <span className="rounded-full border border-algoB/40 bg-algoB/10 px-3 py-1 font-medium text-algoB">
            B · {functional.purpose_b}
          </span>
          <span className="ml-auto font-mono text-ink-subtle">
            confidence {(functional.confidence * 100).toFixed(0)}%
          </span>
        </div>

        <p className="rounded-lg border border-edge bg-canvas p-3 text-sm text-ink">
          {functional.verdict}
        </p>

        <dl className="grid gap-2 text-xs text-ink-muted">
          <div>
            <dt className="font-semibold text-ink">Input behaviour</dt>
            <dd className="mt-0.5">{functional.input_analysis}</dd>
          </div>
          <div>
            <dt className="font-semibold text-ink">Output behaviour</dt>
            <dd className="mt-0.5">{functional.output_analysis}</dd>
          </div>
        </dl>

        <div>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-subtle">
            <Lightbulb className="h-3.5 w-3.5 text-warn" /> Reasoning
          </p>
          <ul className="space-y-2">
            {functional.reasoning.map((reason, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink-muted">
                {functional.equivalent ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-ok/70" />
                ) : (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-bad/70" />
                )}
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
