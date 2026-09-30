import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";
import { Loader2 } from "lucide-react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
}

const VARIANTS = {
  primary:
    "bg-accent text-white hover:bg-[#3fb950] border border-[#2ea04366] shadow-[0_0_20px_rgba(46,160,67,0.25)]",
  ghost: "bg-transparent text-ink-muted hover:bg-raised hover:text-ink border border-transparent",
  outline: "bg-raised text-ink hover:border-edge-bright border border-edge",
  danger: "bg-bad/15 text-bad hover:bg-bad/25 border border-bad/40",
};

const SIZES = {
  sm: "px-2.5 py-1.5 text-xs",
  md: "px-3.5 py-2 text-sm",
  lg: "px-5 py-2.5 text-sm",
};

export function Button({
  variant = "outline",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-algoA",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}
