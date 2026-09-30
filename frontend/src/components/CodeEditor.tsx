import Editor, { type OnMount } from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

const MONACO_OPTIONS = {
  minimap: { enabled: false },
  fontSize: 13,
  lineNumbers: "on" as const,
  scrollBeyondLastLine: false,
  renderLineHighlight: "line" as const,
  smoothScrolling: true,
  cursorBlinking: "smooth" as const,
  padding: { top: 12, bottom: 12 },
  automaticLayout: true,
  tabSize: 4,
  wordWrap: "on" as const,
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
  overviewRulerLanes: 0,
  bracketPairColorization: { enabled: true },
};

/**
 * Monaco editor with a graceful degradation path: if the editor bundle
 * cannot be loaded (e.g. offline environment), we fall back to a plain
 * textarea so the application stays fully usable.
 */
export function CodeEditor({
  value,
  onChange,
  language,
  fallbackLanguage,
  height = 340,
}: {
  value: string;
  onChange: (value: string) => void;
  language: string; // editor highlighting language
  fallbackLanguage: string; // mode used for the textarea placeholder logic
  height?: number;
}) {
  const [monacoFailed, setMonacoFailed] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    timer.current = setTimeout(() => setMonacoFailed(true), 8000);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const handleMount: OnMount = () => {
    if (timer.current) clearTimeout(timer.current);
  };

  if (monacoFailed) {
    return (
      <div className="relative" style={{ height }}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
          data-mode={fallbackLanguage}
          className={clsx(
            "h-full w-full resize-none rounded-b-xl border-0 bg-canvas p-3",
            "font-mono text-[13px] leading-relaxed text-ink outline-none",
          )}
          placeholder={
            fallbackLanguage === "natural"
              ? "Describe the algorithm in plain English…"
              : fallbackLanguage === "pseudocode"
                ? "FUNCTION Sort(A)\n    …\nEND FUNCTION"
                : "def algorithm(input):\n    …"
          }
        />
        <span className="absolute right-2 top-2 rounded bg-raised px-1.5 py-0.5 text-[10px] text-ink-subtle">
          plain text mode
        </span>
      </div>
    );
  }

  return (
    <div style={{ height }} className="overflow-hidden rounded-b-xl bg-canvas">
      <Editor
        value={value}
        onChange={(v) => onChange(v ?? "")}
        language={language}
        theme="vs-dark"
        options={MONACO_OPTIONS}
        onMount={handleMount}
        loading={
          <div className="flex h-full items-center justify-center text-xs text-ink-subtle">
            loading editor…
          </div>
        }
      />
    </div>
  );
}
