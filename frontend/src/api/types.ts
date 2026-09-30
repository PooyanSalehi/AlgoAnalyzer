/**
 * TypeScript mirrors of the backend pydantic schemas (API contract).
 * Keep in sync with `backend/app/schemas/analysis.py`.
 */

export type InputMode = "python" | "pseudocode" | "natural";

export interface AlgorithmInput {
  name?: string | null;
  code: string;
  mode: InputMode;
}

export interface AnalyzeOptions {
  run_benchmarks: boolean;
  ai_provider: "heuristic" | "openai";
}

export interface AnalyzeRequest {
  algorithm_a: AlgorithmInput;
  algorithm_b: AlgorithmInput;
  options: AnalyzeOptions;
}

export interface ArgSummary {
  name: string;
  kind: string;
  annotation?: string | null;
  has_default: boolean;
}

export interface LoopSummary {
  kind: string;
  depth: number;
  bound: string;
  line: number;
  note: string;
}

export interface AllocationSummary {
  kind: string;
  size: string;
  note: string;
}

export interface FunctionSummary {
  name: string;
  args: ArgSummary[];
  returns: string[];
  loops: LoopSummary[];
  max_loop_depth: number;
  is_recursive: boolean;
  recursive_call_count: number;
  recursion_shrink: string | null;
  recursion_branching: number;
  memoized: boolean;
  conditionals: number;
  early_exit: boolean;
  allocations: AllocationSummary[];
  builtin_calls: string[];
  method_calls: string[];
  data_structures: string[];
  operations: Record<string, number>;
  hints: string[];
  notes: string[];
}

export interface AlgorithmOverview {
  name: string;
  mode: InputMode;
  line_count: number;
  imports: string[];
  functions: FunctionSummary[];
  primary: string | null;
  purpose: string;
  confidence: number;
  warnings: string[];
}

export interface TimeComplexity {
  best: string;
  average: string;
  worst: string;
  best_rank: number;
  average_rank: number;
  worst_rank: number;
  pattern: string;
  recurrence: string | null;
  explanations: string[];
}

export interface SpaceComplexity {
  auxiliary: string;
  total: string;
  recursion_depth: string | null;
  explanations: string[];
}

export interface AlgorithmComplexity {
  time: TimeComplexity;
  space: SpaceComplexity;
}

export interface ComplexityComparisonRow {
  metric: string;
  a: string;
  b: string;
}

export interface SimilarityFeature {
  feature: string;
  score: number;
  weight: number;
  detail: string;
}

export interface SimilarityReport {
  score: number;
  band: string;
  summary: string;
  features: SimilarityFeature[];
}

export interface FunctionalReport {
  equivalent: boolean;
  verdict: string;
  confidence: number;
  purpose_a: string;
  purpose_b: string;
  input_analysis: string;
  output_analysis: string;
  operation_analysis: string;
  reasoning: string[];
  empirical_output_match: boolean | null;
  empirical_samples: number;
}

export interface BenchmarkPoint {
  n: number;
  time_ms: number | null;
  memory_kb: number | null;
  error: string | null;
}

export interface AlgorithmBenchmark {
  name: string;
  status: string;
  points: BenchmarkPoint[];
  notes: string[];
}

export interface BenchmarkComparisonRow {
  n: number;
  time_a_ms: number;
  time_b_ms: number;
  ratio: number | null;
}

export interface BenchmarkReport {
  status: string;
  a: AlgorithmBenchmark;
  b: AlgorithmBenchmark;
  output_agreement: boolean | null;
  agreement_samples: number;
  comparison: BenchmarkComparisonRow[];
  notes: string[];
}

export interface GrowthPoint {
  n: number;
  a: number;
  b: number;
}

export interface AlgorithmAnalysis {
  overview: AlgorithmOverview;
  complexity: AlgorithmComplexity;
}

export interface AnalysisResult {
  analysis_id: number | null;
  created_at: string;
  a: AlgorithmAnalysis;
  b: AlgorithmAnalysis;
  complexity_table: ComplexityComparisonRow[];
  similarity: SimilarityReport;
  functional: FunctionalReport;
  benchmark: BenchmarkReport;
  growth: GrowthPoint[];
  growth_labels: Record<string, string>;
  explanation: string;
  explanation_provider: string;
  report_markdown: string;
  warnings: string[];
}

export interface AnalysisRunSummary {
  id: number;
  created_at: string;
  algorithm_a_name: string;
  algorithm_b_name: string;
  similarity_score: number | null;
  functional_verdict: string | null;
}

export interface ExampleAlgorithm {
  name: string;
  code: string;
  mode: InputMode;
}

export interface ExamplePair {
  id: string;
  title: string;
  description: string;
  a: ExampleAlgorithm;
  b: ExampleAlgorithm;
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  database: string;
}
