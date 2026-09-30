import { useState } from "react";
import { Header, type Tab } from "./components/layout/Header";
import { AnalyzerPage } from "./pages/AnalyzerPage";
import { HistoryPage } from "./pages/HistoryPage";
import { useAnalysis } from "./hooks/useAnalysis";

export default function App() {
  const [tab, setTab] = useState<Tab>("analyzer");
  const analysis = useAnalysis();

  return (
    <div className="min-h-screen">
      <Header tab={tab} onTabChange={setTab} />

      <main className="mx-auto max-w-[1500px] px-4 py-6 lg:px-6">
        {tab === "analyzer" ? (
          <AnalyzerPage
            formA={analysis.formA}
            setFormA={analysis.setFormA}
            formB={analysis.formB}
            setFormB={analysis.setFormB}
            runBenchmarks={analysis.runBenchmarks}
            setRunBenchmarks={analysis.setRunBenchmarks}
            loading={analysis.loading}
            error={analysis.error}
            result={analysis.result}
            examples={analysis.examples}
            onAnalyze={analysis.analyze}
            onLoadExample={analysis.loadExample}
          />
        ) : (
          <HistoryPage
            version={analysis.historyVersion}
            onLoad={(id) => {
              void analysis.loadHistoryEntry(id);
              setTab("analyzer");
            }}
          />
        )}
      </main>

      <footer className="border-t border-edge py-5 text-center text-xs text-ink-subtle">
        AlgoAnalyzer · university project · FastAPI + React + TypeScript + PostgreSQL
      </footer>
    </div>
  );
}
