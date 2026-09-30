import { Sparkles } from "lucide-react";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AnalysisResult } from "../../api/types";

/**
 * AI explanation layer output: human-readable interpretation of the full
 * analysis (provider badge shows which explainer produced the text).
 */
export function ExplanationPanel({ result }: { result: AnalysisResult }) {
  return (
    <Card
      title="AI Explanation"
      subtitle="Human-readable interpretation of the comparison"
      icon={<Sparkles className="h-4 w-4 text-ok" />}
      actions={
        <Badge tone="info">
          {result.explanation_provider === "openai" ? "LLM" : "heuristic engine"}
        </Badge>
      }
    >
      <div className="md-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.explanation}</ReactMarkdown>
      </div>
    </Card>
  );
}
