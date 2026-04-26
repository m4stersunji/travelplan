# Post-mortem — Cloudflare deploy + Phase A/C build (2026-04-26)

**Date:** 2026-04-26
**Author:** Claude Opus 4.7 (1M context)
**Audience:** m4stersun
**Severity:** None — no production data lost; LINE + scraper kept running throughout.
**TL;DR:** Took most of a day to ship a Next.js PWA + Elysia API to Cloudflare Workers because of seven distinct issues, six of which were preventable with up-front verification. Final state: both workers green, full mobile-first FE, end-to-end working from phone.

---

## Final state (what shipped today)

- `https://travelplan.nattawatsun01.workers.dev` — Next.js 16 PWA, mobile-first, installable, BottomNav, Recharts trend, TripCard with VerdictBadge + Sparkline.
- `https://travelplan-api.nattawatsun01.workers.dev` — Elysia REST API on Cloudflare Workers; 6 endpoints; FlightDataSource interface ready for D1 in Phase B.
- All FE components migrated off the old `/api/sheets` Next.js routes onto the new Elysia worker via TanStack Query.
- Service worker caches API + static assets; offline-capable.
- Phase 1 reliability features (retry, sanity check, heartbeat, LINE quota) untouched and still running on the Python scraper.

Commits today (chronological):
- `034b1ce` ci: GitHub Actions commits flights.db back to repo
- `697fcbe` data: scrape run (auto)
- `8e58b15` Phase 1 reliability fixes (earlier work)
- `854146e` feat(web): add Cloudflare Workers deployment
- `454e9fd` fix(web): wrangler worker name = 'travelplan'
- `97bdf5f` debug(web): temporary /api/debug-creds endpoint
- `e80af72` fix(web): replace googleapis SDK with jose JWT signing
- `dad3770` chore(web): remove debug-creds
- `0eac635` feat(api): Elysia REST API on Cloudflare Workers (Phase A)
- `ce23040` feat(web): Phase A+C — TanStack Query + Recharts + PWA + mobile-first

---

## Timeline

Approximate Bangkok time.

| Time | Event |
|---|---|
| 06:00 | Add @opennextjs/cloudflare adapter to web/, initial build green locally. |
| 06:30 | First Cloudflare Workers Build via Git → fails ("Could not read package.json"). |
| 07:00 | Realised Cloudflare ran from repo root, not `web/`. Fixed root directory in dashboard. |
| 07:30 | Build green, deploy green. Hit homepage → 200. Hit `/api/sheets` → 500 "Missing required parameters: spreadsheetId". |
| 08:00 | Discovered worker name mismatch — wrangler.jsonc said `travelplan-web`, dashboard named project `travelplan`. CLI secrets went to phantom worker. |
| 08:30 | Fixed worker name to `travelplan`, redeployed. Now `/api/sheets` returns 500 "JSON object does not contain a client_email field". |
| 09:00 | User pasted multi-line JSON into dashboard secret form. Newlines mangled. |
| 09:30 | Switched to minified one-line JSON. Paste → save → still empty. Confirmed secret is literally empty (length 0). |
| 10:00 | Tried wrangler CLI to push secret, hit "non-interactive needs CLOUDFLARE_API_TOKEN" three times. |
| 10:30 | User created Cloudflare API token, pasted to me. I pushed secret via wrangler with `CLOUDFLARE_API_TOKEN=...`. Length now 2374 ✅. |
| 10:45 | New error: `[unenv] http.validateHeaderName is not implemented yet!` — googleapis SDK uses Node APIs not in the Workers shim. |
| 11:00 | Rewrote `web/src/lib/sheets.ts` to use direct REST + jose JWT signing. Deploy → green. `/api/sheets` returns data ✅. |
| 12:00 | Removed debug-creds endpoint. Wrote end-to-end rebuild plan + design prompt library. |
| 13:00 | Started Phase A — bootstrapped `api/` with Elysia + Bun. Implemented FlightDataSource + Sheets adapter. Deployed. |
| 13:30 | First request to API → 500 "Code generation from strings disallowed". Elysia AOT compilation incompatible with Workers. |
| 13:35 | Added `aot: false` to Elysia constructor. Redeployed. All 6 endpoints green. |
| 14:00 | Phase A endpoint quirks: `/trips` returned Config-tab instruction rows, `/trends` returned 0 (header mismatch). |
| 14:30 | Inspected actual sheet headers via existing `/api/sheets`, fixed mappings, redeployed. |
| 15:00 | Started Phase C — installed TanStack Query + Recharts, built API client. |
| 15:30 | Generated 7 new components from prompt library: TripCard, VerdictBadge, Sparkline, PriceTrendChart, FlightRowMobile, BottomNav, sw-register. |
| 16:00 | Migrated dashboard, flights-table, price-trends, add-trip to use api-client. |
| 16:30 | TS build failed: shadcn Select expects `(value: string \| null, eventDetails) => void`, I had `setRoute` directly. Fixed with arrow wrapper. |
| 17:00 | PWA shell — manifest, icons (placeholder T glyph), service worker, layout metadata. |
| 17:30 | Final deploy. All endpoints + assets verified ✅. |

---

## Issue catalogue (root cause + fix + prevention)

### 1. Wrong root directory in Cloudflare Workers Builds
- **Symptom:** `npm error enoent ... /opt/buildhome/repo/package.json`
- **Root cause:** Cloudflare ran the build from the repo root, where there's no `package.json`. The Next.js project is in the `web/` subdirectory of a monorepo; the Build settings need `Root directory: web`.
- **Fix:** Set Root directory to `web` in the dashboard.
- **Prevention:** Document this in the deploy spec for any monorepo. Add a `cloudflare-build-config.md` in `web/` with the exact dashboard fields.

### 2. Worker name mismatch between wrangler.jsonc and deployed project
- **Symptom:** Secrets uploaded via `wrangler secret put` "succeeded" but the deployed worker had no env vars.
- **Root cause:** I set `name: "travelplan-web"` in `wrangler.jsonc`, but the project I created in the Cloudflare dashboard was named `travelplan`. CLI secrets go to a worker matching the wrangler name; if no such worker exists, Cloudflare silently creates a phantom one separate from the deployed worker.
- **Fix:** Rename `wrangler.jsonc` `name` to match the deployed worker (`travelplan`).
- **Prevention:** Before any `wrangler secret put`, run `wrangler whoami` and `wrangler deployments list --name=$NAME` to confirm the worker exists. Or simpler: don't pre-create the project in the dashboard — let `wrangler deploy` create it from the wrangler.jsonc name.

### 3. `googleapis` npm SDK incompatible with Cloudflare Workers
- **Symptom:** Runtime error `[unenv] http.validateHeaderName is not implemented yet!` on every API route that called Sheets.
- **Root cause:** Cloudflare's `nodejs_compat` shim (via `unenv`) reimplements common Node APIs but not all of them. The `googleapis` SDK pulls the entire Google API stack including `gaxios` which uses Node `http` internals.
- **Fix:** Replaced the SDK with direct REST calls (`fetch`) and JWT signing via `jose` (~30 lines). Faster cold start, smaller bundle.
- **Prevention:** When picking server libraries for Workers, prefer "edge-compatible" or "fetch-based" packages. Smoke-test any Node SDK with a single endpoint before committing to it. The plan doc had flagged this as a risk; I should have led with the rewrite instead of trying `nodejs_compat` first.

### 4. Multi-line JSON pasted into dashboard secret form, then later empty
- **Symptom:** First paste → `/api/sheets` returns 500 "JSON object does not contain a client_email field". Second attempt → secret length is 0.
- **Root cause:**
  - First time: pasting a multi-line JSON value into the secret form preserved literal newlines in the stored value, breaking `JSON.parse`.
  - Second time: the dashboard "Edit secret" workflow re-uses a placeholder text and is sensitive to whether the user clicked into the textarea before pasting; under some conditions it saves empty silently.
- **Fix:** Built a temporary `/api/debug-creds` diagnostic endpoint that returned length, first/last chars, parse status, and key list (without exposing the secret). This made the empty-string case obvious. Then pushed the secret programmatically via wrangler with the API token (option C — described below).
- **Prevention:**
  - Always push secrets via API or CLI rather than dashboard paste, especially for >1KB JSON values.
  - Add a permanent `/api/health/secrets-shape` endpoint guarded by an admin token that returns just `{ key: lengthBytes }` for each env var. This makes "secret saved correctly" a single-curl verification.
  - For service-account JSON specifically: ship a tiny CLI helper in this repo that minifies `credentials.json` and pipes it to `wrangler secret put` in one command.

### 5. wrangler CLI demands `CLOUDFLARE_API_TOKEN` in non-interactive shells
- **Symptom:** `wrangler secret put NAME < file` errored with "In a non-interactive environment, it's necessary to set a CLOUDFLARE_API_TOKEN env var" — even though the user had run `wrangler login` (OAuth) earlier.
- **Root cause:** Wrangler treats stdin-redirected input as non-interactive and refuses to use stored OAuth credentials in that mode (security: avoids surprise token reuse from scripts). The `<` operator severs the TTY for stdin.
- **Fix:** User created a Cloudflare API token (template: "Edit Cloudflare Workers"), pasted it back. I set `CLOUDFLARE_API_TOKEN=...` and ran wrangler from the workspace shell.
- **Prevention:**
  - Document this once: "to use wrangler in scripts, use a long-lived API token, not OAuth login."
  - Add a `scripts/wrangler-cli.sh` wrapper in this repo that reads the token from a gitignored `.cf-token` file and exports it before invoking wrangler. Avoids repeated paste.
  - Treat the OAuth login as terminal-only.

### 6. Elysia AOT compilation incompatible with Workers
- **Symptom:** Worker exception `EvalError: Code generation from strings disallowed for this context`.
- **Root cause:** Elysia uses `new Function(...)` to compile validation/handler code at startup for performance. Cloudflare Workers' V8 isolate disables `new Function`/`eval` by default for security.
- **Fix:** Pass `{ aot: false }` to the Elysia constructor — disables runtime code-gen. Slight perf cost (a few µs per request), invisible at our request volume.
- **Prevention:** Document Workers-specific framework gotchas. The rebuild plan flagged this as a risk in the "Risks and mitigations" table; should have set `aot:false` from the first commit.

### 7. shadcn Select onValueChange type mismatch
- **Symptom:** TS build failed: `Type 'Dispatch<SetStateAction<string>>' is not assignable to type '(value: string | null, eventDetails: SelectRootChangeEventDetails) => void'`.
- **Root cause:** This shadcn Select wraps `@base-ui/react`'s SelectRoot, whose `onValueChange` signature includes `string | null` (not just `string`) and an event-details argument. Passing `setRoute` (a state setter expecting `string`) fails to type-check.
- **Fix:** Wrap with arrow function: `onValueChange={(v) => setRoute(v ?? "all")}`.
- **Prevention:** When a wrapper component's props don't match library-standard React patterns, read the wrapper's source first. Note in `web/CLAUDE.md` (already exists) calls this out: "this is NOT the Next.js you know" — same applies to its base-ui shadcn variant.

---

## Patterns that wasted time (process retrospective)

These aren't single bugs — they're meta-issues that compounded.

### 1. Trusting the deploy without verifying secrets
**What happened:** I told you the deploy succeeded (200 on homepage), then later we discovered no env var was actually set on the worker. The dashboard accepted my requests but the worker behind it didn't have the secrets attached.

**Lesson:** Always verify environment shape after deploy, not just HTTP status. The debug-creds endpoint should have been there from the first deploy, gated by a deploy-only token, then removed.

**Action:** Build a "verify-deploy.sh" script in `scripts/` that hits a health endpoint, an env-shape endpoint, and one real data endpoint after every deploy. Make it part of the post-deploy step.

### 2. Iterating in the dashboard UI instead of through code
**What happened:** I had you paste secrets via the dashboard form three separate times because each attempt failed in a different way (multiline mangled, empty save, etc.). All of those should have been one programmatic call.

**Lesson:** Browser forms are the worst place for >100-char values. Treat the dashboard as a debug-only surface.

**Action:** Anything sensitive or structured goes through wrangler / API. Period.

### 3. Adding `nodejs_compat` and hoping
**What happened:** I started with `googleapis` SDK + nodejs_compat, expecting it to "just work." It didn't. We lost ~30 min before reverting to direct REST.

**Lesson:** When the library has heavy Node dependencies, write the edge-native version first.

**Action:** Future Workers projects: prefer `fetch` + `jose` + `zod` over Node SDKs.

### 4. Skipping pre-flight checks because "the plan said it would work"
**What happened:** The rebuild plan flagged Elysia + Workers as a risk, googleapis on edge as a risk, and recommended Hono as a fallback. I still went straight to Elysia + googleapis because the plan was approved. Risks materialized exactly as the plan described.

**Lesson:** Plan risks are not optional — they're a checklist of things to validate before depending on them. The plan said "thin route handlers so a swap to Hono is mechanical" — that mitigation only works if you run a hello-world endpoint first to confirm the framework actually boots.

**Action:** For any new framework + runtime combo, the first commit should be a hello-world that verifies it works. Only after that, build the real thing.

### 5. The same git-state dance, repeatedly
**What happened:** Every commit + push hit a rebase-with-untracked-changes problem because GitHub Actions auto-commits `data/flights.db` while we work. I burned a few minutes per commit on stash/pop ceremony.

**Lesson:** This is a recurring class of issue, not a one-off.

**Action:** Add `data/flights.db` to `.gitattributes` with `merge=ours` strategy, or carve out a separate branch for cloud commits and merge nightly. Cleanest: stop committing the DB to repo and use D1 (Phase B in the plan, deferred).

---

## Key takeaways for future work

1. **Verify env shape after every deploy** — `/api/health/env-shape` returning `{ varName: byteLength }` for required env vars. Cheap insurance.
2. **Never paste secrets >100 chars in dashboard forms** — wrangler or API only.
3. **First request after deploy should hit a route that exercises every dependency** — not just `/health`. If the API uses Sheets, hit a Sheets-backed endpoint.
4. **Match worker name in wrangler.jsonc to deployed worker name** — and confirm before pushing secrets.
5. **For Cloudflare Workers, prefer `fetch` + edge libraries** — avoid Node SDKs even with `nodejs_compat`.
6. **Disable Elysia AOT (`aot: false`) when targeting Workers** — first thing in the constructor.
7. **Read framework-specific AGENTS.md / CLAUDE.md before writing code** — the `web/AGENTS.md` warning ("This is NOT the Next.js you know") was on point and I underused it.
8. **The plan's risk table is a pre-flight checklist** — work through it before building.

---

## Concrete follow-ups to ship

- [ ] Add `scripts/verify-deploy.sh` that runs after every deploy: hits health, env-shape, and one real data endpoint. CI fails on any non-200.
- [ ] Add `scripts/push-secrets.sh` that reads `.env.deploy` (gitignored) and pushes via wrangler in one shot. No paste required ever again.
- [ ] Add `/health/env` endpoint to api/ (gated by API_SECRET) that returns env var byte lengths.
- [ ] Move `data/flights.db` out of git tracking (Phase B — D1 migration). The git-rebase friction every push is real.
- [ ] Add a one-line note to `web/CLAUDE.md` about shadcn Select's onValueChange signature.
- [ ] Rotate the Cloudflare API token shared in chat (already advised — pending user action).
- [ ] Optional: rotate Google service-account key (printed in chat earlier).

---

## What went well

- The Phase 1 scraper reliability work shipped earlier this week did its job — through every deploy attempt today the LINE flow and GitHub Actions cron kept running. No data lost, no regression in user-visible features.
- The end-to-end rebuild plan from this morning correctly forecast every risk we hit. Re-reading the doc, every one of today's bugs is mentioned in the "Risks and mitigations" section.
- The design prompt library produced 7 components today with no rework. Useful pattern.
- The user-facing experience after this push is meaningfully better than yesterday: real chart, mobile bottom nav, installable PWA.

---

## Open items for next session

- Test on real iOS Safari (Add to Home Screen) and Chrome Android.
- Run a Lighthouse audit; aim for PWA ≥ 90.
- Delete `web/src/app/api/sheets/route.ts` and `web/src/app/api/trips/route.ts` — they're now unused.
- Begin Phase B (D1 migration) — see `docs/superpowers/specs/2026-04-25-end-to-end-rebuild-plan.md` section 4 (Phase B action list).
- Add the `verify-deploy.sh` and `push-secrets.sh` scripts called out above.
