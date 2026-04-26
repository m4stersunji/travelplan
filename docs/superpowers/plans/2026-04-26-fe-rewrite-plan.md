# FE Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `web/` (Next.js 16 PWA) with a Vite + React 19 + TanStack Router SPA that ships the IA from `docs/superpowers/specs/2026-04-26-fe-rewrite-design.md`.

**Architecture:** SPA served as Cloudflare Worker static assets. TanStack Router for file-based routing. TanStack Query for data fetching against the existing Elysia API at `https://travelplan-api.nattawatsun01.workers.dev`. shadcn/ui + Tailwind v4 for primitives. Recharts for trend chart.

**Tech Stack:** Vite 6, React 19, TanStack Router, TanStack Query, shadcn/ui, Tailwind v4, Recharts, jose (already in api/), Cloudflare Workers static assets.

---

## Task 1: Stash old web/ and scaffold Vite project

**Files:**
- Move: `web/` → `web/.attic/`
- Create: `web/` (fresh Vite scaffold)

- [ ] **Step 1: Move existing web/ aside**

```bash
cd /home/m4stersun/travelplan
mkdir -p web/.attic
git mv web/* web/.attic/ 2>/dev/null || true
mv web/.gitignore web/.attic/.gitignore 2>/dev/null || true
mv web/.env.local web/.attic/.env.local 2>/dev/null || true
git status --short | head -20
```

Expected: large list of `R  web/<file> -> web/.attic/<file>` rename entries.

- [ ] **Step 2: Scaffold fresh Vite + React + TS**

```bash
cd /home/m4stersun/travelplan
npm create vite@latest web -- --template react-ts
cd web
ls
```

Expected: `index.html  package.json  src/  tsconfig.json  vite.config.ts  public/` etc.

- [ ] **Step 3: Install runtime deps**

```bash
cd /home/m4stersun/travelplan/web
npm install @tanstack/react-router @tanstack/react-query @tanstack/query-sync-storage-persister @tanstack/react-query-persist-client recharts lucide-react clsx tailwind-merge class-variance-authority
```

Expected: `added N packages`.

- [ ] **Step 4: Install dev deps**

```bash
cd /home/m4stersun/travelplan/web
npm install -D tailwindcss @tailwindcss/vite @tanstack/router-plugin wrangler vitest @testing-library/react @testing-library/jest-dom jsdom @types/node
```

Expected: dev deps installed.

- [ ] **Step 5: Verify dev server boots**

```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 3
curl -sS http://localhost:5173/ | head -2
kill %1 2>/dev/null
```

Expected: `<!doctype html>...<title>Vite + React + TS</title>`.

- [ ] **Step 6: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/.attic web/package.json web/package-lock.json web/tsconfig.json web/tsconfig.node.json web/tsconfig.app.json web/vite.config.ts web/index.html web/src web/public web/.gitignore web/eslint.config.js
git commit -m "scaffold(web): Vite + React + TS, stash old Next.js to .attic"
```

---

## Task 2: Tailwind v4 + shadcn setup

**Files:**
- Modify: `web/vite.config.ts`
- Create: `web/src/styles/globals.css`
- Modify: `web/src/main.tsx`
- Create: `web/components.json`
- Create: `web/tsconfig.json` (path aliases)

- [ ] **Step 1: Configure Tailwind v4 via Vite plugin**

Replace `web/vite.config.ts` with:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import path from "node:path";

export default defineConfig({
  plugins: [TanStackRouterVite(), react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: { port: 5173 },
  build: { outDir: "dist", target: "es2022" },
});
```

- [ ] **Step 2: Create global stylesheet**

Create `web/src/styles/globals.css`:

```css
@import "tailwindcss";

@theme {
  --color-bg: 0 0% 100%;
  --color-fg: 0 0% 4%;
  --color-muted: 0 0% 96%;
  --color-muted-fg: 0 0% 45%;
  --color-border: 0 0% 90%;
  --color-card: 0 0% 100%;
  --color-card-fg: 0 0% 4%;
  --color-primary: 142 71% 45%;
  --color-primary-fg: 0 0% 100%;
  --color-destructive: 0 72% 51%;
  --color-destructive-fg: 0 0% 100%;
  --color-warning: 38 92% 50%;
  --color-warning-fg: 0 0% 100%;
}

@media (prefers-color-scheme: dark) {
  @theme {
    --color-bg: 0 0% 4%;
    --color-fg: 0 0% 96%;
    --color-muted: 0 0% 12%;
    --color-muted-fg: 0 0% 65%;
    --color-border: 0 0% 16%;
    --color-card: 0 0% 8%;
    --color-card-fg: 0 0% 96%;
  }
}

html, body, #root { height: 100%; }
body {
  background: hsl(var(--color-bg));
  color: hsl(var(--color-fg));
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
```

- [ ] **Step 3: Update tsconfig path alias**

Add to `web/tsconfig.json` `"compilerOptions"`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

Also add same `paths` to `web/tsconfig.app.json`.

- [ ] **Step 4: Create shadcn components.json**

Create `web/components.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/styles/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 5: Create lib/utils**

Create `web/src/lib/utils.ts`:

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 6: Add shadcn primitives**

```bash
cd /home/m4stersun/travelplan/web
npx shadcn@latest add card badge button input label select separator alert
```

Expected: 8 files created in `web/src/components/ui/`.

- [ ] **Step 7: Wire styles into main.tsx**

Replace `web/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/globals.css";
import "./App.tsx";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 8: Smoke-test the styling**

Replace `web/src/App.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function App() {
  return (
    <div className="min-h-screen p-6">
      <Card className="max-w-sm mx-auto">
        <CardHeader>
          <CardTitle>Travelplan</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge>BUY NOW</Badge>
          <p className="mt-2 text-sm text-muted-foreground">Tailwind + shadcn working.</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

Run:
```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 3
curl -sS http://localhost:5173/ | grep -q "Travelplan" && echo OK
kill %1
```

Expected: `OK`.

- [ ] **Step 9: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/
git commit -m "feat(web): Tailwind v4 + shadcn primitives + path aliases"
```

---

## Task 3: Library modules — utils, format, verdict, settings, api-client, query-client

**Files:**
- Create: `web/src/lib/format.ts`
- Create: `web/src/lib/verdict.ts`
- Create: `web/src/lib/settings.ts`
- Create: `web/src/lib/api-client.ts` (port from `web/.attic/src/lib/api-client.ts`)
- Create: `web/src/lib/query-client.ts`
- Create: `web/src/test/setup.ts`
- Create: `web/src/lib/__tests__/verdict.test.ts`
- Create: `web/src/lib/__tests__/format.test.ts`
- Modify: `web/vitest.config.ts` (new)

- [ ] **Step 1: Create vitest config**

Create `web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

Add to `web/package.json` scripts:

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Step 2: Create test setup**

Create `web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Write format.test.ts (failing)**

Create `web/src/lib/__tests__/format.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { formatThb, formatShortDate, formatDuration, isoToShortDate, shortDateToIso } from "../format";

describe("format", () => {
  it("formats THB with comma separator", () => {
    expect(formatThb(7109)).toBe("฿7,109");
    expect(formatThb(0)).toBe("฿0");
  });
  it("formats short date from ISO", () => {
    expect(isoToShortDate("2026-05-29")).toBe("29 May");
    expect(isoToShortDate("2026-10-17")).toBe("17 Oct");
  });
  it("parses short date back to ISO", () => {
    expect(shortDateToIso("29 May", 2026)).toBe("2026-05-29");
    expect(shortDateToIso("17 Oct", 2026)).toBe("2026-10-17");
  });
  it("formats duration minutes to h/m", () => {
    expect(formatDuration(95)).toBe("1h 35m");
    expect(formatDuration(60)).toBe("1h 0m");
    expect(formatDuration(0)).toBe("0h 0m");
  });
  it("formats short date label", () => {
    expect(formatShortDate("2026-05-29")).toBe("29 May");
  });
});
```

- [ ] **Step 4: Run test (should fail)**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run src/lib/__tests__/format.test.ts 2>&1 | tail -10
```

Expected: failure — module `../format` not found.

- [ ] **Step 5: Implement format.ts**

Create `web/src/lib/format.ts`:

```ts
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTH_TO_NUM: Record<string, string> = {
  Jan:"01", Feb:"02", Mar:"03", Apr:"04", May:"05", Jun:"06",
  Jul:"07", Aug:"08", Sep:"09", Oct:"10", Nov:"11", Dec:"12",
};

export function formatThb(value: number): string {
  return `฿${value.toLocaleString("en-US")}`;
}

export function isoToShortDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const day = parseInt(m[3], 10).toString();
  const month = MONTHS[parseInt(m[2], 10) - 1] ?? "";
  return `${day.padStart(2, "0")} ${month}`;
}

export function shortDateToIso(label: string, year: number = new Date().getFullYear()): string {
  const [day, mon] = label.split(" ");
  if (!day || !mon) return label;
  const month = MONTH_TO_NUM[mon] ?? "01";
  return `${year}-${month}-${day.padStart(2, "0")}`;
}

export function formatShortDate(iso: string): string {
  return isoToShortDate(iso);
}

export function formatDuration(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${h}h ${m}m`;
}
```

- [ ] **Step 6: Run test (should pass)**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run src/lib/__tests__/format.test.ts 2>&1 | tail -10
```

Expected: 5 tests pass.

- [ ] **Step 7: Write verdict.test.ts**

Create `web/src/lib/__tests__/verdict.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { computeVerdict } from "../verdict";

describe("computeVerdict", () => {
  it("returns BUY_NOW within 5% of historical min", () => {
    expect(computeVerdict(1050, 2000, 1000)).toBe("BUY_NOW");
    expect(computeVerdict(1000, 2000, 1000)).toBe("BUY_NOW");
  });
  it("returns WAIT at 15%+ above average", () => {
    expect(computeVerdict(2300, 2000, 1500)).toBe("WAIT");
    expect(computeVerdict(2300, 2000, 1000)).toBe("WAIT");
  });
  it("returns OK in between", () => {
    expect(computeVerdict(1700, 2000, 1500)).toBe("OK");
    expect(computeVerdict(2000, 2000, 1500)).toBe("OK");
  });
  it("falls back to OK when historicals are zero", () => {
    expect(computeVerdict(1000, 0, 0)).toBe("OK");
  });
});
```

- [ ] **Step 8: Implement verdict.ts**

Create `web/src/lib/verdict.ts`:

```ts
export type Verdict = "BUY_NOW" | "OK" | "WAIT";

export function computeVerdict(
  currentBest: number,
  historicalAvg: number,
  historicalMin: number,
): Verdict {
  if (historicalMin > 0 && currentBest <= historicalMin * 1.05) return "BUY_NOW";
  if (historicalAvg > 0 && currentBest >= historicalAvg * 1.15) return "WAIT";
  return "OK";
}

export function verdictRationale(
  verdict: Verdict,
  historicalAvg: number,
  historicalMin: number,
): string {
  if (verdict === "BUY_NOW")
    return `Within 5% of all-time low (฿${historicalMin.toLocaleString()})`;
  if (verdict === "WAIT")
    return `15%+ above average (฿${Math.round(historicalAvg).toLocaleString()})`;
  return `Near average (฿${Math.round(historicalAvg).toLocaleString()})`;
}
```

- [ ] **Step 9: Run all tests**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run 2>&1 | tail -10
```

Expected: 9 passing.

- [ ] **Step 10: Implement settings.ts and api-client.ts**

Create `web/src/lib/settings.ts`:

```ts
const KEYS = {
  apiKey: "travelplan.apiKey",
  addedBy: "travelplan.addedBy",
} as const;

export function getStored(key: keyof typeof KEYS): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(KEYS[key]) ?? "";
}

export function setStored(key: keyof typeof KEYS, value: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEYS[key], value);
}

export function clearAllStored(): void {
  if (typeof window === "undefined") return;
  for (const v of Object.values(KEYS)) window.localStorage.removeItem(v);
}
```

Create `web/src/lib/api-client.ts` (port from `web/.attic/src/lib/api-client.ts`):

```ts
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
```

Create `web/src/lib/query-client.ts`:

```ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

- [ ] **Step 11: Verify build still passes**

```bash
cd /home/m4stersun/travelplan/web
npx tsc --noEmit 2>&1 | head -10
```

Expected: no output (clean).

- [ ] **Step 12: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src/lib web/src/test web/vitest.config.ts web/package.json
git commit -m "feat(web): lib modules — format, verdict, settings, api-client, query-client + tests"
```

---

## Task 4: TanStack Router scaffolding + __root layout + nav

**Files:**
- Modify: `web/src/main.tsx`
- Create: `web/src/App.tsx` (overwrite — was a smoke test)
- Create: `web/src/routes/__root.tsx`
- Create: `web/src/routes/index.tsx` (placeholder home for now)
- Create: `web/src/components/nav-mobile.tsx`
- Create: `web/src/components/nav-desktop.tsx`

- [ ] **Step 1: Wire router into App.tsx**

Replace `web/src/App.tsx`:

```tsx
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { routeTree } from "./routeTree.gen";
import { queryClient } from "./lib/query-client";

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Create __root layout**

Create `web/src/routes/__root.tsx`:

```tsx
import { Outlet, createRootRoute } from "@tanstack/react-router";
import { NavDesktop } from "@/components/nav-desktop";
import { NavMobile } from "@/components/nav-mobile";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavDesktop />
      <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-4 md:py-8 pb-24 md:pb-8">
        <Outlet />
      </main>
      <NavMobile />
    </div>
  );
}
```

- [ ] **Step 3: Create nav-mobile**

Create `web/src/components/nav-mobile.tsx`:

```tsx
import { Link } from "@tanstack/react-router";
import { Home, Plus, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  { to: "/", label: "Home", icon: Home },
  { to: "/add", label: "Add", icon: Plus },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function NavMobile() {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t bg-background/90 backdrop-blur"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <div className="grid grid-cols-3">
        {ITEMS.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="flex flex-col items-center gap-1 py-2 text-[11px] text-muted-foreground"
            activeProps={{ className: "text-foreground" }}
          >
            <Icon className="size-5" />
            <span>{label}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Create nav-desktop**

Create `web/src/components/nav-desktop.tsx`:

```tsx
import { Link } from "@tanstack/react-router";

const ITEMS = [
  { to: "/", label: "Home" },
  { to: "/add", label: "Add trip" },
  { to: "/settings", label: "Settings" },
] as const;

export function NavDesktop() {
  return (
    <header className="hidden md:block border-b">
      <div className="mx-auto max-w-2xl px-4 py-3 flex items-center justify-between">
        <Link to="/" className="font-semibold">
          Travelplan
        </Link>
        <nav className="flex gap-4 text-sm">
          {ITEMS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="text-muted-foreground hover:text-foreground"
              activeProps={{ className: "text-foreground font-medium" }}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Create placeholder index route**

Create `web/src/routes/index.tsx`:

```tsx
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Travelplan</h1>
      <p className="text-sm text-muted-foreground">Home page placeholder.</p>
    </div>
  );
}
```

- [ ] **Step 6: Run dev server and verify routing**

```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 4
curl -sS http://localhost:5173/ | grep -q "Home page placeholder" && echo OK
kill %1
```

Expected: `OK`. The TanStack Router plugin should auto-generate `routeTree.gen.ts` on first dev run.

- [ ] **Step 7: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src
git commit -m "feat(web): TanStack Router scaffolding with __root + mobile/desktop nav"
```

---

## Task 5: Home route — TripCard + Sparkline + VerdictBadge

**Files:**
- Create: `web/src/components/sparkline.tsx`
- Create: `web/src/components/verdict-badge.tsx`
- Create: `web/src/components/trip-card.tsx`
- Create: `web/src/components/empty-state.tsx`
- Modify: `web/src/routes/index.tsx`
- Create: `web/src/components/__tests__/verdict-badge.test.tsx`

- [ ] **Step 1: Sparkline component**

Create `web/src/components/sparkline.tsx`:

```tsx
interface Props {
  data: number[];
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkline({ data, width = 96, height = 32, className }: Props) {
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = data.length > 1 ? width / (data.length - 1) : 0;
  const points = data
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const trendDown = data.length > 1 && data[data.length - 1]! < data[0]!;
  const stroke = trendDown ? "#16a34a" : "#dc2626";
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="price trend sparkline"
    >
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}
```

- [ ] **Step 2: Write verdict-badge test**

Create `web/src/components/__tests__/verdict-badge.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { VerdictBadge } from "../verdict-badge";

describe("VerdictBadge", () => {
  it("shows BUY NOW when current is at the floor", () => {
    render(<VerdictBadge currentBest={1000} historicalAvg={2000} historicalMin={1000} />);
    expect(screen.getByText("BUY NOW")).toBeInTheDocument();
  });
  it("shows WAIT when current is well above avg", () => {
    render(<VerdictBadge currentBest={2400} historicalAvg={2000} historicalMin={1000} />);
    expect(screen.getByText("WAIT")).toBeInTheDocument();
  });
  it("shows OK in between", () => {
    render(<VerdictBadge currentBest={1800} historicalAvg={2000} historicalMin={1500} />);
    expect(screen.getByText("OK")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run test (should fail)**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run src/components/__tests__/verdict-badge.test.tsx 2>&1 | tail -8
```

Expected: failure — module not found.

- [ ] **Step 4: VerdictBadge component**

Create `web/src/components/verdict-badge.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import { computeVerdict, verdictRationale, type Verdict } from "@/lib/verdict";

interface Props {
  currentBest: number;
  historicalAvg: number;
  historicalMin: number;
  className?: string;
  showRationale?: boolean;
}

const LABEL: Record<Verdict, string> = {
  BUY_NOW: "BUY NOW",
  OK: "OK",
  WAIT: "WAIT",
};

const STYLE: Record<Verdict, string> = {
  BUY_NOW: "bg-green-600 hover:bg-green-700 text-white border-transparent",
  OK: "bg-amber-500 hover:bg-amber-600 text-white border-transparent",
  WAIT: "bg-red-600 hover:bg-red-700 text-white border-transparent",
};

export function VerdictBadge({
  currentBest,
  historicalAvg,
  historicalMin,
  className,
  showRationale = false,
}: Props) {
  const verdict = computeVerdict(currentBest, historicalAvg, historicalMin);
  return (
    <div className={className}>
      <Badge className={STYLE[verdict]}>{LABEL[verdict]}</Badge>
      {showRationale && (
        <p className="text-xs text-muted-foreground mt-1">
          {verdictRationale(verdict, historicalAvg, historicalMin)}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run test (should pass)**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run src/components/__tests__/verdict-badge.test.tsx 2>&1 | tail -8
```

Expected: 3 pass.

- [ ] **Step 6: TripCard component**

Create `web/src/components/trip-card.tsx`:

```tsx
import { Link } from "@tanstack/react-router";
import { Card, CardContent } from "@/components/ui/card";
import { VerdictBadge } from "@/components/verdict-badge";
import { Sparkline } from "@/components/sparkline";
import { formatThb } from "@/lib/format";

export interface TripCardProps {
  id: string;
  tripName: string;
  cheapestCombo: number;
  goLabel: string;
  cheapestAirline?: string;
  bestSource?: string;
  sparklineData?: number[];
  historicalAvg?: number;
  historicalMin?: number;
}

export function TripCard(props: TripCardProps) {
  const showVerdict =
    typeof props.historicalAvg === "number" && typeof props.historicalMin === "number";
  return (
    <Link
      to="/trip/$id"
      params={{ id: props.id }}
      className="block focus:outline-none focus:ring-2 focus:ring-ring rounded-xl"
    >
      <Card>
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="font-semibold">{props.tripName}</div>
            {showVerdict && (
              <VerdictBadge
                currentBest={props.cheapestCombo}
                historicalAvg={props.historicalAvg ?? 0}
                historicalMin={props.historicalMin ?? 0}
              />
            )}
          </div>
          <div className="flex items-end justify-between gap-3">
            <div>
              <div className="text-3xl font-bold leading-none">
                {formatThb(props.cheapestCombo)}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {props.goLabel}
                {props.bestSource ? ` · ${props.bestSource}` : ""}
              </div>
            </div>
            {props.sparklineData && props.sparklineData.length > 1 && (
              <Sparkline data={props.sparklineData} />
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 7: EmptyState component**

Create `web/src/components/empty-state.tsx`:

```tsx
import { ReactNode } from "react";

interface Props {
  title: string;
  body?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, body, action }: Props) {
  return (
    <div className="text-center py-16">
      <p className="text-base font-medium">{title}</p>
      {body && <div className="text-sm text-muted-foreground mt-2">{body}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

- [ ] **Step 8: Implement Home route**

Replace `web/src/routes/index.tsx`:

```tsx
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQueries, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { TripCard } from "@/components/trip-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { shortDateToIso } from "@/lib/format";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const overviewQ = useQuery({ queryKey: ["overview"], queryFn: api.getOverview });
  const overview = overviewQ.data ?? [];

  const trends = useQueries({
    queries: overview.map((r) => {
      const isoDate = shortDateToIso(r.date);
      return {
        queryKey: ["trend", r.route, isoDate, 14],
        queryFn: () => api.getTrend(r.route, isoDate, 14),
      };
    }),
  });

  if (overviewQ.isLoading) return <SkeletonGrid />;
  if (overviewQ.isError)
    return (
      <EmptyState
        title="Could not load trips"
        body="Check the network and try again."
        action={<Button onClick={() => overviewQ.refetch()}>Retry</Button>}
      />
    );
  if (!overview.length)
    return (
      <EmptyState
        title="No trips yet"
        body="Add your first trip to start tracking prices."
        action={
          <Link to="/add">
            <Button>Add a trip</Button>
          </Link>
        }
      />
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Travelplan</h1>
      <p className="text-xs text-muted-foreground mb-4">
        Auto-checks every 2 hours · last update {overview[0]?.lastCheck}
      </p>

      <div className="space-y-3">
        {overview.map((r, i) => {
          const trend = trends[i]?.data ?? [];
          const prices = trend.map((p) => p.bestPrice).filter((v) => v > 0);
          const min = prices.length ? Math.min(...prices) : 0;
          const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
          const isoDate = shortDateToIso(r.date);
          const id = `${r.route}-${isoDate}`;
          return (
            <TripCard
              key={id}
              id={id}
              tripName={r.route}
              cheapestCombo={r.bestPrice}
              goLabel={r.date}
              cheapestAirline={r.cheapestAirline}
              bestSource={r.bestSource}
              sparklineData={prices.slice(-14)}
              historicalAvg={avg}
              historicalMin={min}
            />
          );
        })}
      </div>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 rounded-xl border bg-muted/40 animate-pulse"
          aria-hidden
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 9: Verify dev server**

```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 4
curl -sS http://localhost:5173/ > /tmp/home.html
grep -q "Travelplan" /tmp/home.html && echo OK
kill %1
```

Expected: `OK`. Visit http://localhost:5173 in browser to verify cards render.

- [ ] **Step 10: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src
git commit -m "feat(web): home route with TripCard + Sparkline + VerdictBadge"
```

---

## Task 6: Trip detail route — chart + flight list

**Files:**
- Create: `web/src/components/price-trend-chart.tsx`
- Create: `web/src/components/flight-row.tsx`
- Create: `web/src/components/flight-list.tsx`
- Create: `web/src/routes/trip.$id.tsx`
- Create: `web/src/components/__tests__/flight-row.test.tsx`

- [ ] **Step 1: PriceTrendChart**

Create `web/src/components/price-trend-chart.tsx`:

```tsx
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { formatThb } from "@/lib/format";

interface Point {
  scrapedAt: string;
  bestPrice: number;
}

interface Props {
  data: Point[];
  height?: number;
}

function tickLabel(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(ts);
  if (!m) return ts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(m[2], 10) - 1]} ${parseInt(m[3], 10)}`;
}

export function PriceTrendChart({ data, height = 240 }: Props) {
  if (!data.length) {
    return (
      <div className="text-center py-12 text-sm text-muted-foreground">
        No price history yet
      </div>
    );
  }
  const avg = data.reduce((s, d) => s + d.bestPrice, 0) / data.length;
  const min = Math.min(...data.map((d) => d.bestPrice));
  const max = Math.max(...data.map((d) => d.bestPrice));
  const yPad = (max - min) * 0.1 || 100;
  const chartData = data.map((d) => ({ ...d, label: tickLabel(d.scrapedAt) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis
          domain={[Math.floor(min - yPad), Math.ceil(max + yPad)]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => formatThb(v as number)}
          width={64}
        />
        <Tooltip
          formatter={(v) => [formatThb(v as number), "Best price"]}
          labelFormatter={(label) => label as string}
        />
        <ReferenceLine
          y={avg}
          stroke="#94a3b8"
          strokeDasharray="3 3"
          label={{
            value: `avg ${formatThb(Math.round(avg))}`,
            fontSize: 10,
            fill: "#94a3b8",
            position: "right",
          }}
        />
        <Line
          type="monotone"
          dataKey="bestPrice"
          stroke="#16a34a"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Write flight-row test**

Create `web/src/components/__tests__/flight-row.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FlightRow } from "../flight-row";
import type { FlightRow as FlightRowType } from "@/lib/api-client";

const sample: FlightRowType = {
  route: "BKK-DAD",
  date: "2026-05-29",
  scrapedAt: "2026-04-26 13:08:50",
  airline: "Thai AirAsia",
  departureTime: "07:50",
  arrivalTime: "09:30",
  durationMinutes: 100,
  priceThb: 3621,
  bestBookingPrice: 3466,
  bestBookingSource: "Jettzy",
  isDirect: true,
};

describe("FlightRow", () => {
  it("shows the cheaper booking price when present", () => {
    render(<FlightRow flight={sample} />);
    expect(screen.getByText(/3,466/)).toBeInTheDocument();
    expect(screen.getByText(/Jettzy/)).toBeInTheDocument();
  });
  it("shows airline price when no booking source", () => {
    render(<FlightRow flight={{ ...sample, bestBookingPrice: null, bestBookingSource: null }} />);
    expect(screen.getByText(/3,621/)).toBeInTheDocument();
  });
  it("renders Direct badge for direct flights", () => {
    render(<FlightRow flight={sample} />);
    expect(screen.getByText("Direct")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: FlightRow component**

Create `web/src/components/flight-row.tsx`:

```tsx
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
```

- [ ] **Step 4: Run flight-row test**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run src/components/__tests__/flight-row.test.tsx 2>&1 | tail -8
```

Expected: 3 pass.

- [ ] **Step 5: FlightList component**

Create `web/src/components/flight-list.tsx`:

```tsx
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
```

- [ ] **Step 6: Trip detail route**

Create `web/src/routes/trip.$id.tsx`:

```tsx
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PriceTrendChart } from "@/components/price-trend-chart";
import { FlightList } from "@/components/flight-list";
import { VerdictBadge } from "@/components/verdict-badge";
import { EmptyState } from "@/components/empty-state";
import { formatThb, isoToShortDate } from "@/lib/format";

export const Route = createFileRoute("/trip/$id")({
  component: TripDetail,
});

function parseId(id: string): { route: string; isoDate: string } | null {
  // id = "BKK-DAD-2026-05-29"
  const m = id.match(/^([A-Z]{3}-[A-Z]{3})-(\d{4}-\d{2}-\d{2})$/);
  if (!m) return null;
  return { route: m[1], isoDate: m[2] };
}

function TripDetail() {
  const { id } = Route.useParams();
  const parsed = parseId(id);

  const trendQ = useQuery({
    queryKey: ["trend", parsed?.route, parsed?.isoDate, 30],
    queryFn: () => api.getTrend(parsed!.route, parsed!.isoDate, 30),
    enabled: !!parsed,
  });

  const flightsQ = useQuery({
    queryKey: ["flights", parsed?.route, parsed?.isoDate, 5],
    queryFn: () =>
      api.getFlights({ route: parsed!.route, date: parsed!.isoDate, limit: 5 }),
    enabled: !!parsed,
  });

  if (!parsed) {
    return <EmptyState title="Invalid trip id" body={`Could not parse ${id}`} />;
  }

  const trend = trendQ.data ?? [];
  const flights = flightsQ.data ?? [];
  const prices = trend.map((p) => p.bestPrice).filter((v) => v > 0);
  const min = prices.length ? Math.min(...prices) : 0;
  const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
  const current = prices.length ? prices[prices.length - 1]! : 0;

  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground mb-4 hover:text-foreground">
        <ArrowLeft className="size-4" /> Home
      </Link>

      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold leading-tight">{parsed.route}</h1>
          <p className="text-xs text-muted-foreground mt-1">{isoToShortDate(parsed.isoDate)}</p>
        </div>
        {avg > 0 && (
          <VerdictBadge
            currentBest={current}
            historicalAvg={avg}
            historicalMin={min}
            showRationale
          />
        )}
      </div>

      <div className="text-3xl font-bold mb-4">
        {formatThb(current)}
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-sm">Price history (30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {trendQ.isLoading ? (
            <div className="h-60 rounded bg-muted/30 animate-pulse" />
          ) : (
            <PriceTrendChart data={trend} />
          )}
          {prices.length > 0 && (
            <>
              <Separator className="my-3" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>min {formatThb(min)}</span>
                <span>avg {formatThb(Math.round(avg))}</span>
                <span>max {formatThb(Math.max(...prices))}</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <h2 className="text-sm font-semibold mb-2">Top 5 flights</h2>
      {flightsQ.isLoading ? (
        <div className="h-32 rounded-xl border bg-muted/30 animate-pulse" />
      ) : (
        <FlightList flights={flights} emptyTitle="No flights cached for this date" />
      )}

      <div className="mt-6 flex gap-2">
        <Button variant="outline" size="sm" onClick={() => trendQ.refetch()}>
          Refresh
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Run all tests**

```bash
cd /home/m4stersun/travelplan/web
npx vitest run 2>&1 | tail -8
```

Expected: ≥ 12 pass.

- [ ] **Step 8: Verify dev server still routes**

```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 4
curl -sS "http://localhost:5173/trip/BKK-DAD-2026-05-29" | grep -q "Home" && echo OK
kill %1
```

Expected: `OK`.

- [ ] **Step 9: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src
git commit -m "feat(web): trip detail route with chart + top 5 flights"
```

---

## Task 7: Add trip route

**Files:**
- Create: `web/src/routes/add.tsx`

- [ ] **Step 1: Add route**

Create `web/src/routes/add.tsx`:

```tsx
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getStored, setStored } from "@/lib/settings";

export const Route = createFileRoute("/add")({
  component: AddTrip,
});

const todayIso = () => new Date().toISOString().slice(0, 10);

function AddTrip() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    tripName: "",
    from: "Bangkok",
    to: "",
    returnFrom: "",
    goDate: todayIso(),
    backDate: todayIso(),
    preferDepart: "12:00",
    preferArrive: "18:00",
    addedBy: "",
    apiKey: "",
  });
  const [errMsg, setErrMsg] = useState("");

  useEffect(() => {
    setForm((f) => ({
      ...f,
      addedBy: getStored("addedBy") || f.addedBy,
      apiKey: getStored("apiKey") || f.apiKey,
    }));
  }, []);

  const mut = useMutation({
    mutationFn: () =>
      api.addTrip(
        {
          tripName: form.tripName,
          from: form.from,
          to: form.to,
          returnFrom: form.returnFrom || undefined,
          goDate: form.goDate,
          backDate: form.backDate,
          preferDepart: form.preferDepart,
          preferArrive: form.preferArrive,
          addedBy: form.addedBy,
        },
        form.apiKey,
      ),
    onSuccess: () => {
      setStored("apiKey", form.apiKey);
      setStored("addedBy", form.addedBy);
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      navigate({ to: "/" });
    },
    onError: (e: Error) => setErrMsg(e.message),
  });

  function update<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm({ ...form, [k]: v });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a trip</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="grid gap-4 md:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setErrMsg("");
            mut.mutate();
          }}
        >
          <Field label="Trip name" required>
            <Input value={form.tripName} onChange={(e) => update("tripName", e.target.value)} required />
          </Field>
          <Field label="Added by" required>
            <Input value={form.addedBy} onChange={(e) => update("addedBy", e.target.value)} required />
          </Field>
          <Field label="From">
            <Input value={form.from} onChange={(e) => update("from", e.target.value)} required />
          </Field>
          <Field label="To" required>
            <Input value={form.to} onChange={(e) => update("to", e.target.value)} required />
          </Field>
          <Field label="Go date">
            <Input
              type="date"
              value={form.goDate}
              min={todayIso()}
              onChange={(e) => update("goDate", e.target.value)}
              required
            />
          </Field>
          <Field label="Back date">
            <Input
              type="date"
              value={form.backDate}
              min={form.goDate}
              onChange={(e) => update("backDate", e.target.value)}
              required
            />
          </Field>
          <Field label="Return from (optional)" hint="Blank = same as 'To'">
            <Input value={form.returnFrom} onChange={(e) => update("returnFrom", e.target.value)} />
          </Field>
          <Field label="API key" required>
            <Input
              type="password"
              value={form.apiKey}
              onChange={(e) => update("apiKey", e.target.value)}
              required
            />
          </Field>
          <div className="md:col-span-2 flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={mut.isPending}>
              {mut.isPending ? "Adding…" : "Add trip"}
            </Button>
            {errMsg && <span className="text-sm text-destructive">{errMsg}</span>}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /home/m4stersun/travelplan/web
npx tsc --noEmit 2>&1 | head -10
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src
git commit -m "feat(web): /add route with mutation + localStorage prefill"
```

---

## Task 8: Settings route + InstallHint

**Files:**
- Create: `web/src/components/install-hint.tsx`
- Create: `web/src/routes/settings.tsx`

- [ ] **Step 1: InstallHint**

Create `web/src/components/install-hint.tsx`:

```tsx
import { Card, CardContent } from "@/components/ui/card";

function isIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(display-mode: standalone)").matches;
}

export function InstallHint() {
  if (typeof window === "undefined") return null;
  if (isStandalone()) {
    return (
      <p className="text-xs text-muted-foreground">
        ✓ Installed on home screen.
      </p>
    );
  }
  return (
    <Card>
      <CardContent className="p-4 text-sm">
        <p className="font-medium mb-1">Install Travelplan</p>
        {isIOS() ? (
          <p className="text-muted-foreground">
            Tap the <strong>Share</strong> button in Safari, then <strong>Add to Home Screen</strong>.
          </p>
        ) : (
          <p className="text-muted-foreground">
            Use your browser menu → <strong>Install app</strong> (Chrome/Edge on Android & desktop).
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Settings route**

Create `web/src/routes/settings.tsx`:

```tsx
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InstallHint } from "@/components/install-hint";
import { clearAllStored, getStored, setStored } from "@/lib/settings";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [addedBy, setAddedBy] = useState("");
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setApiKey(getStored("apiKey"));
    setAddedBy(getStored("addedBy"));
  }, []);

  function save() {
    setStored("apiKey", apiKey);
    setStored("addedBy", addedBy);
    setSavedAt(Date.now());
  }

  function clear() {
    clearAllStored();
    setApiKey("");
    setAddedBy("");
    setSavedAt(Date.now());
  }

  function refresh() {
    queryClient.invalidateQueries();
    setSavedAt(Date.now());
  }

  const version = import.meta.env.MODE === "production" ? "production" : "dev";

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Stored credentials</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Added by</Label>
            <Input value={addedBy} onChange={(e) => setAddedBy(e.target.value)} placeholder="your name" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">API key</Label>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            <Button onClick={save}>Save</Button>
            <Button variant="outline" onClick={clear}>Clear all</Button>
          </div>
          {savedAt && (
            <p className="text-xs text-muted-foreground">Saved at {new Date(savedAt).toLocaleTimeString()}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data</CardTitle>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={refresh}>Force refresh</Button>
          <p className="text-xs text-muted-foreground mt-2">
            Invalidates cached API queries. Useful right after a manual scrape.
          </p>
        </CardContent>
      </Card>

      <InstallHint />

      <p className="text-xs text-muted-foreground text-center">
        Travelplan · {version}
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Verify all four routes**

```bash
cd /home/m4stersun/travelplan/web
npm run dev &
sleep 4
for path in / /trip/BKK-DAD-2026-05-29 /add /settings; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" "http://localhost:5173$path")
  echo "$path → $code"
done
kill %1
```

Expected: each path returns 200.

- [ ] **Step 4: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/src
git commit -m "feat(web): /settings + InstallHint"
```

---

## Task 9: PWA shell — manifest, sw.js, icons, sw-register

**Files:**
- Create: `web/public/manifest.webmanifest`
- Create: `web/public/sw.js`
- Create: `web/public/icon-192.png` (port from `web/.attic/public/icon-192.png`)
- Create: `web/public/icon-512.png` (port from `web/.attic/public/icon-512.png`)
- Create: `web/src/components/sw-register.tsx`
- Modify: `web/src/routes/__root.tsx`
- Modify: `web/index.html`

- [ ] **Step 1: Port icons from attic**

```bash
cd /home/m4stersun/travelplan/web
cp .attic/public/icon-192.png .attic/public/icon-512.png public/
```

- [ ] **Step 2: Create manifest**

Create `web/public/manifest.webmanifest`:

```json
{
  "name": "Travelplan",
  "short_name": "Travelplan",
  "description": "Flight price tracker and decision support",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0a0a0a",
  "theme_color": "#0a0a0a",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
```

- [ ] **Step 3: Create service worker**

Create `web/public/sw.js`:

```js
const CACHE = "travelplan-v1";
const API_RE = /^https:\/\/travelplan-api\.[^/]+\/(overview|flights|trends|trips|alerts)/;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  if (API_RE.test(request.url)) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }
  if (request.mode === "navigate" || (request.headers.get("accept") || "").includes("text/html")) {
    event.respondWith(networkFirst(request));
    return;
  }
});

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request).then((resp) => {
    if (resp.ok) cache.put(request, resp.clone());
    return resp;
  }).catch(() => cached);
  return cached || network;
}

async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(request);
    return cached || new Response("Offline", { status: 503 });
  }
}
```

- [ ] **Step 4: SWRegister component**

Create `web/src/components/sw-register.tsx`:

```tsx
import { useEffect } from "react";

export function SWRegister() {
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !("serviceWorker" in navigator) ||
      window.location.hostname === "localhost"
    ) return;
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((e) => console.warn("SW register failed", e));
  }, []);
  return null;
}
```

- [ ] **Step 5: Mount SWRegister in __root**

Replace `web/src/routes/__root.tsx`:

```tsx
import { Outlet, createRootRoute } from "@tanstack/react-router";
import { NavDesktop } from "@/components/nav-desktop";
import { NavMobile } from "@/components/nav-mobile";
import { SWRegister } from "@/components/sw-register";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavDesktop />
      <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-4 md:py-8 pb-24 md:pb-8">
        <Outlet />
      </main>
      <NavMobile />
      <SWRegister />
    </div>
  );
}
```

- [ ] **Step 6: Update index.html with manifest + theme**

Replace `web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
    <meta name="theme-color" content="#0a0a0a" />
    <link rel="icon" href="/icon-192.png" />
    <link rel="apple-touch-icon" href="/icon-192.png" />
    <link rel="manifest" href="/manifest.webmanifest" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="Travelplan" />
    <title>Travelplan</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Verify production build**

```bash
cd /home/m4stersun/travelplan/web
npm run build 2>&1 | tail -10
ls dist/
```

Expected: `dist/index.html`, `dist/assets/`, `dist/manifest.webmanifest`, `dist/sw.js`, `dist/icon-*.png`.

- [ ] **Step 8: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/public web/src/components/sw-register.tsx web/src/routes/__root.tsx web/index.html
git commit -m "feat(web): PWA shell — manifest, sw.js, icons, register"
```

---

## Task 10: Cloudflare static assets deploy

**Files:**
- Create: `web/wrangler.jsonc`
- Create: `web/_worker.ts`
- Modify: `web/package.json` (deploy scripts)

- [ ] **Step 1: Create _worker.ts (SPA fallback)**

Create `web/_worker.ts`:

```ts
// Static-assets-only Worker. Serves built SPA from `dist/`.
// Falls back to index.html for client-side routes.
interface Env {
  ASSETS: { fetch: (req: Request) => Promise<Response> };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // Try the asset directly
    const direct = await env.ASSETS.fetch(request);
    if (direct.status !== 404) return direct;
    // SPA fallback to index.html for non-asset paths
    if (!url.pathname.includes(".")) {
      const indexReq = new Request(new URL("/", request.url), request);
      return env.ASSETS.fetch(indexReq);
    }
    return direct;
  },
};
```

- [ ] **Step 2: Create wrangler.jsonc**

Create `web/wrangler.jsonc`:

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "travelplan",
  "main": "_worker.ts",
  "compatibility_date": "2025-04-01",
  "assets": {
    "directory": "dist",
    "binding": "ASSETS",
    "not_found_handling": "single-page-application"
  },
  "observability": { "enabled": true }
}
```

- [ ] **Step 3: Add deploy scripts**

Modify `web/package.json` `"scripts"` section to include:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "deploy": "npm run build && wrangler deploy"
  }
}
```

- [ ] **Step 4: Deploy**

```bash
cd /home/m4stersun/travelplan/web
TOKEN="<paste user's CLOUDFLARE_API_TOKEN here>"
CLOUDFLARE_API_TOKEN="$TOKEN" npm run deploy 2>&1 | tail -10
```

Expected: `Deployed travelplan triggers ... https://travelplan.<subdomain>.workers.dev`.

- [ ] **Step 5: Smoke test live**

```bash
URL="https://travelplan.nattawatsun01.workers.dev"
echo "homepage: $(curl -sS -o /dev/null -w '%{http_code}' $URL/)"
echo "trip:     $(curl -sS -o /dev/null -w '%{http_code}' $URL/trip/BKK-DAD-2026-05-29)"
echo "manifest: $(curl -sS -o /dev/null -w '%{http_code}' $URL/manifest.webmanifest)"
echo "sw.js:    $(curl -sS -o /dev/null -w '%{http_code}' $URL/sw.js)"
echo "icon:     $(curl -sS -o /dev/null -w '%{http_code}' $URL/icon-192.png)"
```

Expected: each `200`.

- [ ] **Step 6: Commit**

```bash
cd /home/m4stersun/travelplan
git add web/wrangler.jsonc web/_worker.ts web/package.json
git commit -m "feat(web): Cloudflare static assets deploy with SPA fallback"
git push origin master
```

---

## Task 11: Cleanup — drop the attic

**Files:**
- Delete: `web/.attic/`

- [ ] **Step 1: Verify production deploy is healthy**

Open https://travelplan.nattawatsun01.workers.dev/ in a browser. Visit each route. Tap a card. Confirm the chart loads. Confirm Add Trip POSTs successfully (use known API key from Settings).

- [ ] **Step 2: Drop the attic**

```bash
cd /home/m4stersun/travelplan
git rm -rf web/.attic
git status --short | head
```

Expected: `D` entries for every file under `web/.attic/`.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(web): drop the Next.js attic — rewrite verified live"
git push origin master
```

---

## Self-review

**Spec coverage:** every section of `2026-04-26-fe-rewrite-design.md` maps to a task here:
- Routing → Tasks 4-8
- Library modules → Task 3
- Components → Tasks 5, 6, 8 (TripCard, VerdictBadge, Sparkline, PriceTrendChart, FlightRow, FlightList, NavMobile, NavDesktop, EmptyState, InstallHint, SWRegister)
- PWA → Task 9
- Deploy → Task 10
- Cleanup → Task 11
- Tests → Tasks 3 (lib) and 5-6 (component)

**Placeholders:** none. Every code block is complete.

**Type consistency:** `FlightRow` interface is the api-client export and the component name; component uses the type-aliased import `FlightRowType` to avoid the collision (Task 6, Step 2). `Verdict` type is used consistently. `TripCardProps` matches its consumer in Home.

**Open questions for executor:**
- Step 4 of Task 10 needs the user's Cloudflare API token. The executor should retrieve it from the user (or from a secure shell env var) before running.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-fe-rewrite-plan.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session, batch with checkpoints for review.

**Which approach?**
