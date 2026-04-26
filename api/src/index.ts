/**
 * travelplan-api — Elysia REST API on Cloudflare Workers.
 * Fronts Google Sheets (Phase A) or D1 (Phase B) via FlightDataSource.
 */

import { Elysia, t } from "elysia";
import { createDataSource } from "./data";
import { isAuthorized } from "./lib/auth";

interface Env {
  DATA_SOURCE?: string;
  GOOGLE_SHEET_ID: string;
  GOOGLE_CREDENTIALS_JSON: string;
  API_SECRET?: string;
}

const corsHeaders = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, x-api-key",
  "access-control-max-age": "86400",
};

const cacheRead = "s-maxage=300, stale-while-revalidate=900";

function buildApp(env: Env) {
  const ds = createDataSource(env);

  // aot:false disables runtime code-gen (new Function) which Cloudflare
  // Workers blocks via "Code generation from strings disallowed".
  return new Elysia({ aot: false })
    .onAfterHandle(({ set }) => {
      Object.entries(corsHeaders).forEach(([k, v]) => set.headers[k] = v);
    })
    .options("/*", () => new Response(null, { headers: corsHeaders }))
    .get("/", () => ({
      name: "travelplan-api",
      docs: "/health, /flights, /trends/:route, /trips, /alerts",
    }))
    .get("/health", () => ({ ok: true, ts: Date.now() }))
    .get(
      "/overview",
      async ({ set }) => {
        set.headers["cache-control"] = cacheRead;
        return ds.getOverview();
      },
    )
    .get(
      "/flights",
      async ({ query, set }) => {
        set.headers["cache-control"] = cacheRead;
        return ds.getFlights({
          route: query.route,
          date: query.date,
          limit: query.limit ? Number(query.limit) : undefined,
        });
      },
      {
        query: t.Object({
          route: t.Optional(t.String()),
          date: t.Optional(t.String()),
          limit: t.Optional(t.String()),
        }),
      },
    )
    .get(
      "/trends/:route",
      async ({ params, query, set }) => {
        set.headers["cache-control"] = cacheRead;
        if (!query.date) {
          set.status = 400;
          return { error: "date query param required" };
        }
        return ds.getTrend(params.route, query.date, query.days ? Number(query.days) : 30);
      },
      {
        params: t.Object({ route: t.String() }),
        query: t.Object({
          date: t.Optional(t.String()),
          days: t.Optional(t.String()),
        }),
      },
    )
    .get("/trips", async ({ set }) => {
      set.headers["cache-control"] = cacheRead;
      return ds.getTrips();
    })
    .post(
      "/trips",
      async ({ body, request, set }) => {
        if (!isAuthorized(request.headers, env.API_SECRET)) {
          set.status = 401;
          return { error: "Unauthorized" };
        }
        await ds.appendTrip({
          tripName: body.tripName,
          from: body.from,
          to: body.to,
          returnFrom: body.returnFrom,
          goDate: body.goDate,
          backDate: body.backDate,
          preferDepart: body.preferDepart,
          preferArrive: body.preferArrive,
          active: "Yes",
          addedBy: body.addedBy,
        });
        return { ok: true };
      },
      {
        body: t.Object({
          tripName: t.String(),
          from: t.String(),
          to: t.String(),
          returnFrom: t.Optional(t.String()),
          goDate: t.String(),
          backDate: t.String(),
          preferDepart: t.Optional(t.String()),
          preferArrive: t.Optional(t.String()),
          addedBy: t.String(),
        }),
      },
    )
    .get(
      "/alerts",
      async ({ query, set }) => {
        set.headers["cache-control"] = cacheRead;
        return ds.getAlerts({
          since: query.since,
          limit: query.limit ? Number(query.limit) : 50,
        });
      },
      {
        query: t.Object({
          since: t.Optional(t.String()),
          limit: t.Optional(t.String()),
        }),
      },
    );
}

// Cloudflare Worker fetch handler
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const app = buildApp(env);
    return app.handle(request);
  },
};
