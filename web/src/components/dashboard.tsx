"use client";
/**
 * Dashboard — overview tab. Shows TripCard for each route with verdict + sparkline.
 */
import { useQueries, useQuery } from "@tanstack/react-query";
import { api, type OverviewRow, type PriceHistoryPoint } from "@/lib/api-client";
import { TripCard } from "@/components/trip-card";

interface RouteData extends OverviewRow {
  isoDate: string;
}

const MONTH_NAME_TO_NUM: Record<string, string> = {
  Jan: "01", Feb: "02", Mar: "03", Apr: "04", May: "05", Jun: "06",
  Jul: "07", Aug: "08", Sep: "09", Oct: "10", Nov: "11", Dec: "12",
};

function shortDateToIso(label: string): string {
  // "29 May" → "2026-05-29" (assumes current year context)
  const [day, mon] = label.split(" ");
  if (!day || !mon) return label;
  const month = MONTH_NAME_TO_NUM[mon] || "01";
  const year = new Date().getFullYear();
  return `${year}-${month}-${day.padStart(2, "0")}`;
}

export default function Dashboard() {
  const overviewQ = useQuery({
    queryKey: ["overview"],
    queryFn: api.getOverview,
  });

  const overview = overviewQ.data || [];
  const routes: RouteData[] = overview.map((r) => ({
    ...r,
    isoDate: shortDateToIso(r.date),
  }));

  const trends = useQueries({
    queries: routes.map((r) => ({
      queryKey: ["trend", r.route, r.isoDate],
      queryFn: () => api.getTrend(r.route, r.isoDate, 14),
      enabled: !!r.isoDate,
    })),
  });

  if (overviewQ.isLoading) return <SkeletonGrid />;
  if (overviewQ.isError) {
    return (
      <div className="text-center py-12 text-sm text-destructive">
        Failed to load dashboard. Try again later.
      </div>
    );
  }
  if (!routes.length) {
    return (
      <div className="text-center py-12 text-sm text-muted-foreground">
        No trips yet. Add one in the Trips tab.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {routes.map((r, i) => {
        const trend: PriceHistoryPoint[] = trends[i]?.data ?? [];
        const prices = trend.map((p) => p.bestPrice).filter((v) => v > 0);
        const min = prices.length ? Math.min(...prices) : 0;
        const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
        return (
          <TripCard
            key={`${r.route}-${r.date}`}
            tripName={r.route}
            cheapestCombo={r.bestPrice}
            goDate={r.date}
            backDate=""
            cheapestAirline={r.cheapestAirline}
            bestSource={r.bestSource}
            sparklineData={prices.slice(-14)}
            historicalAvg={avg}
            historicalMin={min}
          />
        );
      })}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="h-40 rounded-xl border bg-muted/30 animate-pulse"
          aria-hidden
        />
      ))}
    </div>
  );
}
