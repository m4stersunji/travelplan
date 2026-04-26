const API_URL =
  import.meta.env.VITE_API_URL ?? "https://travelplan-api.nattawatsun01.workers.dev";

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

export interface AddTripBody {
  tripName: string;
  from: string;
  to: string;
  returnFrom?: string;
  goDate: string;
  backDate: string;
  preferDepart?: string;
  preferArrive?: string;
  addedBy: string;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_URL}${path}`);
  if (!r.ok) throw new Error(`GET ${path} failed: ${r.status}`);
  return r.json();
}

export const api = {
  getOverview: () => get<OverviewRow[]>("/overview"),
  getFlights: (params: { route?: string; date?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.route) qs.set("route", params.route);
    if (params.date) qs.set("date", params.date);
    if (params.limit) qs.set("limit", String(params.limit));
    const q = qs.toString() ? `?${qs}` : "";
    return get<FlightRow[]>(`/flights${q}`);
  },
  getTrend: (route: string, date: string, days = 30) =>
    get<PriceHistoryPoint[]>(
      `/trends/${encodeURIComponent(route)}?date=${encodeURIComponent(date)}&days=${days}`,
    ),
  getTrips: () => get<TripConfig[]>("/trips"),
  addTrip: async (body: AddTripBody, apiKey: string): Promise<{ ok: boolean }> => {
    const r = await fetch(`${API_URL}/trips`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": apiKey },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`POST /trips failed: ${r.status} ${await r.text()}`);
    return r.json();
  },
};
