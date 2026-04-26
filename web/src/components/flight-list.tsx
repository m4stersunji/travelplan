import { FlightRow } from "@/components/flight-row";
import { EmptyState } from "@/components/empty-state";
import type { FlightRow as FlightRowType } from "@/lib/api-client";

export function FlightList({
  flights,
  emptyTitle = "No flights yet",
}: {
  flights: FlightRowType[];
  emptyTitle?: string;
}) {
  if (!flights.length) return <EmptyState title={emptyTitle} />;
  return (
    <div className="space-y-2">
      {flights.map((f, i) => (
        <FlightRow key={i} flight={f} />
      ))}
    </div>
  );
}
