import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PriceTrendChart } from "@/components/price-trend-chart";
import { FlightList } from "@/components/flight-list";
import { VerdictBadge } from "@/components/verdict-badge";
import { EmptyState } from "@/components/empty-state";
import { formatThb, isoToShortDate } from "@/lib/format";

export const Route = createFileRoute("/trip/$id")({
  component: TripDetail,
});

function parseId(id: string): { route: string; isoDate: string } | null {
  // id = "BKK-DAD-2026-05-29"
  const m = id.match(/^([A-Z]{3}-[A-Z]{3})-(\d{4}-\d{2}-\d{2})$/);
  if (!m) return null;
  return { route: m[1], isoDate: m[2] };
}

function TripDetail() {
  const { id } = Route.useParams();
  const parsed = parseId(id);

  const trendQ = useQuery({
    queryKey: ["trend", parsed?.route, parsed?.isoDate, 30],
    queryFn: () => api.getTrend(parsed!.route, parsed!.isoDate, 30),
    enabled: !!parsed,
  });

  const flightsQ = useQuery({
    queryKey: ["flights", parsed?.route, parsed?.isoDate, 5],
    queryFn: () =>
      api.getFlights({ route: parsed!.route, date: parsed!.isoDate, limit: 5 }),
    enabled: !!parsed,
  });

  if (!parsed) {
    return <EmptyState title="Invalid trip id" body={`Could not parse ${id}`} />;
  }

  const trend = trendQ.data ?? [];
  const flights = flightsQ.data ?? [];
  const prices = trend.map((p) => p.bestPrice).filter((v) => v > 0);
  const min = prices.length ? Math.min(...prices) : 0;
  const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
  const current = prices.length ? prices[prices.length - 1]! : 0;

  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-4 hover:text-foreground">
        <ArrowLeft className="size-4" /> Home
      </Link>

      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold leading-tight">{parsed.route}</h1>
          <p className="text-xs text-muted-foreground mt-1">{isoToShortDate(parsed.isoDate)}</p>
        </div>
        {avg > 0 && (
          <VerdictBadge
            currentBest={current}
            historicalAvg={avg}
            historicalMin={min}
            showRationale
          />
        )}
      </div>

      <div className="text-3xl font-bold mb-4">
        {formatThb(current)}
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-sm">Price history (30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {trendQ.isLoading ? (
            <div className="h-60 rounded bg-muted/30 animate-pulse" />
          ) : (
            <PriceTrendChart data={trend} />
          )}
          {prices.length > 0 && (
            <>
              <Separator className="my-3" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>min {formatThb(min)}</span>
                <span>avg {formatThb(Math.round(avg))}</span>
                <span>max {formatThb(Math.max(...prices))}</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <h2 className="text-sm font-semibold mb-2">Top 5 flights</h2>
      {flightsQ.isLoading ? (
        <div className="h-32 rounded-xl border bg-muted/30 animate-pulse" />
      ) : (
        <FlightList flights={flights} emptyTitle="No flights cached for this date" />
      )}

      <div className="mt-6 flex gap-2">
        <Button variant="outline" size="sm" onClick={() => trendQ.refetch()}>
          Refresh
        </Button>
      </div>
    </div>
  );
}
