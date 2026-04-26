/**
 * FlightRowMobile — single flight as a stacked card (replaces table on small screens).
 */
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FlightRow } from "@/lib/api-client";

export function FlightRowMobile({ flight }: { flight: FlightRow }) {
  const price = flight.bestBookingPrice || flight.priceThb;
  const showSource = flight.bestBookingSource && flight.bestBookingSource !== flight.airline;
  const dur = flight.durationMinutes
    ? `${Math.floor(flight.durationMinutes / 60)}h ${flight.durationMinutes % 60}m`
    : null;

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex justify-between items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="font-medium truncate">{flight.airline}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {flight.departureTime} → {flight.arrivalTime}
              {dur && <span className="ml-2">({dur})</span>}
            </p>
            <div className="flex gap-1.5 mt-2">
              {flight.isDirect ? (
                <Badge variant="secondary" className="text-[10px]">Direct</Badge>
              ) : (
                <Badge variant="outline" className="text-[10px]">
                  {flight.numStops || 1}-stop
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
            <p className="font-bold text-lg">฿{price.toLocaleString()}</p>
            {showSource && (
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {flight.bestBookingSource}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
