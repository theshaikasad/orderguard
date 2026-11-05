# OrderGuard implementation progress

## Verified baseline

- Read repository guidance, README, backend/frontend, PostgreSQL schema, migrations and tests before editing.
- M2 Compose healthy; all original 87 PostgreSQL tests passed before M3 changes. No M2 repair was needed.
- M3: settings, sourced conversational drafts, explicit publishing/versioning, pause, business scoping, frozen quote configuration snapshots, overview and Scenario Lab implemented.
- Live Muse Bloom & Co.: ₹859 quote and natural acceptance, published ₹799 bouquet price yielding ₹959 for a new customer, original ₹859 retained; direct PostgreSQL and HTTP isolation checks passed.
- Live Muse A–F scenarios passed. Florist final-slot race also passed with exactly one reservation.
- Real provider timeout saved no state; same-message retry refused unsupported 50-rose pricing. Explicit injected outage rolled back; real Muse retry and duplicate delivery were idempotent.
- Latest baseline: 117 PostgreSQL backend tests passed; frontend lint, native/image builds and Compose startup passed. Alembic at 0003_orders.
- 13 existing bakery/florist/production conversation records retained the exact same canonical digest across image recreation.
- Evidence: artifacts/m3/*.json. Three final-proxy live turns: interpretation median 12.378s, reply median 9.073s, SQL median 16.06ms, HTTP median 21.585s.

## Boundary of UI verification

Native Chrome created a business and submitted the exact Bloom seller message; sourced draft persisted. Full publish/edit UI acceptance is unverified. The requested Chrome extension repeatedly reports “browser access host is unavailable,” including after user reconnection and runtime reset. No claim of full browser acceptance is made.

## Expanded authorization

Latest user request authorizes M3 completion, Scenario G/H, supported catalogue upload, M4 adapter with signed synthetic tests, performance/reliability work and demo preparation. Owner unavailable; no real sends/public deployment/submission permitted.

## In progress

- Complete remaining M3 cases and text-menu upload.
- Verify current official Meta documentation, then implement a safe local Instagram adapter.

## Expanded verification

- Text-menu uploader implemented; three format/UTF-8/size tests pass. Unsupported PDFs/images/spreadsheets are disclosed.
- G (duplicate and out-of-order) and H (catalogue change while accepted) passed with genuine Muse in isolated florist namespaces.
- Signed Instagram replay processed a real Muse ₹959 order and natural acceptance; duplicate replay remained unchanged. No Instagram delivery occurred.
- Adapter tests cover raw signature tampering, account routing, duplicate conflicts, durable failures/backoff, unsupported media, out-of-order deliveries, disconnect, conservative window, held drafts, competing processors and fast enqueue during slow Muse inference.
- 147 PostgreSQL backend tests passed before the final self-message/non-ASCII-signature additions; final suite pending.
- Official Meta reasoning documentation verified `low`. A paired reply-only experiment returned approved Meta wording at 7.839s default and 4.868s low. This is one pair, not a general benchmark; defaults remain unchanged.
- OAuth/current account authorization remain incomplete. Instagram runtime credentials are not configured. Real sends are hard-disabled by Compose; no public send route exists.

## Final local verification

- Final application image: **151 backend tests passed** against PostgreSQL in the final polish re-run; all original regressions retained. One upstream deprecation warning remains.
- Frontend lint, three text-menu tests, native production build and final Docker builds passed.
- Final Compose startup: database/backend/frontend healthy; overview/settings/Lab/channels and their API routes return HTTP 200.
- Runtime and clean disposable migration check both reached `0004_instagram`.
- Final restart preserved the original 13 selected business/order/production records byte-for-byte in canonical JSON: `46f1c6e128d277932540e650cff9f2a2fe624e9a99ff77f2f1ac33c1822d2008`.
- Final repository scan checked 94 nonignored files against private runtime values and found zero exposures. No secrets printed/committed.
- Additional live Muse checks passed: written “two orders per day”; exact false-owner 50-rose request rejected; late flavor/product plus date change held pending with original production snapshot and one review.
- All eight Lab scenarios have live Muse evidence; signed synthetic Instagram replay accepted ₹959 and deduplicated correctly. No actual Instagram delivery occurred.
- Final runtime confirms live inbound=false, outbound=false, OAuth=not_implemented; no Instagram app/token credentials configured.
- Reports and source evidence are in `M3_REPORT.md`, `artifacts/m3`, `artifacts/m4`; demo and setup materials are under `docs`.

## Remaining blockers / stop boundary

Full Chrome-extension UI acceptance/mobile visual QA remain unverified because the browser access host was unavailable. OAuth, professional-account authorization, public webhook delivery, remote revocation and live Instagram sends are incomplete. No public deployment, real customer message, payment or hackathon submission was performed. The authorized final source and demo film push to `origin/main` was completed on November 5, 2026. Stop at the authorized M3/M4 adapter and demo-preparation boundary.
