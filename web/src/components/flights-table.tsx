"use client";
/**
 * FlightsTable — desktop table + mobile card list. Filterable by route.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { FlightRowMobile } from "@/components/flight-row-mobile";

const CITY_TO_CODE: Record<string, string> = {
  Bangkok: "BKK",
  Danang: "DAD",
  Osaka: "KIX",
  Tokyo: "TYO",
};

function cityToCode(name: string): string {
  return CITY_TO_CODE[name] || name.slice(0, 3).toUpperCase();
}

export default function FlightsTable() {
  const [route, setRoute] = useState<string>("all");

  const tripsQ = useQuery({ queryKey: ["trips"], queryFn: api.getTrips });
  const flightsQ = useQuery({
    queryKey: ["flights", route],
    queryFn: () =>
      api.getFlights({ route: route === "all" ? undefined : route, limit: 50 }),
  });

  const routes = Array.from(
    new Set((tripsQ.data || []).map((t) => `${cityToCode(t.from)}-${cityToCode(t.to)}`)),
  );

  if (flightsQ.isLoading) {
    return <div className="h-64 rounded-xl border bg-muted/30 animate-pulse" />;
  }
  if (flightsQ.isError) {
    return (
      <p className="text-center text-sm text-destructive py-12">
        Failed to load flights.
      </p>
    );
  }
  const flights = flightsQ.data || [];

  return (
    <div className="space-y-4">
      <Select value={route} onValueChange={(v) => setRoute(v ?? "all")}>
        <SelectTrigger className="max-w-xs">
          <SelectValue placeholder="All routes" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All routes</SelectItem>
          {routes.map((r) => (
            <SelectItem key={r} value={r}>{r}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      {flights.length === 0 ? (
        <p className="text-sm text-muted-foreground py-12 text-center">
          No flights match this filter.
        </p>
      ) : (
        <>
          <div className="md:hidden space-y-2">
            {flights.map((f, i) => (
              <FlightRowMobile key={i} flight={f} />
            ))}
          </div>
          <div className="hidden md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Route</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Airline</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {flights.map((f, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{f.route}</TableCell>
                    <TableCell>{f.date}</TableCell>
                    <TableCell>{f.airline}</TableCell>
                    <TableCell className="text-xs">
                      {f.departureTime} → {f.arrivalTime}
                    </TableCell>
                    <TableCell>
                      {f.isDirect ? (
                        <Badge variant="secondary">Direct</Badge>
                      ) : (
                        <Badge variant="outline">{f.numStops || 1}-stop</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      ฿{(f.bestBookingPrice || f.priceThb).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
