"use client";
/**
 * PriceTrends — dropdown to pick route+date, then full Recharts line chart.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PriceTrendChart } from "@/components/price-trend-chart";

interface RoutePick {
  route: string;
  isoDate: string;
  label: string;
}

const MONTH_NAME_TO_NUM: Record<string, string> = {
  Jan: "01", Feb: "02", Mar: "03", Apr: "04", May: "05", Jun: "06",
  Jul: "07", Aug: "08", Sep: "09", Oct: "10", Nov: "11", Dec: "12",
};

function shortDateToIso(label: string): string {
  const [day, mon] = label.split(" ");
  if (!day || !mon) return label;
  const month = MONTH_NAME_TO_NUM[mon] || "01";
  const year = new Date().getFullYear();
  return `${year}-${month}-${day.padStart(2, "0")}`;
}

export default function PriceTrends() {
  const overviewQ = useQuery({ queryKey: ["overview"], queryFn: api.getOverview });

  const picks: RoutePick[] = useMemo(() => {
    const list = overviewQ.data || [];
    return list.map((r) => ({
      route: r.route,
      isoDate: shortDateToIso(r.date),
      label: `${r.route} ${r.date}`,
    }));
  }, [overviewQ.data]);

  const [pickKey, setPickKey] = useState<string>("");
  const current = picks.find((p) => `${p.route}|${p.isoDate}` === pickKey) || picks[0];

  const trendQ = useQuery({
    queryKey: ["trend", current?.route, current?.isoDate, 30],
    queryFn: () =>
      current
        ? api.getTrend(current.route, current.isoDate, 30)
        : Promise.resolve([]),
    enabled: !!current,
  });

  if (overviewQ.isLoading) {
    return <div className="h-72 rounded-xl border bg-muted/30 animate-pulse" />;
  }
  if (!picks.length) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        No trips yet — add one in the Trips tab.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <Select
        value={pickKey || `${picks[0]!.route}|${picks[0]!.isoDate}`}
        onValueChange={(v) => setPickKey(v ?? "")}
      >
        <SelectTrigger className="max-w-xs">
          <SelectValue placeholder="Pick a route" />
        </SelectTrigger>
        <SelectContent>
          {picks.map((p) => (
            <SelectItem
              key={`${p.route}|${p.isoDate}`}
              value={`${p.route}|${p.isoDate}`}
            >
              {p.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{current?.label}</CardTitle>
        </CardHeader>
        <CardContent>
          {trendQ.isLoading ? (
            <div className="h-60 rounded bg-muted/30 animate-pulse" />
          ) : (
            <PriceTrendChart data={trendQ.data || []} height={280} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
