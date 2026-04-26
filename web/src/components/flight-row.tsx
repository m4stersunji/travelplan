import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatThb, formatDuration } from "@/lib/format";
import type { FlightRow as FlightRowType } from "@/lib/api-client";

export function FlightRow({ flight }: { flight: FlightRowType }) {
  const price = flight.bestBookingPrice && flight.bestBookingPrice > 0
    ? flight.bestBookingPrice
    : flight.priceThb;
  const showSource =
    flight.bestBookingSource && flight.bestBookingSource !== flight.airline;
  const dur = flight.durationMinutes ? formatDuration(flight.durationMinutes) : null;
  return (
    <Card>
      <CardContent className="p-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium truncate">{flight.airline}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {flight.departureTime} → {flight.arrivalTime}
            {dur && <span className="ml-2">({dur})</span>}
          </p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {flight.isDirect ? (
              <Badge variant="secondary" className="text-[10px]">Direct</Badge>
            ) : (
              <Badge variant="outline" className="text-[10px]">
                {flight.numStops ?? 1}-stop
              </Badge>
            )}
            {flight.checkedBaggage && (
              <Badge variant="outline" className="text-[10px]">
                {flight.checkedBaggage}
              </Badge>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="font-bold text-lg">{formatThb(price)}</p>
          {showSource && (
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {flight.bestBookingSource}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
