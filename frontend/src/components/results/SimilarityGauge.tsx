import { useId } from "react";

/** Colour for a similarity score band. */
function bandColor(score: number): string {
  if (score >= 85) return "#3fb950";
  if (score >= 70) return "#58a6ff";
  if (score >= 40) return "#d29922";
  return "#f85149";
}

/** Animated SVG donut showing the conceptual similarity score. */
export function SimilarityGauge({
  score,
  band,
  size = 180,
}: {
  score: number;
  band: string;
  size?: number;
}) {
  const gradientId = useId();
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const color = bandColor(clamped);

  return (
    <div className="relative flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.45" />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#21262d"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-bold text-white">{clamped.toFixed(0)}</span>
        <span className="text-[11px] uppercase tracking-widest text-ink-subtle">/ 100</span>
      </div>
      <span
        className="mt-1 rounded-full border px-3 py-1 text-xs font-semibold"
        style={{ color, borderColor: `${color}66`, backgroundColor: `${color}14` }}
      >
        {band}
      </span>
    </div>
  );
}
