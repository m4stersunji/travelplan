/**
 * FlightDataSource — single interface that both Sheets (Phase A) and D1 (Phase B)
 * implementations conform to. The Elysia handlers depend only on this interface.
 *
 * When migrating to D1, build a new implementation in `./d1.ts`, switch the
 * factory in `./index.ts` based on env DATA_SOURCE, and the FE/API contract
 * stays unchanged.
 */

export interface OverviewRow {
  route: string;
  date: string;
  cheapestAirline: string;
  airlinePrice: number;
  bestSource: string;
  bestPrice: number;
  lastCheck: string;
}

export interface FlightRow {
  route: string;
  date: string;
  scrapedAt: string;
  airline: string;
  flightNumber?: string;
  departureAirport?: string;
  departureTime?: string;
  arrivalAirport?: string;
  arrivalTime?: string;
  durationMinutes?: number;
  priceThb: number;
  bestBookingPrice?: number | null;
  bestBookingSource?: string | null;
  numStops?: number;
  isDirect?: boolean;
  cabinBaggage?: string | null;
  checkedBaggage?: string | null;
  serviceType?: string | null;
}

export interface PriceHistoryPoint {
  scrapedAt: string;
  bestPrice: number;
  airline?: string;
}

export interface TripConfig {
  tripName: string;
  from: string;
  to: string;
  returnFrom?: string;
  goDate: string;
  backDate: string;
  preferDepart?: string;
  preferArrive?: string;
  active: string;
  addedBy: string;
  status?: string;
}

export interface AlertRow {
  alertedAt: string;
  route: string;
  searchDate: string;
  bestPriceThb: number | null;
  prevPriceThb: number | null;
  isLowestEver: boolean;
}

export interface FlightDataSource {
  getOverview(): Promise<OverviewRow[]>;
  getFlights(opts: { route?: string; date?: string; limit?: number }): Promise<FlightRow[]>;
  getTrend(route: string, date: string, days?: number): Promise<PriceHistoryPoint[]>;
  getTrips(): Promise<TripConfig[]>;
  appendTrip(trip: TripConfig): Promise<void>;
  getAlerts(opts: { since?: string; limit?: number }): Promise<AlertRow[]>;
}
