# Travelplan Design Prompt Library

Reusable prompts for generating shadcn-compatible components. Each prompt is self-contained and assumes existing primitives in `web/src/components/ui/`.

## How to use

Open the target file path. Paste the relevant prompt into Claude Code with: "Use this prompt to generate the component." The prompt produces a single React 19 + Tailwind v4 + shadcn component.

---

## 1. TripCard

```
Generate `TripCard` for `web/src/components/trip-card.tsx`.

Props:
  - tripName: string
  - cheapestCombo: number      // THB
  - verdict: 'BUY_NOW' | 'WAIT' | 'OK'
  - goDate: string             // ISO
  - backDate: string           // ISO
  - sparklineData: number[]    // recent 14 days

Requirements:
  - Mobile-first, full width, no horizontal scroll
  - Big bold price as primary visual
  - Verdict pill (use shadcn Badge with green/amber/neutral variants)
  - Inline SVG sparkline (~30 lines, no chart lib)
  - Use existing Card, Badge, Separator from @/components/ui
  - Tailwind v4, no extra deps
```

## 2. PriceTrendChart

```
Generate `PriceTrendChart` using Recharts in `web/src/components/price-trend-chart.tsx`.

Props:
  - data: { scrapedAt: string; bestPrice: number; airline: string }[]
  - historicalAvg: number

Requirements:
  - Line chart of bestPrice over scrapedAt for last 30 days
  - Highlight points where price < 0.85 × historicalAvg with a green dot
  - Tooltip shows date, THB-formatted price, source airline
  - ResponsiveContainer, height 240px on mobile
  - Theme-aware via CSS variables
```

## 3. PriceHeatmap

```
Generate `PriceHeatmap` for `web/src/components/price-heatmap.tsx`.

Props:
  - matrix: { go: string; back: string; price: number }[]
  - onSelect?: (go: string, back: string) => void

Requirements:
  - Calendar grid: rows = outbound dates, cols = return dates
  - Color scale: green for cheapest 25%, yellow middle, red top 25%
  - Cells clickable; emit onSelect
  - Pure SVG/CSS grid, no chart lib
  - Mobile-friendly (horizontal scroll OK)
```

## 4. VerdictBadge

```
Generate `VerdictBadge` in `web/src/components/verdict-badge.tsx`.

Props:
  - currentBest: number
  - historicalAvg: number
  - historicalMin: number

Logic:
  - BUY NOW: currentBest <= 1.05 × historicalMin
  - WAIT:    currentBest >= 1.15 × historicalAvg
  - OK:      otherwise

Requirements:
  - Shadcn Badge with green/amber/neutral variants
  - One-line rationale text below the badge
  - Accessible (aria-label with full reasoning)
```

## 5. FlightTableMobile

```
Generate `FlightTableMobile` in `web/src/components/flight-table-mobile.tsx`.

Props:
  - flights: Flight[]   // see api/src/schemas.ts

Requirements:
  - On md+, render existing Table primitive
  - On small screens, render stacked card list (one card per flight)
  - Show: airline, dep→arr time, duration, direct badge, price (prominent)
  - Expand-for-details disclosure with stops, baggage, booking source
  - Use existing Card, Badge from @/components/ui
```

## 6. BottomNav

```
Generate `BottomNav` in `web/src/components/bottom-nav.tsx`.

Requirements:
  - Fixed bottom-0 inset-x-0
  - Only visible below md breakpoint (hidden on md+)
  - Four items: Dashboard, Trends, Trips, Settings
  - Use lucide-react icons
  - Active state derived from current route via next/navigation usePathname
  - Safe-area-aware padding for iOS notch (env(safe-area-inset-bottom))
  - Backdrop blur, semi-transparent background
```

## 7. InstallPwaPrompt

```
Generate `InstallPwaPrompt` in `web/src/components/install-pwa-prompt.tsx`.

Requirements:
  - Listen for beforeinstallprompt, store deferred prompt in state
  - Track visit count in localStorage; show only after 3+ visits
  - Dismissible shadcn Card
  - On iOS Safari (no beforeinstallprompt), show alt instructions:
    "Tap Share, then Add to Home Screen"
  - Detect iOS: /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream
  - Auto-hide if already standalone (window.matchMedia('(display-mode: standalone)'))
```

## 8. OfflineBanner

```
Generate `OfflineBanner` in `web/src/components/offline-banner.tsx`.

Requirements:
  - Subscribe to navigator.onLine and online/offline events
  - Slim banner at top with WifiOff icon when offline
  - Auto-dismiss on reconnect
  - Use shadcn Alert primitive (add via npx shadcn@latest add alert if missing)
  - aria-live="polite" for accessibility
```

## 9. AddTripForm (mobile-first refactor)

```
Refactor `AddTripForm` in `web/src/components/add-trip.tsx`.

Requirements:
  - Single-column on mobile, two-column on md+ (grid)
  - Use existing Input, Label, Select, Button from @/components/ui
  - Native <input type="date"> with min=today (no date-picker dep)
  - Fields: tripName, from, to, returnFrom (optional, defaults to 'to'),
    goDate, backDate, preferDepart (HH:mm), preferArrive (HH:mm), addedBy
  - POST to /trips via TanStack Query useMutation
  - Optimistic success toast (use sonner or shadcn Toast)
  - Disable submit while pending; show inline error on failure
```

## 10. PriceDistributionHistogram

```
Generate `PriceDistributionHistogram` in `web/src/components/price-distribution.tsx` using Recharts BarChart.

Props:
  - data: { price: number; count: number; airlines: string[] }[]
  - median: number

Requirements:
  - X axis: price buckets (THB-formatted)
  - Y axis: count of scrape runs in bucket
  - Show median as ReferenceLine with label "Median ฿X,XXX"
  - Tooltip lists airlines that fell in the bucket (max 5, "+N more")
  - Theme-aware colors via CSS variables
  - ResponsiveContainer, height 280px
```

---

## Tips for iterating

- After generation, run `npm run lint` to catch issues
- Visual review on mobile (Chrome DevTools device toolbar at 360px wide)
- For complex variants: ask "regenerate but make the price font-size 2× larger and verdict pill smaller"
- Keep prompts versioned — when shadcn or Recharts API changes, update the prompts here, not in scattered chat history
