/**
 * Complexity label utilities — colours, ordering and growth models.
 * Mirrors `backend/app/services/complexity/classes.py` so charts can render
 * theoretical reference curves without extra server round-trips.
 */

export type ComplexityTone = "excellent" | "good" | "fair" | "poor" | "critical";

/** Approximate asymptotic rank of a label (1 = O(1) … 10 = O(n!)). */
export function rankFromLabel(label: string): number {
  const l = label.toLowerCase();
  if (l.includes("n!") || l.includes("factorial")) return 10;
  if (l.includes("2")) return /2[ⁿ^n]|exp/.test(l) ? 9 : 5;
  if (l.includes("n³") || l.includes("n^3") || l.includes("cubic")) return 8;
  if (l.includes("n²") || l.includes("n^2") || l.includes("squared")) return 6;
  if (l.includes("n log n") || l.includes("nlogn")) return 5;
  if (l.includes("√n")) return 3;
  if (l.includes("log n") || l.includes("logn")) return 2;
  if (l.includes("(n)")) return 4;
  if (l.includes("v + e")) return 4;
  if (l.includes("(1)")) return 1;
  if (l.includes("n^")) {
    const exponent = parseFloat(l.split("n^")[1]);
    if (!Number.isNaN(exponent)) return Math.min(8, 4 + exponent - 1);
  }
  return 4; // unknown → assume linear
}

/** Colour tone for badges / charts based on how demanding a class is. */
export function toneForLabel(label: string): ComplexityTone {
  const rank = rankFromLabel(label);
  if (rank <= 2) return "excellent";
  if (rank <= 4) return "good";
  if (rank <= 5) return "fair";
  if (rank <= 7) return "poor";
  return "critical";
}

/** Tailwind classes for each tone (kept static for JIT friendliness). */
export const TONE_CLASSES: Record<ComplexityTone, string> = {
  excellent: "bg-ok/10 text-ok border-ok/40",
  good: "bg-ok/10 text-ok border-ok/40",
  fair: "bg-sky-500/10 text-sky-400 border-sky-500/40",
  poor: "bg-warn/10 text-warn border-warn/40",
  critical: "bg-bad/10 text-bad border-bad/40",
};

export const TONE_HEX: Record<ComplexityTone, string> = {
  excellent: "#3fb950",
  good: "#3fb950",
  fair: "#58a6ff",
  poor: "#d29922",
  critical: "#f85149",
};

/** Theoretical operation count for a label at input size n (chart model). */
export function growthForLabel(label: string, n: number): number {
  const x = Math.max(1, n);
  const l = label.toLowerCase();
  if (l.includes("n!")) return factorial(Math.min(x, 20));
  if (/2[ⁿ^n]/.test(l) || l.includes("exp")) return Math.pow(2, Math.min(x, 200));
  if (l.includes("n³") || l.includes("n^3")) return x * x * x;
  if (l.includes("n²") || l.includes("n^2")) return x * x;
  if (l.includes("n log n")) return x * Math.log2(x);
  if (l.includes("log n")) return Math.log2(x);
  if (l.includes("√n")) return Math.sqrt(x);
  if (l.includes("v + e")) return 2 * x;
  if (l.includes("(n)")) return x;
  if (l.includes("n^")) {
    const exponent = parseFloat(l.split("n^")[1]);
    if (!Number.isNaN(exponent)) return Math.pow(x, exponent);
  }
  return 1;
}

function factorial(k: number): number {
  let out = 1;
  for (let i = 2; i <= k; i++) out *= i;
  return out;
}

/** Standard reference classes rendered in the growth chart. */
export const REFERENCE_CLASSES = [
  "O(1)",
  "O(log n)",
  "O(n)",
  "O(n log n)",
  "O(n²)",
  "O(2ⁿ)",
] as const;

/** Formats milliseconds with adaptive precision. */
export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 0.01) return `${(ms * 1000).toFixed(1)} µs`;
  if (ms < 1) return `${ms.toFixed(3)} ms`;
  if (ms < 100) return `${ms.toFixed(2)} ms`;
  return `${ms.toFixed(0)} ms`;
}

/** Formats kilobytes. */
export function formatKb(kb: number | null | undefined): string {
  if (kb == null) return "—";
  if (kb < 1) return `${(kb * 1024).toFixed(0)} B`;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}
