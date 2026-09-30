import { Activity, GitCompareArrows, History, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { HealthStatus } from "../../api/types";

export type Tab = "analyzer" | "history";

const TABS: { id: Tab; label: string; icon: typeof Activity }[] = [
  { id: "analyzer", label: "Analyzer", icon: GitCompareArrows },
  { id: "history", label: "History", icon: History },
];

export function Header({
  tab,
  onTabChange,
}: {
  tab: Tab;
  onTabChange: (tab: Tab) => void;
}) {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((h) => !cancelled && setHealth(h))
      .catch(() => !cancelled && setHealth(null));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="sticky top-0 z-20 border-b border-edge bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 lg:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-ok/40 bg-ok/10">
            <Activity className="h-5 w-5 text-ok" />
          </div>
          <div>
            <h1 className="text-[15px] font-semibold leading-tight text-white">
              Algo<span className="text-ok">Analyzer</span>
            </h1>
            <p className="text-[11px] leading-tight text-ink-subtle">
              Algorithm analysis &amp; comparison platform
            </p>
          </div>
        </div>

        <nav className="flex items-center gap-1 rounded-lg border border-edge bg-surface p-1">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={clsx(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
                tab === id
                  ? "bg-raised text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                  : "text-ink-muted hover:text-ink",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2 text-[11px] text-ink-subtle">
          {health ? (
            <>
              <ShieldCheck className="h-3.5 w-3.5 text-ok" />
              <span className="font-mono">
                API v{health.version} · {health.database}
              </span>
            </>
          ) : (
            <span className="font-mono text-warn">API offline — run the backend</span>
          )}
        </div>
      </div>
    </header>
  );
}
