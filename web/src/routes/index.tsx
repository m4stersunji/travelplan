import { createFileRoute, Link } from "@tanstack/react-router";
import { useQueries, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { TripCard } from "@/components/trip-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { shortDateToIso } from "@/lib/format";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const overviewQ = useQuery({ queryKey: ["overview"], queryFn: api.getOverview });
  const overview = overviewQ.data ?? [];

  const trends = useQueries({
    queries: overview.map((r) => {
      const isoDate = shortDateToIso(r.date);
      return {
        queryKey: ["trend", r.route, isoDate, 14],
        queryFn: () => api.getTrend(r.route, isoDate, 14),
      };
    }),
  });

  if (overviewQ.isLoading) return <SkeletonGrid />;
  if (overviewQ.isError)
    return (
      <EmptyState
        title="Could not load trips"
        body="Check the network and try again."
        action={<Button onClick={() => overviewQ.refetch()}>Retry</Button>}
      />
    );
  if (!overview.length)
    return (
      <EmptyState
        title="No trips yet"
        body="Add your first trip to start tracking prices."
        action={
          <Link to="/add">
            <Button>Add a trip</Button>
          </Link>
        }
      />
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Travelplan</h1>
      <p className="text-xs text-muted-foreground mb-4">
        Auto-checks every 2 hours · last update {overview[0]?.lastCheck}
      </p>

      <div className="space-y-3">
        {overview.map((r, i) => {
          const trend = trends[i]?.data ?? [];
          const prices = trend.map((p) => p.bestPrice).filter((v) => v > 0);
          const min = prices.length ? Math.min(...prices) : 0;
          const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
          const isoDate = shortDateToIso(r.date);
          const id = `${r.route}-${isoDate}`;
          return (
            <TripCard
              key={id}
              id={id}
              tripName={r.route}
              cheapestCombo={r.bestPrice}
              goLabel={r.date}
              cheapestAirline={r.cheapestAirline}
              bestSource={r.bestSource}
              sparklineData={prices.slice(-14)}
              historicalAvg={avg}
              historicalMin={min}
            />
          );
        })}
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 rounded-xl border bg-muted/40 animate-pulse"
          aria-hidden
        />
      ))}
    </div>
  );
}
