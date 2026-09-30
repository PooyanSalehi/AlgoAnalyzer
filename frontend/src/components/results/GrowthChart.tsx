import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp } from "lucide-react";
import { Card } from "../ui/Card";
import { REFERENCE_CLASSES, growthForLabel } from "../../lib/complexity";
import type { AnalysisResult } from "../../api/types";

const REFERENCE_COLORS = ["#6e7681", "#8b949e", "#9198a1", "#a8b3bd", "#c0cad3", "#dae2ea"];

/**
 * Theoretical growth chart (log–log): worst-case operation counts for both
 * algorithms, overlaid with the canonical complexity reference curves.
 */
export function GrowthChart({ result }: { result: AnalysisResult }) {
  const sizes = result.growth.map((p) => p.n);
  const labelA = result.growth_labels.a;
  const labelB = result.growth_labels.b;

  const data = sizes.map((n) => {
    const row: Record<string, number> = {
      n,
      [`A · ${labelA}`]: result.growth.find((p) => p.n === n)?.a ?? 0,
      [`B · ${labelB}`]: result.growth.find((p) => p.n === n)?.b ?? 0,
    };
    for (const cls of REFERENCE_CLASSES) {
      row[cls] = growthForLabel(cls, n);
    }
    return row;
  });

  return (
    <Card
      title="Complexity Growth (theoretical)"
      subtitle={`Modelled operation count in the worst case — A: ${labelA} · B: ${labelB} — against reference classes (log scale)`}
      icon={<TrendingUp className="h-4 w-4 text-ok" />}
    >
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
            <CartesianGrid stroke="#21262d" strokeDasharray="3 3" />
            <XAxis
              dataKey="n"
              stroke="#6e7681"
              tick={{ fontSize: 11, fontFamily: "ui-monospace" }}
              scale="log"
              domain={["auto", "auto"]}
              allowDataOverflow
            />
            <YAxis
              stroke="#6e7681"
              tick={{ fontSize: 11, fontFamily: "ui-monospace" }}
              scale="log"
              domain={["auto", "auto"]}
              allowDataOverflow
              tickFormatter={(v: number) => (v >= 1000 ? `${v.toExponential(0)}` : `${v}`)}
            />
            <Tooltip
              contentStyle={{
                background: "#161b22",
                border: "1px solid #30363d",
                borderRadius: 10,
                fontSize: 12,
              }}
              labelStyle={{ color: "#e6edf3", fontFamily: "ui-monospace" }}
              formatter={(value: number | string) => Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey={`A · ${labelA}`}
              stroke="#58a6ff"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#58a6ff" }}
            />
            <Line
              type="monotone"
              dataKey={`B · ${labelB}`}
              stroke="#bc8cff"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "#bc8cff" }}
            />
            {REFERENCE_CLASSES.map((cls, i) => (
              <Line
                key={cls}
                type="monotone"
                dataKey={cls}
                stroke={REFERENCE_COLORS[i]}
                strokeWidth={1}
                strokeDasharray="4 4"
                dot={false}
                legendType="none"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
