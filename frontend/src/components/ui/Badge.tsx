import type { ReactNode } from "react";
import clsx from "clsx";
import { TONE_CLASSES, toneForLabel } from "../../lib/complexity";

interface BadgeProps {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "bad" | "info" | "algoA" | "algoB";
  className?: string;
}

const TONES: Record<NonNullable<BadgeProps["tone"]>, string> = {
  neutral: "bg-raised text-ink-muted border-edge-bright",
  ok: "bg-ok/10 text-ok border-ok/40",
  warn: "bg-warn/10 text-warn border-warn/40",
  bad: "bg-bad/10 text-bad border-bad/40",
  info: "bg-algoA/10 text-algoA border-algoA/40",
  algoA: "bg-algoA/10 text-algoA border-algoA/40",
  algoB: "bg-algoB/10 text-algoB border-algoB/40",
};

export function Badge({ children, tone = "neutral", className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Badge specialised for complexity labels (colours by asymptotic rank). */
export function ComplexityBadge({ label }: { label: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium",
        TONE_CLASSES[toneForLabel(label)],
      )}
    >
      {label}
    </span>
  );
}
