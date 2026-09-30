import { Braces, Repeat, ArrowRightLeft, Boxes, GitBranch, Zap } from "lucide-react";
import clsx from "clsx";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import type { AlgorithmAnalysis } from "../../api/types";

/**
 * Parsed-structure panel: what the AST parser extracted from each
 * algorithm (loops, recursion, allocations, data structures, operations).
 * This is the "evidence" behind the complexity analysis.
 */
export function StructurePanel({
  analysis,
  tone,
}: {
  analysis: AlgorithmAnalysis;
  tone: "A" | "B";
}) {
  const primary = analysis.overview.functions.find(
    (f) => f.name === analysis.overview.primary,
  );

  const accent = tone === "A" ? "text-algoA" : "text-algoB";
  const border = tone === "A" ? "border-algoA/30" : "border-algoB/30";

  return (
    <Card
      title={
        <span>
          Parsed Structure — <span className={accent}>{analysis.overview.name}</span>
        </span>
      }
      subtitle={`mode: ${analysis.overview.mode} · purpose: ${analysis.overview.purpose} · ${
        analysis.overview.line_count
      } lines · confidence ${(analysis.overview.confidence * 100).toFixed(0)}%`}
      icon={<Braces className={clsx("h-4 w-4", tone === "A" ? "text-algoA" : "text-algoB")} />}
      className={clsx("min-w-0", border)}
    >
      {!primary ? (
        <p className="text-sm text-ink-muted">No function structure detected.</p>
      ) : (
        <div className="space-y-4 text-sm">
          {/* signature */}
          <div className="rounded-lg border border-edge bg-canvas p-3">
            <p className="font-mono text-xs">
              <span className={accent}>def</span> {primary.name}(
              {primary.args.map((a) => (
                <span key={a.name} className="text-ink-muted">
                  {a.name}
                  <span className="text-ink-subtle">: {a.kind}</span>
                  {a.has_default ? <span className="text-ink-subtle"> = …</span> : null},{" "}
                </span>
              ))}
              ) → <span className="text-ok">{primary.returns.join(" | ") || "None"}</span>
            </p>
          </div>

          {/* feature grid */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <Stat
              icon={<Repeat className="h-3.5 w-3.5" />}
              label="Loops"
              value={`${primary.loops.length} (depth ${primary.max_loop_depth})`}
            />
            <Stat
              icon={<GitBranch className="h-3.5 w-3.5" />}
              label="Recursive"
              value={primary.is_recursive ? `yes ×${primary.recursive_call_count}` : "no"}
            />
            <Stat
              icon={<Zap className="h-3.5 w-3.5" />}
              label="Conditionals"
              value={String(primary.conditionals)}
            />
            <Stat
              icon={<ArrowRightLeft className="h-3.5 w-3.5" />}
              label="Early exit"
              value={primary.early_exit ? "yes" : "no"}
            />
            <Stat
              icon={<Boxes className="h-3.5 w-3.5" />}
              label="Structures"
              value={primary.data_structures.join(", ") || "—"}
            />
            <Stat
              icon={<Braces className="h-3.5 w-3.5" />}
              label="Allocations"
              value={String(primary.allocations.length)}
            />
          </div>

          {/* loops table */}
          {primary.loops.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                Loop nest
              </p>
              <ul className="space-y-1 font-mono text-xs text-ink-muted">
                {primary.loops.map((loop, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="text-ink-subtle">L{loop.line}</span>
                    <span className="text-ink">{loop.kind}</span>
                    <Badge tone={loop.bound === "n" ? "info" : loop.bound === "log" ? "ok" : "neutral"}>
                      bound: {loop.bound}
                    </Badge>
                    <span className="text-ink-subtle">depth {loop.depth}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* recursion info */}
          {primary.is_recursive && (
            <div className="rounded-lg border border-edge bg-canvas p-3 text-xs">
              <p className="text-ink">
                Recursion: <span className="text-ok">{primary.recursive_call_count}</span> self-call(s)
                {primary.recursion_shrink && (
                  <>
                    {" "}· shrink:{" "}
                    <span className={accent}>{primary.recursion_shrink}</span>
                  </>
                )}
                {primary.memoized && (
                  <Badge tone="ok" className="ml-2">memoized</Badge>
                )}
              </p>
            </div>
          )}

          {/* math explanations */}
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-subtle">
              Mathematical reasoning
            </p>
            <ul className="list-disc space-y-1.5 pl-4 text-xs text-ink-muted">
              {analysis.complexity.time.explanations.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
              {analysis.complexity.space.explanations.map((line, i) => (
                <li key={`s-${i}`}>{line}</li>
              ))}
            </ul>
          </div>

          {analysis.overview.warnings.length > 0 && (
            <ul className="list-disc space-y-1 pl-4 text-[11px] text-warn/90">
              {analysis.overview.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-edge bg-canvas px-2.5 py-2">
      <p className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-ink-subtle">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 truncate font-mono text-xs text-ink" title={value}>
        {value}
      </p>
    </div>
  );
}
