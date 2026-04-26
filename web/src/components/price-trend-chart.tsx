import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { formatThb } from "@/lib/format";

interface Point {
  scrapedAt: string;
  bestPrice: number;
}

interface Props {
  data: Point[];
  height?: number;
}

function tickLabel(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ts);
  if (!m) return ts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(m[2], 10) - 1]} ${parseInt(m[3], 10)}`;
}

export function PriceTrendChart({ data, height = 240 }: Props) {
  if (!data.length) {
    return (
      <div className="text-center py-12 text-sm text-muted-foreground">
        No price history yet
      </div>
    );
  }
  const avg = data.reduce((s, d) => s + d.bestPrice, 0) / data.length;
  const min = Math.min(...data.map((d) => d.bestPrice));
  const max = Math.max(...data.map((d) => d.bestPrice));
  const yPad = (max - min) * 0.1 || 100;
  const chartData = data.map((d) => ({ ...d, label: tickLabel(d.scrapedAt) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis
          domain={[Math.floor(min - yPad), Math.ceil(max + yPad)]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => formatThb(v as number)}
          width={64}
        />
        <Tooltip
          formatter={(v) => [formatThb(v as number), "Best price"]}
          labelFormatter={(label) => label as string}
        />
        <ReferenceLine
          y={avg}
          stroke="#94a3b8"
          strokeDasharray="3 3"
          label={{
            value: `avg ${formatThb(Math.round(avg))}`,
            fontSize: 10,
            fill: "#94a3b8",
            position: "right",
          }}
        />
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
