import { Card } from "../ui/Card";
import type { AnalysisResult } from "../../api/types";

/**
 * Glass-box scoring: each weighted feature of the similarity engine with
 * its individual contribution, rendered as horizontal bars.
 */
export function SimilarityBreakdown({ result }: { result: AnalysisResult }) {
  const features = [...result.similarity.features].sort(
    (a, b) => b.weight * b.score - a.weight * a.score,
  );

  const label = (feature: string) =>
    feature
      .split("_")
      .map((w) => w[0].toUpperCase() + w.slice(1))
      .join(" ");

  return (
    <Card
      title="Similarity Breakdown"
      subtitle="Weighted feature-vector comparison — why the score is what it is"
    >
      <ul className="space-y-3.5">
        {features.map((feature) => (
          <li key={feature.feature}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="font-medium text-ink">{label(feature.feature)}</span>
              <span className="font-mono text-ink-subtle">
                {(feature.score * 100).toFixed(0)}% × {feature.weight.toFixed(0)} pts
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.max(2, feature.score * 100)}%`,
                  background:
                    feature.score >= 0.7
                      ? "linear-gradient(90deg,#2ea043,#3fb950)"
                      : feature.score >= 0.4
                        ? "linear-gradient(90deg,#9e6a03,#d29922)"
                        : "linear-gradient(90deg,#b62324,#f85149)",
                }}
              />
            </div>
            <p className="mt-1 text-[11px] text-ink-subtle">{feature.detail}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
