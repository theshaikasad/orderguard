# OrderGuard

Configure once. Automate routine sales. Escalate genuine exceptions.

OrderGuard is a local, synthetic sales and order workspace for small businesses. **M3 adds conversational seller setup, editable settings, published configuration versions and an isolated Scenario Lab.** Meta Muse interprets language and selects validated replies. Python alone authorizes prices, capacity reservations and commitments. M4 adds a signature-verified Instagram inbox adapter and isolated replay; no live Instagram account, real payments, external notifications, authentication or cloud deployment is connected.

## Final submission package

[Copy-ready submission and owner checklist](docs/SUBMISSION.md) · [Exact recording script and manual UI checks](docs/DEMO.md) · [Final verified results](docs/FINAL_VERIFICATION.md). Feature freeze: no new Instagram functionality or performance changes. Full final-session browser acceptance is incomplete; see the verification record.

## Run

With Docker and Compose v2 running, from the repository root:

```sh
cp -n .env.example .env
```

Privately set `POSTGRES_PASSWORD` and the existing Meta `MODEL_API_KEY` in `.env`. Never commit credentials. Without a model key the UI and manual settings still work; inference reports an error and does not invent a result.

```sh
docker compose up --build -d --wait
```

Open **http://127.0.0.1:3000/overview**. Use `127.0.0.1` explicitly if an old native development service listens on IPv6 localhost. API docs: http://127.0.0.1:8000/docs.

Startup automatically applies Alembic migrations and idempotent fictional bakery seed data. Existing database configuration is never overwritten by startup. The PostgreSQL named volume survives normal restarts, rebuilds and `docker compose down`. Do not use `down -v` unless deliberately deleting the database. Keep independent backups.

Published ports bind to loopback by default. **Demo business switching is not tenant authentication.** Every database operation is scoped server-side, but any local caller can select a business. Do not expose this unauthenticated simulator publicly.

## Seller walkthrough

1. Click **New business** in the navigation. It starts paused and unpublished.
2. In **Business settings → Overview**, paste your business description or menu and click **Help me set up with Muse**.
3. Muse proposes sourced draft edits. It asks about ambiguous extra-charge units and missing service areas. Nothing becomes an active commercial rule yet. Expand setup evidence to inspect its source quotes.
4. Answer questions conversationally or edit **Products & Pricing**, **Customizations**, **Delivery & Availability**, **Payments & Policies**, **Agent Personality**, and **When to Notify Me**. Manual editing works without a model connection. Prices are whole INR amounts. For delivery, add explicit service-area keywords; the customer must provide an address containing an allowed area. This is a keyword check, not geocoding.
5. Save the draft, resolve setup questions, and open **Review & Publish**. Review prices, units, hours, fees, lead time, capacity, deposit and safety rules; check the review box and explicitly publish. Resume automation when ready.
6. Open **Conversations** and type as a synthetic customer. The agent reads the selected business's published configuration on every turn, with no server restart. Configuration edits remain draft until published.
7. Open **Scenario Lab**, choose a scenario, and inspect expected versus persisted outcomes, messages, reviews, errors and per-call timing. Each run copies the published configuration into an isolated lab business. Reset removes lab records only.

For Bloom & Co., enter the exact description in `backend/scripts/verify_bloom.py`. The original description leaves extra units, service area, hours, location and cancellation/safety policies incomplete. Supply those as seller decisions; for example, extras per bouquet, Indiranagar delivery, 24 hours' lead time, two orders/day, zero deposit and owner review for accepted changes. Do not silently fill those gaps.

Then request 12 red roses with ribbon and a greeting card, provide one bouquet, a future date and an Indiranagar address. The fixed breakdown is ₹699 + ₹50 + ₹30 + ₹80 = **₹859**. Accept with “Perfect, let's go ahead!” Publish ₹799 for the bouquet and request the same selection in a new conversation: **₹959**. The existing ₹859 commitment retains its original terms.

## Rules and persistence

- `businesses`: business profile/current published configuration, active version and pause state.
- `configuration_drafts`: validated editable configuration, optimistic revision, unresolved questions and sourced setup conversation.
- `configuration_versions`: immutable application-published snapshots keyed by business and version. Migration preserves the original M2 configuration as version 1.
- `conversations`, `messages`, `events`: business-owned sourced state and append-only history. Composite foreign keys and unique message IDs/positions prevent cross-business linkage and duplicate records.
- `orders`: atomic business-owned projection of requested, accepted and production specifications. The simulator supports one order per conversation.
- `instagram_accounts`, `instagram_inbox`, `instagram_outbox`, `instagram_replays`: account ownership, durable delivery/retry status, held replies and source-owned isolated replay mappings. Tokens remain runtime secrets; PostgreSQL stores references only.
- `scenario_runs`: business-owned lab results referencing separate isolated lab businesses. A lab business cannot be selected through normal customer API routes.

Catalogues, fees and policies use validated JSONB inside relational ownership/version tables. Supported rules are typed values, not executable code. Draft proposals require exact seller source quotes; numeric rules require matching evidence. Unknown fields, unsupported approval-rule types and invalid charges are rejected. Seller review is mandatory before activation.

Fixed price = configured variant price × quantity + selected extras × quantity + fulfillment fee. Extras may explicitly be per item or per numeric size unit. Fractional-rupee results require review. No discounts or negotiation. Capacity can count items or orders; **acceptance reserves capacity, quotes do not**. A PostgreSQL business-row transaction lock serializes all writers for that business across processes, including rechecks before acceptance. Concurrent requests cannot reserve the last slot twice.

New quotes record a configuration version and snapshot. Publishing invalidates pending quotes before they can be accepted, even if only policy changed. Accepted commitments and frozen production plans retain their historical prices/specifications; legacy M2 records retain their actual historical terms without invented configuration provenance. Historical evidence remains auditable after catalogue changes.

Payment assertions stay claimed/unverified. Acceptance never starts production. An explicit owner action starts simulated production. Late changes create a pending review and preserve that snapshot. Mandatory dietary, unsupported-request, accepted-change, dispute and exact-slot gates cannot be disabled. Sellers can additionally require approval for all orders. Other free-form escalation/cancellation guidance is displayed for the owner; it is not arbitrary executable policy.

Customer replies use approved fact-equivalent phrases; Muse cannot introduce unapproved claims. Writing failures use a validated deterministic fallback, labelled in seller audit details. Interpretation/setup failures save no inferred mutation. Normal automatic quotes and clarification create no owner alert.

## Scenario Lab

| Scenario | Persisted invariant |
|---|---|
| A — Changing requirements | Latest size/date/extras; obsolete quotes invalidated; final deterministic total accepted |
| B — Final capacity slot | Two concurrent acceptance writers; exactly one reservation and one escalation |
| C — Unauthorized request | No unauthorized commitment or overridden-price offer |
| D — Payment claim | Claim recorded; never verified |
| E — Late production change | Frozen production plan intact; one actionable owner review |
| F — Conditional acceptance | Conditional/free-extra request cannot accept |
| G — Duplicate / out-of-order delivery | One incoming turn; duplicate unchanged; stale input rejected |
| H — Catalogue changes mid-order | Old accepted terms preserved; new quote uses the published price |

Runtime runs use genuine Muse; errors remain errors. There is no canned model substitute. Mock providers exist only in automated tests and produce `mock` provenance. Scenario A requires two sizes plus eggless/floral options; use the demo bakery for that bakery-specific case. B visibly overrides the isolated copy to one daily slot. Other configured policies still apply and may cause an honest failure. Repeatable resets do not touch seller orders or published rules. Step tokens prevent duplicate step retries from advancing a run twice.

## Verify

Create a separate disposable test database once if needed:

```sh
docker compose exec -T db createdb -U orderguard orderguard_test
```

```sh
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg:///orderguard_test backend python -m pytest -q -p no:cacheprovider
```

```sh
cd frontend
npm run lint
npm run test:catalogue
npm run build -- --webpack
```

Opt-in actual Muse checks, using the private runtime key:

```sh
docker compose exec -T backend python scripts/smoke_meta.py --live
docker compose exec -T backend python scripts/verify_bloom.py --live
docker compose exec -T backend python scripts/verify_lab.py --live
```

`verify_bloom.py` creates a new synthetic florist, performs real sourced onboarding, explicit seller corrections/publishing, HTTP conversations, direct PostgreSQL verification, ₹859/₹959 price versioning, isolation and a real concurrent Lab B run. Its outage test is explicitly injected through FastAPI, followed by a real Muse retry. `--business <id>` continues an already published ₹699 florist. These tests leave inspectable synthetic records; use separate test businesses for repeated price-change runs. `verify_lab.py` supports A–H through the runtime frontend proxy; its default is A–F. Run G/H explicitly against a fully configured business. JSON evidence is saved under `/tmp` in the backend container; copy it out with `docker compose cp` if needed.

Timing: seller audit stores interpretation and reply-request durations and SQL execution timing through the decision. HTTP `Server-Timing` includes all measured SQL statements for the request, including saves/lock waits, but excludes network connection setup and commit overhead. The acceptance script measures complete client-observed HTTP duration and reports medians/maxima. Mock tests do not establish live performance.

See [M3_REPORT.md](M3_REPORT.md) for actual verification results, UI boundaries, failures and measured latency. Never infer success from the presence of a test script.

## Native development and portability

PostgreSQL is required; tests never substitute SQLite. With a private `backend/.env` based on its example:

```sh
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m app.bootstrap
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```sh
cd frontend
npm ci
cp -n .env.example .env.local
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Next.js forwards same-origin `/api` requests to runtime `API_INTERNAL_URL`; credentials never reach browser code. Docker images exclude `.env`, local SQLite files and caches. `DATABASE_URL` can target external PostgreSQL; the default Compose setup uses libpq runtime environment values. Set `ORDERGUARD_BUSINESS_ID` for the default workspace. `BIND_HOST`, `FRONTEND_PORT` and `BACKEND_PORT` control deliberate local bindings. Never share expanded `docker compose config` output because it contains secrets.

Existing SQLite files remain untouched. To explicitly import old synthetic records, copy the file into the backend and run the read-only atomic importer:

```sh
docker compose cp backend/data/demo.sqlite3 backend:/tmp/orderguard-legacy.sqlite3
docker compose exec -T backend python -m app.import_sqlite /tmp/orderguard-legacy.sqlite3
```

Matching records are skipped, conflicts abort the complete batch. Never run concurrent SQLite/PostgreSQL writers during an import. M2's startup, persistence, idempotency, rollback, concurrent writer and importer regressions remain in the backend suite.

## Boundaries

English replies, INR pricing and India-time date interpretation only. Hours are descriptive; exact slots always need human review. Service areas use explicit address keywords, not a real logistics connection. No real inventory/calendar or payment verification. One order per conversation. Custom automatic conditions beyond the supported typed rules and owner resolution of pending reviews are not implemented. Coarse business locks include model latency, so slow Muse calls serialize that business's turns. This is a local prototype, not authenticated multi-tenant hosting.

## Instagram adapter and demo package

Open `/channels` for honest status and signed synthetic replay. The webhook enqueues without calling Muse; the explicit inbox worker invokes the existing agent and stores a held reply. No runtime route automatically sends messages. Compose hard-disables outbound transport. OAuth, professional-account permissions, live webhook reception and remote revocation remain unverified/incomplete.

See [Instagram setup and boundary](docs/INSTAGRAM.md), [architecture](docs/ARCHITECTURE.md), [demo script](docs/DEMO.md), [progress log](PROGRESS.md) and [verification report](M3_REPORT.md).

```sh
docker compose exec -T backend python scripts/verify_instagram_replay.py --live --business YOUR_BLOOM_ID
docker compose exec -T backend python scripts/verify_lab.py --live --business YOUR_BLOOM_ID --scenarios GH
docker compose exec -T backend python scripts/compare_reasoning.py --live
```

The first command uses real Muse with **synthetic Instagram transport**, not a live Instagram connection. Outbound tests use mocked HTTP. The reasoning experiment is an opt-in comparison; defaults remain unchanged. Empty `MUSE_*_REASONING_EFFORT` settings preserve the working model default. Do not use unsupported `none`; see [Meta's reasoning documentation](https://dev.meta.ai/docs/reasoning).

Plain UTF-8 `.txt` menus up to 8 KB/8,000 characters are validated before being loaded into setup. Empty, oversized, binary, invalid UTF-8 and unsupported file formats are rejected. Uploading text never publishes it automatically.

Work stops after this M3/M4 adapter and demo preparation. No public deployment or submission was performed.
