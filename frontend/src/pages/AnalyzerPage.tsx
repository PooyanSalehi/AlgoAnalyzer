import { ChevronRight, Play, BookOpen } from "lucide-react";
import clsx from "clsx";
import { CodeEditor } from "../components/CodeEditor";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SimilarityGauge } from "../components/results/SimilarityGauge";
import { ComplexityAtAGlance, ComplexityTable } from "../components/results/ComplexityTable";
import { GrowthChart } from "../components/results/GrowthChart";
import { BenchmarkSection } from "../components/results/BenchmarkCharts";
import { FunctionalPanel } from "../components/results/FunctionalPanel";
import { SimilarityBreakdown } from "../components/results/SimilarityBreakdown";
import { ExplanationPanel } from "../components/results/ExplanationPanel";
import { ReportPanel } from "../components/results/ReportPanel";
import { StructurePanel } from "../components/results/StructurePanel";
import type { AnalysisResult } from "../api/types";
import type { EditorForm } from "../hooks/useAnalysis";

const MODES: { value: EditorForm["mode"]; label: string }[] = [
  { value: "python", label: "Python" },
  { value: "pseudocode", label: "Pseudocode" },
  { value: "natural", label: "Natural language" },
];

const PIPELINE_STAGES = [
  "Parsing source (AST)",
  "Complexity analysis",
  "Similarity & functional comparison",
  "Sandboxed benchmarks",
  "Report generation",
];

function EditorCard({
  tone,
  form,
  onChange,
}: {
  tone: "A" | "B";
  form: EditorForm;
  onChange: (form: EditorForm) => void;
}) {
  const isA = tone === "A";
  return (
    <Card
      className="min-w-0"
      title={
        <span className="flex items-center gap-2">
          <span
            className={clsx(
              "inline-block h-2.5 w-2.5 rounded-full",
              isA ? "bg-algoA shadow-[0_0_8px_#58a6ff]" : "bg-algoB shadow-[0_0_8px_#bc8cff]",
            )}
          />
          Algorithm {tone}
        </span>
      }
      subtitle={isA ? "the reference implementation" : "the challenger"}
      actions={
        <div className="flex items-center gap-2">
          <input
            value={form.name}
            onChange={(e) => onChange({ ...form, name: e.target.value })}
            placeholder={`Algorithm ${tone} name`}
            className="w-36 rounded-md border border-edge bg-canvas px-2 py-1 text-xs text-ink outline-none placeholder:text-ink-subtle focus:border-algoA/60"
          />
          <select
            value={form.mode}
            onChange={(e) => onChange({ ...form, mode: e.target.value as EditorForm["mode"] })}
            className="rounded-md border border-edge bg-canvas px-2 py-1 text-xs text-ink-muted outline-none focus:border-algoA/60"
          >
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      }
    >
      <div className="-m-4 overflow-hidden rounded-xl">
        <CodeEditor
          value={form.code}
          onChange={(code) => onChange({ ...form, code })}
          language={form.mode === "python" ? "python" : "plaintext"}
          fallbackLanguage={form.mode}
          height={340}
        />
      </div>
    </Card>
  );
}

function PipelineProgress() {
  return (
    <Card className="border-ok/30">
      <div className="flex flex-col items-center gap-4 py-6">
        <div className="flex items-center gap-1.5">
          {PIPELINE_STAGES.map((_, i) => (
            <span
              key={i}
              className="h-1.5 w-10 animate-pulse-soft rounded-full bg-ok/70"
              style={{ animationDelay: `${i * 220}ms` }}
            />
          ))}
        </div>
        <p className="text-sm text-ink-muted">
          Running analysis pipeline — parsing, complexity math, benchmarks…
        </p>
        <ul className="grid gap-1 text-xs text-ink-subtle sm:grid-cols-2">
          {PIPELINE_STAGES.map((stage) => (
            <li key={stage} className="flex items-center gap-1.5">
              <ChevronRight className="h-3 w-3 text-ok" />
              {stage}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

export function AnalyzerPage({
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
  onAnalyze,
  onLoadExample,
}: {
  formA: EditorForm;
  setFormA: (f: EditorForm) => void;
  formB: EditorForm;
  setFormB: (f: EditorForm) => void;
  runBenchmarks: boolean;
  setRunBenchmarks: (v: boolean) => void;
  loading: boolean;
  error: string | null;
  result: AnalysisResult | null;
  examples: { id: string; title: string; description: string }[];
  onAnalyze: () => void;
  onLoadExample: (id: string) => void;
}) {
  return (
    <div className="space-y-6">
      {/* ---------------- toolbar ---------------- */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-edge bg-surface px-4 py-3 shadow-card">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-ink-subtle" />
          <select
            onChange={(e) => e.target.value && onLoadExample(e.target.value)}
            defaultValue=""
            className="max-w-[280px] rounded-md border border-edge bg-canvas px-2.5 py-1.5 text-xs text-ink outline-none focus:border-algoA/60"
          >
            <option value="">Load example comparison…</option>
            {examples.map((pair) => (
              <option key={pair.id} value={pair.id}>
                {pair.title}
              </option>
            ))}
          </select>
        </div>

        <label className="flex cursor-pointer select-none items-center gap-2 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={runBenchmarks}
            onChange={(e) => setRunBenchmarks(e.target.checked)}
            className="h-3.5 w-3.5 accent-[#2ea043]"
          />
          Run empirical benchmarks
        </label>

        <Button
          variant="primary"
          size="lg"
          loading={loading}
          onClick={onAnalyze}
          className="ml-auto"
        >
          {!loading && <Play className="h-4 w-4" />}
          {loading ? "Analyzing…" : "Analyze & Compare"}
        </Button>
      </div>

      {error && (
        <div className="rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          {error}
        </div>
      )}

      {/* ---------------- editors ---------------- */}
      <div className="grid gap-5 xl:grid-cols-2">
        <EditorCard tone="A" form={formA} onChange={setFormA} />
        <EditorCard tone="B" form={formB} onChange={setFormB} />
      </div>

      {/* ---------------- results ---------------- */}
      {loading && <PipelineProgress />}

      {result && !loading && (
        <div className="space-y-6">
          {/* summary row */}
          <div className="grid gap-5 lg:grid-cols-[auto_1fr]">
            <Card className="flex items-center justify-center">
              <SimilarityGauge score={result.similarity.score} band={result.similarity.band} />
            </Card>
            <div className="grid gap-5 sm:grid-cols-2">
              <FunctionalPanel result={result} />
              <ComplexityAtAGlance result={result} />
            </div>
          </div>

          <ComplexityTable result={result} />

          <GrowthChart result={result} />

          <BenchmarkSection result={result} />

          <div className="grid gap-5 xl:grid-cols-2">
            <SimilarityBreakdown result={result} />
            <ExplanationPanel result={result} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <StructurePanel analysis={result.a} tone="A" />
            <StructurePanel analysis={result.b} tone="B" />
          </div>

          <ReportPanel result={result} />

          {result.warnings.length > 0 && (
            <div className="rounded-xl border border-warn/30 bg-warn/5 px-4 py-3">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-warn">
                Analysis notes
              </p>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-ink-muted">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
