/**
 * Google Sheets implementation of FlightDataSource.
 * Uses direct REST + JWT signing via jose (Workers-compatible).
 */

import { SignJWT, importPKCS8 } from "jose";
import type {
  AlertRow,
  FlightDataSource,
  FlightRow,
  OverviewRow,
  PriceHistoryPoint,
  TripConfig,
} from "./adapter";

const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function isoToShortDate(iso: string): string {
  // "2026-05-29" -> "29 May"
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const day = String(parseInt(m[2]!, 10) > 0 ? parseInt(m[3]!, 10) : 0).padStart(2, "0");
  const monthIdx = parseInt(m[2]!, 10) - 1;
  return `${day} ${MONTH_ABBR[monthIdx] || ""}`.trim();
}

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets";
const SCOPE = "https://www.googleapis.com/auth/spreadsheets";

interface ServiceAccountCreds {
  client_email: string;
  private_key: string;
  token_uri?: string;
}

interface CachedToken {
  value: string;
  exp: number;
}

interface Env {
  GOOGLE_SHEET_ID: string;
  GOOGLE_CREDENTIALS_JSON: string;
}

export class SheetsDataSource implements FlightDataSource {
  private cachedToken: CachedToken | null = null;

  constructor(private env: Env) {}

  private async getAccessToken(): Promise<string> {
    const now = Math.floor(Date.now() / 1000);
    if (this.cachedToken && this.cachedToken.exp - 30 > now) {
      return this.cachedToken.value;
    }
    const creds = JSON.parse(this.env.GOOGLE_CREDENTIALS_JSON || "{}") as ServiceAccountCreds;
    if (!creds.client_email || !creds.private_key) {
      throw new Error("GOOGLE_CREDENTIALS_JSON missing client_email or private_key");
    }
    const privateKey = await importPKCS8(creds.private_key, "RS256");
    const assertion = await new SignJWT({ scope: SCOPE })
      .setProtectedHeader({ alg: "RS256", typ: "JWT" })
      .setIssuer(creds.client_email)
      .setAudience(creds.token_uri || TOKEN_URL)
      .setIssuedAt(now)
      .setExpirationTime(now + 3600)
      .sign(privateKey);
    const body = new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion,
    });
    const resp = await fetch(creds.token_uri || TOKEN_URL, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!resp.ok) {
      throw new Error(`Token exchange failed: ${resp.status} ${await resp.text()}`);
    }
    const json = (await resp.json()) as { access_token: string; expires_in: number };
    this.cachedToken = { value: json.access_token, exp: now + json.expires_in };
    return json.access_token;
  }

  private async readRows(tab: string): Promise<Record<string, string>[]> {
    const token = await this.getAccessToken();
    const range = encodeURIComponent(`${tab}!A:Z`);
    const resp = await fetch(`${SHEETS_BASE}/${this.env.GOOGLE_SHEET_ID}/values/${range}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) {
      throw new Error(`Sheets read failed (${tab}): ${resp.status}`);
    }
    const json = (await resp.json()) as { values?: string[][] };
    const rows = json.values || [];
    if (rows.length < 2) return [];
    const headers = rows[0]!;
    return rows.slice(1).map((row) => {
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => {
        obj[h] = row[i] || "";
      });
      return obj;
    });
  }

  private async appendRowRaw(tab: string, values: string[]): Promise<void> {
    const token = await this.getAccessToken();
    const range = encodeURIComponent(`${tab}!A:Z`);
    const resp = await fetch(
      `${SHEETS_BASE}/${this.env.GOOGLE_SHEET_ID}/values/${range}:append?valueInputOption=USER_ENTERED`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({ values: [values] }),
      },
    );
    if (!resp.ok) {
      throw new Error(`Sheets append failed (${tab}): ${resp.status} ${await resp.text()}`);
    }
  }

  async getOverview(): Promise<OverviewRow[]> {
    const rows = await this.readRows("Overview");
    return rows
      .filter((r) => r.Route && r.Route !== "BEST ROUNDTRIP")
      .map((r) => ({
        route: r.Route ?? "",
        date: r.Date ?? "",
        cheapestAirline: r["Cheapest Airline"] ?? "",
        airlinePrice: Number(r["Airline Price"] || 0),
        bestSource: r["Best Source"] ?? "",
        bestPrice: Number(r["Best Price"] || 0),
        lastCheck: r["Last Check"] ?? "",
      }));
  }

  async getFlights(opts: { route?: string; date?: string; limit?: number }): Promise<FlightRow[]> {
    const rows = await this.readRows("All Flights");
    const all: FlightRow[] = rows.map((r) => ({
      route: r.Route ?? "",
      date: r["Search Date"] ?? r.Date ?? "",
      scrapedAt: r["Scraped At"] ?? "",
      airline: r.Airline ?? "",
      flightNumber: r["Flight #"] ?? r["Flight Number"] ?? undefined,
      departureAirport: r["Dep Airport"] ?? r["Departure Airport"] ?? undefined,
      departureTime: r["Dep Time"] ?? r["Departure Time"] ?? undefined,
      arrivalAirport: r["Arr Airport"] ?? r["Arrival Airport"] ?? undefined,
      arrivalTime: r["Arr Time"] ?? r["Arrival Time"] ?? undefined,
      durationMinutes: Number(r["Duration (min)"] || r["Duration"] || 0) || undefined,
      priceThb: Number(r["Price (THB)"] || r.Price || 0),
      bestBookingPrice: r["Best Booking Price"] ? Number(r["Best Booking Price"]) : null,
      bestBookingSource: r["Best Booking Source"] || null,
      numStops: r["Stops"] ? Number(r["Stops"]) : undefined,
      isDirect: r["Direct"] === "TRUE" || r["Direct"] === "true" || r["Direct"] === "1",
      cabinBaggage: r["Cabin Baggage"] || null,
      checkedBaggage: r["Checked Baggage"] || null,
      serviceType: r["Service Type"] || null,
    }));
    let filtered = all;
    if (opts.route) filtered = filtered.filter((f) => f.route === opts.route);
    if (opts.date) filtered = filtered.filter((f) => f.date === opts.date);
    if (opts.limit) filtered = filtered.slice(0, opts.limit);
    return filtered;
  }

  async getTrend(route: string, date: string, days = 30): Promise<PriceHistoryPoint[]> {
    // Price History is wide-format: rows = timestamps, cols = "{route} {dateLabel} (Best)"
    // dateLabel example: "29 May" from ISO "2026-05-29"
    const rows = await this.readRows("Price History");
    const dateLabel = isoToShortDate(date);
    const colBest = `${route} ${dateLabel} (Best)`;
    const colAirline = `${route} ${dateLabel} (Airline)`;
    const points: PriceHistoryPoint[] = [];
    for (const r of rows) {
      const ts = r["Checked At"] ?? "";
      const bestVal = r[colBest];
      const airlineVal = r[colAirline];
      const price = Number(bestVal || airlineVal || 0);
      if (!ts || !price) continue;
      points.push({ scrapedAt: ts, bestPrice: price });
    }
    points.sort((a, b) => a.scrapedAt.localeCompare(b.scrapedAt));
    return points.slice(-days * 24);
  }

  async getTrips(): Promise<TripConfig[]> {
    const rows = await this.readRows("Config");
    return rows
      .filter((r) => r["Trip Name"] && r.From && r.To && r["Go Date"])
      .map((r) => ({
        tripName: r["Trip Name"] ?? "",
        from: r.From ?? "",
        to: r.To ?? "",
        returnFrom: r["Return From"] || undefined,
        goDate: r["Go Date"] ?? "",
        backDate: r["Back Date"] ?? "",
        preferDepart: r["Prefer Depart"] || undefined,
        preferArrive: r["Prefer Arrive"] || undefined,
        active: r.Active ?? "Yes",
        addedBy: r["Added By"] ?? "",
        status: r.Status || undefined,
      }));
  }

  async appendTrip(trip: TripConfig): Promise<void> {
    await this.appendRowRaw("Config", [
      trip.tripName,
      trip.from,
      trip.to,
      trip.returnFrom || trip.to,
      trip.goDate,
      trip.backDate,
      trip.preferDepart || "12:00",
      trip.preferArrive || "18:00",
      trip.active || "Yes",
      trip.addedBy,
      trip.status || "",
    ]);
  }

  async getAlerts(opts: { since?: string; limit?: number }): Promise<AlertRow[]> {
    // The Python scraper writes alerts to a sheet too — this reads from the
    // Dashboard tab's price-alert section. Falls back to empty if not present.
    try {
      const rows = await this.readRows("Price History");
      const items: AlertRow[] = rows
        .filter((r) => r["Is Lowest Ever"] === "TRUE" || r["Is Lowest Ever"] === "true")
        .map((r) => ({
          alertedAt: r["Scraped At"] ?? "",
          route: r.Route ?? "",
          searchDate: r["Search Date"] ?? r.Date ?? "",
          bestPriceThb: r["Best Price"] ? Number(r["Best Price"]) : null,
          prevPriceThb: r["Prev Price"] ? Number(r["Prev Price"]) : null,
          isLowestEver: true,
        }));
      let filtered = items;
      if (opts.since) filtered = filtered.filter((a) => a.alertedAt >= opts.since!);
      if (opts.limit) filtered = filtered.slice(0, opts.limit);
      return filtered;
    } catch {
      return [];
    }
  }
}
