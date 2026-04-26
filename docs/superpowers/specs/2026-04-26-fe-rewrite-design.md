# FE Rewrite — Design Spec

**Date:** 2026-04-26
**Status:** Approved (use case + framework + IA locked)
**Supersedes:** Phase C of `2026-04-25-end-to-end-rebuild-plan.md`
**Audience:** implementation will be executed by Claude

## Goal

Rewrite the flight-tracker frontend as a small, mobile-first SPA optimized for the **"should I buy this?"** decision flow. The current Next.js 16 implementation works but feels heavyweight, looks utility-grade, and the four-tab layout buries the decision behind a navigation tax.

The new FE keeps the same Cloudflare Workers deployment surface and the same Elysia API contract — only the client changes.

The user has stated they will **finalize visual polish themselves** using Claude design, so this spec focuses on **structure, behavior, and information architecture**, not pixel-level styling.

## Non-goals

- Server-side rendering, ISR, server components, or any Next.js-specific feature.
- Native mobile apps (iOS/Android). PWA only.
- Multi-user auth (deferred — `x-api-key` shared secret remains for writes).
- D1 migration (Phase B in the parent plan; FE talks only to Elysia API).
- Visual polish — colors, typography, micro-interactions. User finalizes.

## Locked decisions

| Decision | Choice | Reason |
|---|---|---|
| Use case | Hybrid: verdict cards + drill-down | Optimizes the 5-second glance and the 5-minute review without separate apps. |
| Framework | Vite + React 19 + TanStack Router | SPA, no SSR magic, instant HMR, type-safe routing. |
| Data fetching | TanStack Query (kept from current FE) | Already proven against the Elysia API. |
| UI primitives | shadcn/ui + Tailwind v4 (kept) | Component prompt library reusable as-is. |
| Charts | Recharts (kept) | Already integrated. |
| Deploy | Cloudflare Workers — `Static Assets` binding only | Pure SPA, no Worker code needed for the FE; the API is a separate worker. |
| State | TanStack Query cache + minimal `localStorage` for prefs | No global store needed. |

## Information architecture

Four routes. Mobile-first; on desktop the layout stretches but the IA is identical.

```
/                       Home — verdict cards (one per active trip)
├── /trip/$id           Drill-down — chart + top flights + history + actions
├── /add                Add trip form
└── /settings           API key, refresh, install hint, version
```

**Navigation pattern**

- **Mobile:** bottom nav with 4 icons (Home, Add, Settings, *future tab*). Trip detail enters via tap on a card; returns via back arrow or browser back.
- **Desktop (>= md):** top nav row with the same 4 destinations. Trip detail uses the same route — fills the content column. No second sidebar.

The home screen is the source of truth for *which trips exist*; trip detail is purely a drill-down for the trip already on the home list. There is no "list all flights" or "trends" tab — that data lives inside trip detail. **This is the simplification.**

## Page designs (structural, not visual)

All component-level visual polish (spacing, exact colors, typography scale) is deferred to the user's Claude-design pass.

### Home `/`

Above the fold:

- App title + subtitle (today's date, last-check timestamp).
- One **TripCard** per active trip. Each card shows:
  - Trip name (e.g., "Danang", "Osaka").
  - Big price (cheapest roundtrip combo from `/overview`).
  - Verdict badge (BUY NOW / OK / WAIT) with one-line rationale.
  - Date range (`29 May → 2 Jun`).
  - 14-day price sparkline.
- "Add trip" footer button (mobile only — desktop uses the top nav).

Below the fold (scroll):

- Per-trip secondary cards if more than 2 active trips.
- Empty state when no active trips.

Tap any card → `/trip/$id`.

### Trip detail `/trip/$id`

- Back arrow + breadcrumb-style title.
- Hero block: cheapest combo, verdict badge, date range, last-check time.
- **Price history chart** (Recharts, 30 days, with avg reference line).
- **Top 5 cheapest flights** for the trip (cards on mobile, table on `md+`).
- "View all flights" link → expands the list.
- Actions row: Refresh, Share link, Disable trip.

The legacy "Heatmap" view is deferred — the chart + top flights is enough decision support for the current trip count.

### Add trip `/add`

Single-column form on mobile, two-column on `md+`. Fields:

- Trip name (required)
- From city (default: Bangkok)
- To city (required)
- Return from (optional, defaults to To)
- Go date, Back date (native `<input type="date">`)
- Prefer depart, prefer arrive (HH:mm)
- Added by (your name)
- API key (required, password input)

POST to `/trips` with `x-api-key` header. On success, route back to `/` and invalidate the trips query.

### Settings `/settings`

- API key field (saved to `localStorage` so the form on `/add` can prefill).
- Force-refresh button (clears TanStack Query cache + reloads).
- "Install Travelplan" hint (PWA add-to-home-screen instructions, OS-aware).
- Version + last-deploy timestamp.

## Architecture

### Folder structure (new app)

```
web/                       (replaced in-place)
├── package.json
├── vite.config.ts
├── index.html
├── public/
│   ├── manifest.webmanifest
│   ├── icon-192.png
│   ├── icon-512.png
│   └── sw.js
├── src/
│   ├── main.tsx                    Entry: renders <RouterProvider/>
│   ├── routeTree.gen.ts            (auto-generated by TanStack Router)
│   ├── routes/
│   │   ├── __root.tsx              Layout: nav + outlet
│   │   ├── index.tsx               /  → HomeRoute
│   │   ├── trip.$id.tsx            /trip/$id → TripDetailRoute
│   │   ├── add.tsx                 /add → AddTripRoute
│   │   └── settings.tsx            /settings → SettingsRoute
│   ├── components/
│   │   ├── ui/                     shadcn primitives (kept from current web/)
│   │   ├── trip-card.tsx           home card
│   │   ├── verdict-badge.tsx       pill + rationale (kept)
│   │   ├── sparkline.tsx           inline SVG (kept)
│   │   ├── price-trend-chart.tsx   Recharts (kept)
│   │   ├── flight-row.tsx          single flight card / table row
│   │   ├── flight-list.tsx         list with mobile/desktop variants
│   │   ├── nav-mobile.tsx          bottom nav
│   │   ├── nav-desktop.tsx         top nav
│   │   ├── empty-state.tsx         shared empty/error UI
│   │   └── pwa/
│   │       ├── sw-register.tsx
│   │       └── install-hint.tsx
│   ├── lib/
│   │   ├── api-client.ts           typed fetch wrapper (kept)
│   │   ├── query-client.ts         TanStack Query client + persistor
│   │   ├── verdict.ts              decision logic (computeVerdict, helpers)
│   │   ├── format.ts               formatters: currency, dates, durations
│   │   ├── settings.ts             localStorage wrapper
│   │   └── pwa.ts                  install detection, share helpers
│   └── styles/
│       └── globals.css             Tailwind v4 entry, CSS variables, design tokens
├── tsconfig.json
└── wrangler.jsonc                  Deploy as Static Assets only
```

### Routing

TanStack Router with file-based routes.

- `__root.tsx` provides the layout (nav-desktop on top, nav-mobile fixed at bottom, `<Outlet />` between).
- Trip detail uses path param `$id` — the `id` is the route slug (e.g., `BKK-DAD-2026-05-29`). Resolved against `/overview` data fetched by the parent loader (or via TanStack Query lookup).
- Search params drive secondary state (e.g., `/trip/foo?days=14`).

### Data fetching

Same client as the current FE (`src/lib/api-client.ts`). Same Elysia endpoints. TanStack Query keys mirror endpoint shape:

- `["overview"]` → home cards
- `["trends", route, isoDate, days]` → trip detail chart + home sparkline
- `["flights", route, date, limit]` → flight list
- `["trips"]` → settings + add-trip form
- Mutations: `addTrip` (`POST /trips`)

Persist cache to `localStorage` via `@tanstack/query-sync-storage-persister` so PWA cold starts feel instant.

### PWA

- Manifest, icons, service worker — same approach as current `web/public/sw.js`. Service worker uses cache-first for `/api/*` (the API origin), network-first for HTML, cache-first for static assets.
- `<sw-register>` mounts inside `__root` and registers `/sw.js` only on production hosts (skip localhost).
- iOS: respects `apple-touch-icon` from the manifest. No Web Push (out of scope).

### Deploy

- `wrangler.jsonc` declares the project as a static-assets-only Worker:
  ```jsonc
  {
    "name": "travelplan",
    "main": "src/_worker.ts",     // tiny passthrough that serves assets
    "assets": { "directory": "dist", "binding": "ASSETS" },
    "compatibility_date": "2025-04-01"
  }
  ```
- A 5-line `_worker.ts` returns `env.ASSETS.fetch(request)` so SPA fallback to `index.html` works for all routes.
- Build: `pnpm vite build` (or `npm run build`).
- Deploy: `wrangler deploy` from `web/`.

This is *simpler* than the OpenNext.js setup currently in place — no Next.js runtime on the worker.

### Migration strategy

**In-place replacement of `web/`** rather than parallel `web2/`. Reasons:

- The current FE was just deployed today and is fully understood; no users depend on it staying around for comparison.
- Same Cloudflare Worker name (`travelplan`) → no DNS or routing changes.
- Same secrets (`GOOGLE_CREDENTIALS_JSON`, `GOOGLE_SHEET_ID`, `API_SECRET`) — they're attached to the worker, not the code.
- Easier review: one PR, full diff visible.

The cutover step:

1. Move existing `web/` contents to `web/.attic/` (preserve for one commit, in case we need to read shadcn config).
2. `npm create vite@latest` into a fresh `web/`.
3. Port `tailwind.config.ts`, `components.json`, `tsconfig.json` shadcn paths.
4. Reinstall shadcn primitives (`npx shadcn@latest add card badge button input label select separator table tabs alert`).
5. Port `src/lib/api-client.ts` and the kept components (`verdict-badge`, `sparkline`, `price-trend-chart`, `trip-card`, `flight-row-mobile`).
6. Build the four routes.
7. Deploy. Verify.
8. Delete `web/.attic/` in a follow-up commit.

The Elysia API and the Python scraper are untouched.

## Component inventory

| Component | Source | Notes |
|---|---|---|
| TripCard | rewrite from current `trip-card.tsx` | Tappable; navigates to `/trip/$id`. |
| VerdictBadge | port as-is | Decision logic in `lib/verdict.ts`. |
| Sparkline | port as-is | |
| PriceTrendChart | port as-is | Recharts; theme via CSS variables. |
| FlightRow | new (refines current `flight-row-mobile`) | Same component for mobile & desktop; layout switch via Tailwind responsive classes. |
| FlightList | new | Wraps FlightRow with empty/loading/error states. |
| NavMobile | new (refines `bottom-nav`) | TanStack `<Link>` for active styling. |
| NavDesktop | new | Top nav row, hidden below `md`. |
| EmptyState | new | Single component used for empty/loading/error. |
| InstallHint | new | OS-aware "Add to Home Screen" copy. |

Each component lives in a single file under 150 lines and has a one-paragraph header comment describing inputs and behavior.

## Behavior contracts (for testing later)

- Home renders one card per overview row. Loading shows skeleton, not "Loading…".
- Tapping a card navigates to `/trip/{id}` where `id = ${route}-${isoDate}` (URL-safe).
- Trip detail loads cleanly when accessed directly via URL (i.e., not just via tap from home) — the route's loader fetches what it needs.
- Add trip form prefills `addedBy` and `apiKey` from localStorage if previously saved.
- Settings can clear localStorage and force-refresh.
- Service worker registers only on non-localhost hosts.
- Offline: home still shows the last cached overview + "Last updated X ago" indicator.

## Error handling

- API failures → show inline error in the affected card or page section, not a full-page error. Retry button.
- 401 on POST `/trips` → message: "Wrong API key" with link to Settings.
- Service worker offline + no cache → show offline screen with "Try again" button.
- Empty data (no trips, no flights, no history) → EmptyState with a contextual prompt.

## Testing

- **Vitest** for `lib/` modules (`verdict.ts`, `format.ts`, `settings.ts`).
- **Component tests** with Testing Library for VerdictBadge, TripCard, FlightRow.
- **Manual smoke tests** before each deploy: load home, tap a trip, view chart, refresh, add trip (with valid + invalid key), settings.
- **Lighthouse PWA** post-deploy — target ≥ 90 on mobile.

## Definition of done

- [ ] All four routes render data from the live Elysia API.
- [ ] Mobile (375px wide) layout has no horizontal scroll on any route.
- [ ] Desktop (≥ md) layout doesn't waste full width — content column capped.
- [ ] Add trip flow works end-to-end (form → POST → home updates).
- [ ] PWA installable on iOS Safari and Chrome Android.
- [ ] Service worker caches API + assets; offline reload shows last data.
- [ ] All migrated components pass their unit tests.
- [ ] Old `web/` (Next.js) replaced; old commit available in git history.

## Risks

| Risk | Mitigation |
|---|---|
| TanStack Router learning curve | Use file-based routing only; avoid advanced features (search-param schemas, route layouts) until needed. |
| Migrating Tailwind v4 + shadcn config | Copy existing `components.json` and `globals.css` literally; only re-run shadcn `add` for primitives we use. |
| Cloudflare Workers Static Assets quirks | Tested already with current Next.js — same primitive. The `_worker.ts` passthrough is documented. |
| Visual polish slips beyond user's Claude-design pass | Keep classNames using Tailwind utility classes (no scoped CSS) so user can restyle without refactor. |

## Out of scope (future)

- Heatmap calendar view
- Web Push notifications
- LINE magic-link auth
- D1 migration (Phase B in parent plan)
- Multi-currency support
- Friends-write trips
