# End-to-End Product Evolution Plan — Travelplan

**Date:** 2026-04-25
**Status:** Draft for review

## 0. Executive summary

Evolve the existing flight tracker into a three-tier product without rebuilding what works:

- **Tier 1 (unchanged):** Python scraper + GitHub Actions cron + LINE notifier + SQLite (committed). Source of truth for raw data; continues to drive the LINE flow.
- **Tier 2 (new):** A thin Elysia (Bun) REST API on Cloudflare Workers, fronting either Google Sheets (Phase A) or Cloudflare D1 (Phase B). Replaces the Next.js route handlers that currently call `googleapis` directly.
- **Tier 3 (evolved):** The current Next.js 16 dashboard becomes a mobile-first PWA — same URL, same Worker deploy, plus manifest + service worker + responsive layout. No native app.

Migration is incremental and reversible: each phase has a feature flag, a rollback, and never breaks the LINE pipeline or GitHub Actions cron.

---

## 1. Architecture decisions

### 1.1 Backend framework: Elysia (Bun, TS)

| Option | Verdict | Reason |
|---|---|---|
| **Elysia** | chosen | Native TS end-to-end types via `treaty`/Eden client, runs on Bun and on Cloudflare Workers, small bundle, modern DX. |
| Hono | strong runner-up | Smaller, equally Workers-friendly; fallback if Elysia + Workers misbehaves. |
| Fastify | rejected | Designed for Node, heavyweight on Workers. |
| Express | rejected | Doesn't run on Workers without heavy shimming. |

**Tradeoff:** Elysia's Workers support is newer than Hono's. Mitigation: keep route handlers framework-thin (pure functions for query logic) so a swap to Hono is mechanical.

### 1.2 Data store: keep Google Sheets (A) → Cloudflare D1 (B)

| Option | Free tier? | Verdict |
|---|---|---|
| **Google Sheets (current)** | yes | Keep as user-facing config + analysis surface during transition. |
| **Cloudflare D1** | yes (5 GB, 5M reads/day) | Chosen target. Edge SQLite, same dialect as `data/flights.db`. |
| Supabase | yes | Rejected — extra vendor, network hop. |
| Turso | yes | Solid alternative; rejected for single-vendor stack. |

**D1 ingest path:** Python scraper continues writing `data/flights.db`. A new `scripts/sync_to_d1.py` runs after the scrape, upserting only the latest run's rows.

**Rollback:** if D1 sync fails for N runs, FE falls back to Sheets-backed endpoint via env flag (`DATA_SOURCE=sheets|d1`).

### 1.3 PWA framework: keep Next.js 16

- Already deployed on `@opennextjs/cloudflare`. Swap to Vite/Remix/Solid costs 1-2 weeks for negligible UX gain.
- This repo's Next.js 16 has its own conventions (`web/AGENTS.md`); always read `node_modules/next/dist/docs/` before changing routing/data-fetching patterns.
- PWA support comes from a hand-rolled manifest + service worker. We avoid `next-pwa` because it lags Next.js majors.

**Tradeoff:** iOS Safari PWA limits (no Web Push pre-iOS 16.4 home-screen, no background sync). Plan accommodates by keeping LINE as primary push.

### 1.4 State + data fetching: TanStack Query

Replaces `useEffect + fetch` in `web/src/components/dashboard.tsx`, `price-trends.tsx`, `add-trip.tsx`. Adds offline cache hydration via `persistQueryClient`, background refetch, request deduping. No Redux/Zustand needed.

### 1.5 Charts: Recharts (primary) + lightweight sparkline

- **Recharts** for trend chart and histogram — stable React 19 partner.
- **Inline SVG sparkline** (~30 lines) inside `TripCard` to avoid pulling Recharts into every list item.
- Visx rejected (too low-level), Chart.js rejected (canvas, harder to theme), Tremor rejected (heavy, fights shadcn).

### 1.6 Auth: defer, then magic-link via LINE

- **Now:** keep `x-api-key` shared-secret on write endpoints. Read endpoints stay public.
- **Later (optional Phase D):** magic-link via LINE — Worker pushes a short-lived signed token to the user's chat.
- Clerk / Cloudflare Access rejected: paid tiers, overkill.

### 1.7 Hosting topology

```
GitHub Actions (every 2h)
        └── Python scraper → SQLite → committed to repo
                                   └── (Phase B) HTTP push → Cloudflare D1
                                   └── (Phase A) Google Sheets push (existing)

Cloudflare Workers
   ├── travelplan        (existing) — Next.js 16 PWA, FE
   └── travelplan-api    (NEW)      — Elysia REST: /flights /trends /trips /alerts
        └── reads Sheets (Phase A) or D1 (Phase B)

User device
   └── PWA installed from https://travelplan.nattawatsun01.workers.dev
        └── Service worker caches /api/flights, /api/trends/*
```

---

## 2. Migration phases

### Phase A — stand up Elysia API alongside FE
**Goal:** Existing FE keeps working; new `api/` worker serves the same data via clean endpoints.
**Effort:** ~3 days
**What breaks:** nothing.
**Rollback:** delete the new Worker.
**Success criteria:**
- `GET /flights?route=BKK-DAD&date=2026-05-29` returns typed JSON.
- `dashboard.tsx` reads from new endpoint via TanStack Query.
- LINE + GitHub Actions unchanged.

### Phase B — migrate data layer to D1
**Goal:** D1 becomes primary read source. Sheets stays as analyst dashboard + Config input.
**Effort:** ~3-4 days
**What breaks:** during dual-write, transient inconsistency possible.
**Rollback:** flip `DATA_SOURCE=sheets`.
**Success criteria:**
- D1 and SQLite row counts within ±5 after each scrape.
- All FE charts render from D1.
- LINE flow untouched.

### Phase C — PWA refactor (mobile-first)
**Goal:** Same URL, but installable + mobile-first.
**Effort:** ~2-3 days
**Rollback:** revert manifest + SW registration.
**Success criteria:**
- Lighthouse PWA score ≥ 90 mobile.
- Add to Home Screen works on iOS Safari 17+ / Chrome Android.
- Cached dashboard loads <1s on repeat visit while offline.

### Phase D — mobile-only delights (optional)
Web Push (where iOS allows), offline trip-add queue, share-sheet target, View Transitions.
**Effort:** ~3-5 days, splittable into 1-day tickets.

---

## 3. File structure

```
/home/m4stersun/travelplan/
├── api/                                      [NEW] Elysia + Bun + Cloudflare Worker
│   ├── src/
│   │   ├── index.ts
│   │   ├── routes/
│   │   │   ├── flights.ts
│   │   │   ├── trends.ts
│   │   │   ├── trips.ts
│   │   │   ├── alerts.ts
│   │   │   └── health.ts
│   │   ├── data/
│   │   │   ├── adapter.ts            # FlightDataSource interface
│   │   │   ├── sheets.ts             # Phase A
│   │   │   ├── d1.ts                 # Phase B
│   │   │   └── index.ts              # picks adapter from env
│   │   ├── schemas.ts                # zod/typebox response shapes
│   │   └── lib/auth.ts               # x-api-key check
│   ├── migrations/0001_init.sql      # mirrors src/database.py DDL
│   ├── package.json
│   ├── wrangler.jsonc                # name: travelplan-api, d1 binding
│   └── README.md
│
├── scripts/                                  [NEW]
│   ├── sync_to_d1.py
│   ├── seed_d1_from_sqlite.py
│   └── verify_parity.py
│
├── web/                                      [exists]
│   ├── public/
│   │   ├── manifest.webmanifest      [NEW]
│   │   ├── icon-192.png              [NEW]
│   │   ├── icon-512.png              [NEW]
│   │   └── sw.js                     [NEW]
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx            [edit]
│   │   │   ├── page.tsx              [edit]
│   │   │   └── (mobile)/             [NEW]
│   │   │       ├── trips/[id]/page.tsx
│   │   │       └── settings/page.tsx
│   │   ├── components/
│   │   │   ├── trip-card.tsx         [NEW]
│   │   │   ├── price-trend-chart.tsx [NEW]
│   │   │   ├── price-heatmap.tsx     [NEW]
│   │   │   ├── verdict-badge.tsx     [NEW]
│   │   │   ├── bottom-nav.tsx        [NEW]
│   │   │   └── sparkline.tsx         [NEW]
│   │   ├── lib/
│   │   │   ├── api-client.ts         [NEW] typed Eden client
│   │   │   ├── query-client.ts       [NEW] TanStack Query
│   │   │   └── pwa.ts                [NEW]
│   └── package.json                  [edit] add tanstack/query, recharts
│
├── docs/
│   ├── superpowers/specs/
│   │   └── 2026-04-25-end-to-end-rebuild-plan.md   [this doc]
│   └── design/prompt-library.md      [NEW]
│
├── .github/workflows/
│   └── flight-tracker.yml            [edit] add D1 sync (Phase B)
│
└── src/                              [Python — unchanged]
```

---

## 4. Action list (ordered, checkable)

### Phase A — Elysia API
- [ ] A1. `bun init` in `api/`, add Elysia + cors deps.
- [ ] A2. `api/wrangler.jsonc` (name `travelplan-api`, `nodejs_compat`).
- [ ] A3. `FlightDataSource` interface in `api/src/data/adapter.ts`.
- [ ] A4. `api/src/data/sheets.ts` — port reads from `web/src/lib/sheets.ts`.
- [ ] A5. Routes: `GET /flights`, `/trends/:route`, `/trips`, `POST /trips`, `/alerts`, `/health`.
- [ ] A6. Zod/typebox schemas in `api/src/schemas.ts`.
- [ ] A7. `cd api && bunx wrangler deploy`.
- [ ] A8. In `web/`, install `@tanstack/react-query`; create typed Eden client `web/src/lib/api-client.ts`.
- [ ] A9. Migrate `dashboard.tsx` first behind `NEXT_PUBLIC_USE_NEW_API=true`.
- [ ] A10. Migrate `price-trends.tsx`, `flights-table.tsx`, `add-trip.tsx`.
- [ ] A11. Soak test: 1 day with LINE + cron unchanged.
- [ ] A12. Delete `web/src/lib/sheets.ts` + legacy `web/src/app/api/{sheets,trips}/`.

### Phase B — D1 migration
- [ ] B1. `bunx wrangler d1 create travelplan`.
- [ ] B2. `api/migrations/0001_init.sql` mirroring `src/database.py` DDL.
- [ ] B3. `bunx wrangler d1 migrations apply travelplan`.
- [ ] B4. D1 binding in `api/wrangler.jsonc`.
- [ ] B5. `api/src/data/d1.ts` (same `FlightDataSource` interface).
- [ ] B6. `scripts/seed_d1_from_sqlite.py` — one-time backfill.
- [ ] B7. `scripts/sync_to_d1.py` — append-only after each scrape.
- [ ] B8. Add D1 sync step to `.github/workflows/flight-tracker.yml` (soft-fail).
- [ ] B9. Run `scripts/verify_parity.py` daily for 1 week.
- [ ] B10. Flip `DATA_SOURCE=d1` on Worker.
- [ ] B11. Document rollback.

### Phase C — PWA mobile-first
- [ ] C1. `web/public/manifest.webmanifest` (standalone, theme color, icons).
- [ ] C2. Generate icons (192, 512, maskable).
- [ ] C3. `web/public/sw.js` — cache-first for `/api/*`, network-first for HTML.
- [ ] C4. Register SW in `web/src/lib/pwa.ts`.
- [ ] C5. Update `layout.tsx` metadata (viewport, themeColor, appleWebApp). Read `node_modules/next/dist/docs/` first.
- [ ] C6. `bottom-nav.tsx` — fixed bottom on mobile, hidden on `md+`.
- [ ] C7. Refactor `page.tsx` tabs: stacked on small, horizontal on `md+`.
- [ ] C8. `trip-card.tsx` — full-width, big price, sparkline, verdict.
- [ ] C9. `price-trend-chart.tsx` (Recharts).
- [ ] C10. `price-heatmap.tsx` — calendar grid.
- [ ] C11. `verdict-badge.tsx` (BUY NOW / OK / WAIT).
- [ ] C12. Per-route detail `web/src/app/(mobile)/trips/[id]/page.tsx`.
- [ ] C13. Persist TanStack Query cache to IndexedDB.
- [ ] C14. Lighthouse PWA score, real-device test (iOS, Android).

### Phase D — delights (optional, parallelizable)
- [ ] D1. Web Push (Android/desktop only), Worker stores subscription in D1.
- [ ] D2. Offline trip add via SW background sync.
- [ ] D3. Share-sheet target.
- [ ] D4. View Transitions API.
- [ ] D5. (Optional) LINE magic-link login.

---

## 5. Design prompt library (10 reusable prompts)

Saved to `docs/design/prompt-library.md`. Each prompt yields a single shadcn-compatible component.

1. **TripCard** — "Generate `TripCard` for `web/src/components/trip-card.tsx`. Props: `tripName`, `cheapestCombo` (THB), `verdict` ('BUY_NOW'|'WAIT'|'OK'), `goDate`, `backDate`, `sparklineData` (number[]). Mobile-first, full width, no horizontal scroll, big price, verdict pill, inline SVG sparkline. Use existing `Card`, `Badge`, `Separator`. Tailwind v4."
2. **PriceTrendChart** — "Generate `PriceTrendChart` using Recharts. Line chart of `bestPrice` over `scrapedAt` for last 30 days. Highlight points where price < 0.85 × historical avg with a green dot. Tooltip: date, THB-formatted price, source airline. Responsive container, 240px on mobile."
3. **PriceHeatmap** — "Generate `PriceHeatmap` calendar grid (rows = outbound dates, cols = return dates) of best round-trip prices. Color scale: green cheapest 25%, yellow middle, red top 25%. Cells clickable; emit `onSelect(go, back)`. Pure SVG/CSS grid."
4. **VerdictBadge** — "Generate `VerdictBadge`. Inputs: `currentBest`, `historicalAvg`, `historicalMin`. Logic: BUY NOW if currentBest ≤ 1.05 × historicalMin; WAIT if ≥ 1.15 × avg; else OK. Use shadcn `Badge` with variants. One-line rationale below."
5. **FlightTableMobile** — "Generate `FlightTableMobile`. Props: `flights[]`. On `md+`, render `Table`. On small screens, render stacked card list. Show airline, dep→arr, duration, direct badge, price prominently, expand-for-details disclosure."
6. **BottomNav** — "Generate `BottomNav`. Fixed `bottom-0 inset-x-0`, only visible below `md`. Four items (Dashboard, Trends, Trips, Settings) with `lucide-react` icons. Active state from current route. Safe-area-aware padding."
7. **InstallPwaPrompt** — "Generate `InstallPwaPrompt`. Listens for `beforeinstallprompt`, shows dismissible `Card` after 3+ visits (track in localStorage). On iOS Safari, alternate instructions ('Tap Share, then Add to Home Screen')."
8. **OfflineBanner** — "Generate `OfflineBanner`. Subscribes to `navigator.onLine` + `online`/`offline` events. Slim banner with `WifiOff` icon when offline; auto-dismisses on reconnect. Uses shadcn `Alert`."
9. **AddTripForm** — "Refactor `AddTripForm`. Single-column on mobile, two on `md+`. Use existing `Input`, `Label`, `Select`, `Button`. Native `<input type=date>` with min=today. POST via TanStack Query mutation; optimistic success toast."
10. **PriceDistributionHistogram** — "Generate `PriceDistributionHistogram` using Recharts BarChart. X axis: price buckets (THB), Y axis: count of scrape runs. Show median as `ReferenceLine`. Tooltip lists airlines in bucket."

---

## 6. API design (Elysia routes — sketch)

```ts
// api/src/index.ts
import { Elysia, t } from 'elysia'
import { flightsRoute } from './routes/flights'
// ...
export default new Elysia()
  .use(flightsRoute)
  .use(trendsRoute)
  .use(tripsRoute)
  .use(alertsRoute)
  .get('/health', () => ({ ok: true, ts: Date.now() }))
  .compile()
```

| Method | Path | Purpose | Backed by |
|---|---|---|---|
| GET | `/flights?route=&date=&limit=` | Flight list for one route+date | Sheets/D1 |
| GET | `/trends/:route?date=&days=30` | Price-over-time series | D1 / Sheets `Price History` |
| GET | `/trips` | Active trips from `Config` | Sheets `Config` (always) |
| POST | `/trips` | Append trip (`x-api-key`) | Sheets `Config` |
| GET | `/alerts?since=` | Recent `price_alerts` | D1/Sheets |
| GET | `/health` | Liveness | n/a |

---

## 7. Open questions

- [ ] **Data store target**: confirm Cloudflare D1 over Turso?
- [ ] **Trips to migrate first**: all four at once, or just Danang first?
- [ ] **Web Push in Phase D**: yes/no?
- [ ] **Custom domain**: keep `*.workers.dev` or wire `travelplan.<your-domain>`?
- [ ] **API auth scope**: should reads also require `x-api-key`?
- [ ] **Currency**: hardcode THB or multi-currency in Phase D?
- [ ] **Friends-write**: PWA edit access for non-owners?
- [ ] **Charts library lock-in**: Recharts confirmed?
- [ ] **PWA app name + icon**: brand name "Travelplan"? Icon style?
- [ ] **Retention**: keep all rows forever in D1, or roll up >90 days?

---

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Elysia + Workers integration immature | Thin route handlers; Hono fallback ready. |
| Sheets quota during dual-write | Worker only reads; existing Python writes unchanged. |
| D1 read limits if FE hammered | Edge cache + TanStack persist + `s-maxage=300`. |
| Next.js 16 conventions diverge from training | Always read `node_modules/next/dist/docs/` before changes. |
| iOS Safari PWA gaps | LINE remains primary push; PWA supplementary. |
| GH Actions secrets sprawl (D1_TOKEN added) | Document in `.env.example`; soft-fail D1 sync. |
| Service worker stale cache | Version with build hash; `skipWaiting` + `clients.claim`. |
| Friends mis-edit Config | Extend status writeback validation in `src/sheets_config.py`. |

---

## 9. Definition of done (per phase)

- **A done:** all four FE components fetch from new API; legacy `/api/sheets` deleted; one full LINE+scraper cycle green.
- **B done:** D1 row counts match SQLite for 7 consecutive days; `DATA_SOURCE=d1` in production; rollback rehearsed.
- **C done:** Lighthouse mobile PWA ≥ 90; installable on iOS+Android; all primary screens responsive at 360px wide.
- **D done:** at least one delight shipped behind a flag with toggle in Settings.
