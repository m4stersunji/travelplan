"use client";
/**
 * PriceTrendChart — line chart of best price over time.
 * Recharts, theme-aware via CSS variables, responsive height.
 */
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";

interface Point {
  scrapedAt: string;
  bestPrice: number;
  airline?: string;
}

interface Props {
  data: Point[];
  height?: number;
  showAvg?: boolean;
}

function formatTs(ts: string): string {
  // "2026-04-26 13:08:56" → "Apr 26"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ts);
  if (!m) return ts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const monthIdx = parseInt(m[2]!, 10) - 1;
  const day = parseInt(m[3]!, 10);
  return `${months[monthIdx]} ${day}`;
}

export function PriceTrendChart({ data, height = 240, showAvg = true }: Props) {
  if (!data.length) {
    return (
      <div className="text-center py-12 text-sm text-muted-foreground">
        No price history yet
      </div>
    );
  }
  const avg =
    data.reduce((sum, d) => sum + d.bestPrice, 0) / Math.max(data.length, 1);
  const chartData = data.map((d) => ({ ...d, label: formatTs(d.scrapedAt) }));
  const min = Math.min(...data.map((d) => d.bestPrice));
  const max = Math.max(...data.map((d) => d.bestPrice));
  const yPad = (max - min) * 0.1 || 100;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
          minTickGap={20}
        />
        <YAxis
          domain={[Math.floor(min - yPad), Math.ceil(max + yPad)]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => `฿${(v as number).toLocaleString()}`}
          width={60}
        />
        <Tooltip
          contentStyle={{
            background: "var(--background)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value) => [`฿${(value as number).toLocaleString()}`, "Best price"]}
          labelFormatter={(label) => label}
        />
        {showAvg && (
          <ReferenceLine
            y={avg}
            stroke="#94a3b8"
            strokeDasharray="3 3"
            label={{
              value: `avg ฿${Math.round(avg).toLocaleString()}`,
              fontSize: 10,
              fill: "#94a3b8",
              position: "right",
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey="bestPrice"
          stroke="#16a34a"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
