import { useMemo } from "react";
import { Download, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import type { AnalysisResult } from "../../api/types";

/** Full generated report (Markdown) with download button. */
export function ReportPanel({ result }: { result: AnalysisResult }) {
  const filename = useMemo(() => {
    const safe = (s: string) => s.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase();
    return `algoanalyzer-${safe(result.a.overview.name)}-vs-${safe(result.b.overview.name)}.md`;
  }, [result]);

  const download = () => {
    const blob = new Blob([result.report_markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card
      title="Analysis Report"
      subtitle="Professional Markdown report — also stored in the database history"
      icon={<FileText className="h-4 w-4 text-ok" />}
      actions={
        <Button variant="outline" size="sm" onClick={download}>
          <Download className="h-3.5 w-3.5" />
          Download .md
        </Button>
      }
    >
      <div className="max-h-[520px] overflow-y-auto pr-2">
        <div className="md-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.report_markdown}</ReactMarkdown>
        </div>
      </div>
    </Card>
  );
}
