import type { ReactNode } from "react";
import clsx from "clsx";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
}

/** GitHub-style dark panel. */
export function Card({ children, className, title, subtitle, icon, actions }: CardProps) {
  return (
    <section
      className={clsx(
        "rounded-xl border border-edge bg-surface shadow-card backdrop-blur-sm",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-edge px-4 py-3">
          <div className="min-w-0">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
              {icon}
              {title}
            </h3>
            {subtitle && <p className="mt-0.5 text-xs text-ink-muted">{subtitle}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
