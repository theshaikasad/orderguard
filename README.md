# OrderGuard

Turn messy customer conversations into reliable orders. The fictional Little Crumb bakery uses real Meta Muse interpretation and checked, friendly reply composition, with deterministic fixed prices and explicit acceptance. **M2 adds PostgreSQL persistence and portable Docker deployment.** No Instagram, onboarding, authentication or payment processor is connected.

## Start with Docker

Install Docker with Compose v2 and start its engine. From the repository root:

```sh
cp -n .env.example .env
```

Privately set a strong `POSTGRES_PASSWORD` and your existing Meta `MODEL_API_KEY` in `.env`. Do not paste credentials into chat or commit them. The app starts without a model key, but interpretation correctly returns an error rather than pretending to call Muse.

```sh
docker compose up --build
```

Open http://localhost:3000. API docs: http://localhost:8000/docs. To start in the background and wait for health checks:

```sh
docker compose up --build -d --wait
```

Startup waits for PostgreSQL health, runs **Alembic migrations and an idempotent fictional seed**, starts FastAPI, then starts Next.js. No manual table creation is required. Migration startup is guarded by a PostgreSQL advisory lock, including concurrent backend startups.

The first build downloads base images and pinned dependencies, so it requires registry access. Python dependencies are locked in `backend/requirements.lock`; npm uses its existing lockfile. Docker uses a pinned uv installer and a cached npm install with bounded download retries. Images run the app as non-root users. No `.env`, local database, Git directory, dependency cache or API key is copied into an image.

## What runs where

| Component | Responsibility | Default access |
|---|---|---|
| Next.js container | Existing seller workspace and customer simulator; runtime API proxy | localhost:3000 |
| FastAPI container | Unchanged Muse/policy/pricing/acceptance behavior; transactional storage | localhost:8000 |
| PostgreSQL container | Durable conversations, messages, customers, state and audit records | Internal Compose network only |
| Meta Model API | Real Muse interpretation and checked reply composition | Outbound HTTPS from backend |

Docker packages the application and its runtime dependencies. PostgreSQL is the database that stores the application’s records. On a laptop, these containers run in Docker’s local engine. On a server, the same compatible images run in that server’s container engine; Muse still runs at Meta, not on that server.

The frontend browser uses same-origin `/api/...` requests. Next.js forwards approved routes to **runtime** `API_INTERNAL_URL` (default `http://backend:8000` in Compose). The backend address and model key are never bundled into browser JavaScript. Changing the backend hostname does not require rebuilding the frontend image. A legacy `NEXT_PUBLIC_API_BASE_URL` build-time override remains supported for existing development setups, but is unnecessary for Docker.

## Persistence and consistency

SQLAlchemy 2 connects through psycopg 3 to PostgreSQL. There was no pre-existing SQLAlchemy layer; M1.2 used a single SQLite snapshot table. Alembic revision `0001_postgres` now creates:

- `businesses`: business ID and validated catalogue/policies in JSONB. The existing bakery catalogue is seed data, inserted only if absent; restart never overwrites approved database configuration.
- `customers`: the two explicitly fictional customer identities. Known simulator conversations link to them. Unknown conversation IDs have no invented customer identity.
- `conversations`: business-scoped IDs, optional customer link, version, and the complete sourced JSONB state. Requested specifications, current quote, accepted commitment, frozen production snapshot, alerts, evidence and inference provenance round-trip unchanged.
- `messages`: separately indexed incoming, outgoing and owner turns, with unique IDs and ordered positions within a conversation.
- `events`: separately indexed, ordered audit records including evidence and historical snapshots.

Messages/events and the state snapshot are saved in **one transaction**. Foreign keys prevent orphan records; composite primary keys and unique positions prevent duplicate deliveries and ordering collisions. Existing messages/events cannot be rewritten through the store. Direct stale writes return 409 rather than overwriting a newer state.

A transaction locks the configured **business row** before loading a conversation, calling Muse, checking capacity and saving. This replaces the old in-process lock and protects shared capacity across independent backend processes. Duplicate requests wait, then return existing state without another model call or reply. The lock is deliberately coarse: all customer turns for one business are serialized, including the two model calls. This preserves prototype correctness rather than introducing queues or distributed orchestration.

All queries and locks are scoped by `ORDERGUARD_BUSINESS_ID`. This prepares configuration separation; it is **not** multi-tenant authentication. A deployment serves one configured business, and no client header can choose another business. Reset deletes only that business’s simulated conversations/messages/events, not its catalogue or other businesses.

## Restarts, backups and existing SQLite data

PostgreSQL data lives in the named `postgres_data` volume. Container restart, image rebuild, `docker compose down`, and normal container recreation preserve it. **Deleting the volume or using `docker compose down -v` deletes that database.** A volume is persistence, not a backup. Maintain separate PostgreSQL backups before important use or schema changes.

Existing SQLite files are never deleted or automatically mounted into images. To import the old synthetic workspace after stopping the old local backend:

```sh
docker compose cp backend/data/demo.sqlite3 backend:/tmp/orderguard-legacy.sqlite3
docker compose exec -T backend python -m app.import_sqlite /tmp/orderguard-legacy.sqlite3
```

The importer opens SQLite read-only, validates all snapshots and imports the entire batch in a PostgreSQL transaction. It preserves names where known, IDs, source ordering/timestamps, messages, requested/quoted/accepted/production states, legacy commercial terms, events and evidence. Matching destination records are skipped on repeated import. Any conflicting destination snapshot aborts the entire batch; nothing is silently overwritten. Keep the original file as a rollback reference. Do not run SQLite and PostgreSQL app instances as concurrent writers during migration.

## Configuration and server portability

Root `.env` is for Compose interpolation; credentials are passed only at container runtime. Changing it requires recreating the affected container (`docker compose up -d`), not rebuilding an image. Never run `docker compose config` without `--quiet` when sharing logs: the expanded configuration contains runtime secrets.

- `POSTGRES_PASSWORD`: required for the Compose database. Changing it in `.env` does not rotate the password already stored inside an existing database volume; use an explicit database credential-rotation procedure instead.
- `MODEL_API_KEY`: backend-only Meta credential; no replacement provider or fake inference.
- `ORDERGUARD_BUSINESS_ID`: defaults to `little-crumb-v1`; scopes catalogue/state/customer records and locks. The fictional seed is cloned only for an absent configured business.
- `DATABASE_URL`: optional full SQLAlchemy PostgreSQL URL for an external database. By default Compose uses libpq’s `PGHOST`/`PGUSER`/`PGDATABASE`/`PGPASSWORD` runtime variables, avoiding password interpolation into a URL. Full external URLs can include PostgreSQL SSL options.
- `API_INTERNAL_URL`: runtime frontend upstream; defaults to `http://backend:8000`.
- `BIND_HOST`, `FRONTEND_PORT`, `BACKEND_PORT`: default to `127.0.0.1`, `3000`, `8000`. Alternate ports can be supplied when existing local services occupy these ports.
- `CORS_ORIGINS`: needed only for direct browser-to-backend use; the normal same-origin proxy avoids cross-origin configuration.

The same images can run locally or on a server with suitable environment, storage and network configuration. Build/publish for the server’s CPU architecture; this session verifies the local ARM64 images, not an AMD64 or multi-architecture registry release. No server was provisioned or publicly deployed. Published ports bind to loopback by default because this simulator has no authentication. Put it behind appropriate private access/TLS controls before deliberate server exposure; M2 does not implement those controls.

## Develop without application containers

Use an existing PostgreSQL database and a server-only `backend/.env` based on its example:

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

The frontend proxy defaults to `http://127.0.0.1:8000` in native development. Backend `.env` loading remains an absolute path; fully restart after editing credentials. `ORDERGUARD_DB` is no longer a runtime store setting. Migration changes use `backend/alembic/versions`; direct Alembic commands run from `backend/` with the configured PostgreSQL URL. Application behavior remains in the existing engine/provider/reply modules.

## Verify

Create a separate test database once:

```sh
docker compose exec -T db createdb -U orderguard orderguard_test
```

Run all backend tests against real PostgreSQL (the test fixture uses temporary business IDs and cleans up only those records):

```sh
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg:///orderguard_test backend python -m pytest -q -p no:cacheprovider
```

Native tests require `TEST_DATABASE_URL` explicitly. They fail rather than silently substituting SQLite. Do not point tests at a production database. No existing M1.2 regression was removed; storage fixtures now use PostgreSQL and catalogue-change tests target the same store configuration used by runtime requests.

```sh
cd frontend
npm run lint
npm run build -- --webpack
```

Docker builds use the same webpack command. Default Turbopack was previously blocked by an internal-port sandbox restriction; no UI redesign or frontend dependency upgrade was introduced.

Opt-in real Muse checks:

```sh
docker compose exec -T backend python scripts/smoke_meta.py --live
docker compose exec -T backend python scripts/verify_live_flow.py --live
docker compose exec -T backend python scripts/verify_portable.py --live
```

Smoke makes two real calls (interpretation and reply composition). Full flow exercises the existing M1.2 sequence, compares HTTP state to PostgreSQL, checks duplicate handling and frozen production. These checks require the private key/access/quota and leave synthetic audit records. Normal model writing failures use the existing validated fallback; interpretation failures save no turn and can be retried with the same ID.

M2 verification completed locally on November 5, 2026:

- **87 backend tests passed in the final Python 3.12 container against actual PostgreSQL 16**, including all 77 M1.2 regressions. One upstream Starlette/AnyIO deprecation warning remains. New checks cover clean Alembic initialization, idempotent seed, state/message/event round-trips, conversation/business isolation, unique message IDs, stale writes, append-only history, rollback, concurrent duplicate calls, competing capacity reservations and atomic/idempotent SQLite import.
- **Frontend lint passed natively; webpack builds passed both natively and inside the image build.**
- **Compose startup passed** on ports 3000/8000, with all three services healthy. Database schema and seed were created automatically on the initially empty named volume. The first build attempts hit registry/network failures; the final uv/locked Python and cached, bounded npm builds succeeded.
- **All seven legacy SQLite conversations imported and matched HTTP responses through the Next.js proxy**, including accepted commitments, production snapshots, messages, events and evidence. Repeated import added zero records. Original SQLite SHA-256 remained `76a91b03fc9fc6812e63e5d21027a020ae39d4383034bf7fd3578ccde6591308`.
- **Real Muse smoke passed inside Docker** for both interpretation (`source=meta`) and checked reply composition (`reply_source=meta`). The existing private key was passed at runtime and never printed or committed.
- **Actual portable HTTP workflow passed** through `http://frontend:3000` → FastAPI → Muse → PostgreSQL in conversation `m2-live-05afb4567e`: ₹900 quote → eggless/floral ₹1300 → natural “I confirm” acceptance → unchanged duplicate → explicit owner production snapshot. Every response matched PostgreSQL; all actual model turns and replies reported Meta provenance. No payment was verified or production automatically scheduled.
- **All containers, including PostgreSQL, were force-recreated against the same volume**. All eight conversation states matched the canonical pre-recreation snapshot exactly; the live ₹1300 accepted/production plan survived. Health checks passed again, and the final PostgreSQL test suite remained green.

Not verified: public/cloud deployment, other CPU architectures, a multi-architecture registry release, operational backup restoration, failover or production security. No server was provisioned or exposed publicly. Mock-provider tests validate rules, not real inference; actual PostgreSQL tests validate database behavior, not a production deployment.

## Unchanged agent behavior and remaining limits

Fixed pricing: configured size price × quantity + selected per-cake extras × quantity + applicable fulfillment fee. No discounts or counteroffers. Muse interprets intent; the backend alone authorizes prices/actions. Muse composes from approved phrase variants; complete output validation rejects unapproved claims and uses a checked deterministic fallback on writing failure.

Natural acceptance must bind to the exact current valid quote, with no simultaneous changes or conditions. Acceptance never verifies payment or starts production. Accepted/production changes, dietary uncertainty and unsupported requests require review. IDs/evidence stay under the existing seller audit details. The static M0 `/fixtures` route remains visibly seeded and unchanged.

Still simulated: customers, business catalogue, capacity and owner production actions. Still absent: real calendar/inventory, verified payments, Instagram, onboarding, authentication, media extraction and owner review resolution. One order per conversation; pending reviews require reset. Two serial Muse calls plus the coarse business lock limit throughput. Broader model semantics, public access/security, operational backups, cloud hosting, failover and server/architecture-specific deployment remain outside this verification.

Relevant implementation: `backend/app/database.py`, `store.py`, `bootstrap.py`, `import_sqlite.py`, Alembic, transaction wiring in `main.py`/`engine.py`, PostgreSQL tests, both Dockerfiles, `compose.yaml`, `.dockerignore`, frontend runtime proxy and standalone configuration. Muse provider/reply logic, fixed prices, acceptance decisions and UI styles are unchanged.

M2 stops here. The next recommended milestone is the separately requested M3 scope; no M3/M4 work has begun.
