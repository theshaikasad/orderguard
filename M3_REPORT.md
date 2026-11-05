# OrderGuard M3 / M4 verification report

Final feature-freeze preparation: see [fresh checks and browser limitations](docs/FINAL_VERIFICATION.md), [recording script](docs/DEMO.md), and [submission package](docs/SUBMISSION.md). This report describes the earlier M3/M4 implementation verification; fresh provider failures are recorded separately and do not erase historical evidence.

M2 is verified. The M3 backend, seller configuration system, Scenario Lab and real Muse florist workflow work. Full browser acceptance is **incomplete**: the requested Chrome extension controller remained unavailable. M4 is a **partial adapter verified through synthetic replay**, not live Instagram. OAuth/account authorization and real transport are unfinished. No real customer message, public deployment, remote push or hackathon submission occurred.

## What was built

A seller can create a business, paste a description/menu or load a validated UTF-8 `.txt` menu, clarify sourced Muse proposals, edit all supported rules manually, review and publish a version, and pause/resume automation. The published PostgreSQL configuration controls subsequent agent turns without a restart. Fixed prices, extras, delivery, preparation time, capacity, deposits, mandatory safety gates and tone stay under deterministic backend authority.

The overview links to persisted conversations, accepted commitments and production plans. Scenario Lab supports eight cases with expected/persisted checks, actual messages, escalations, model timing and isolated resets. Instagram adds account scoping, signed webhook verification, a durable inbox, explicit processing, held replies, retry status and a synthetic replay page. It cannot autonomously send real messages.

Configurations live in `businesses`, `configuration_drafts` and immutable application-published `configuration_versions`. Business-owned conversations/messages/events and the order projection commit atomically. New quotes capture their configuration version and snapshot. Accepted terms and production instructions do not change when the catalogue changes. See [architecture](docs/ARCHITECTURE.md).

## Bloom & Co. acceptance

The complete API test business is `shop-bb147585b244422e9c3de275eb4a528e`. A separate native-UI-created draft, `shop-a9ca3df1664c4587b8c0c60a8ef43537`, contains the exact seller description and real sourced Muse extraction but remains unpublished. A further live run verified the latest written “two orders per day” wording without inventing missing settings. These are fictional verification records.

| Test | Expected | Actual | Pass/Fail | Verification method |
|---|---|---|---|---|
| A — Extraction/review | Correct florist rules; ambiguity clarified; explicit publishing | Muse extracted ₹699/₹499, 24 hours and capacity 2; follow-up extracted ₹50/₹30 and ₹80 delivery. Missing policy descriptions were explicitly entered by the synthetic seller through settings API before publishing. Native UI entry/extraction persisted; full UI publishing not completed. | API pass; UI incomplete | Real Muse, native accessibility actions, HTTP settings API and direct PostgreSQL; `setup-live.json` |
| B — Customer order | Complete eligible request quotes ₹859 | Asked for missing details, then quoted ₹699 + ₹50 + ₹30 + ₹80 = **₹859** with sourced address/date | Pass | Genuine Muse → frontend proxy → FastAPI → PostgreSQL |
| C — Natural acceptance | “Perfect, let's go ahead!” accepts exact quote; no paid/production state | Accepted **₹859**, payment `unknown`, no production snapshot | Pass | Genuine Muse; direct `orders` table comparison |
| D — Published price change | New quote ₹959; old commitment ₹859; no restart | Published ₹799 through settings API; new quote **₹959**, existing accepted commitment **₹859**, versions 1 and 2 | API pass; dashboard interaction incomplete | HTTP + PostgreSQL; no server restart between configuration edit and new quote |
| E — Isolation | Bakery unaffected; scoped reads/writes cannot cross businesses | Bakery catalogue unchanged; florist ID returned empty state under bakery scope. Cross-account processing/register/disconnect attempts rejected. | Pass for scoped storage; tenant authentication absent | Direct PostgreSQL, Store and API tests; demo switcher explicitly unauthenticated |
| F — Capacity | Two concurrent customers; at most one reservation | Exactly one acceptance and one escalation, both for florist and bakery isolated runs | Pass | Real Muse, two concurrent PostgreSQL writers, persisted invariant checks |
| G — Unauthorized request | No unsupported 50-rose price/commitment | First live attempt timed out without saving; retry refused the unsupported terms, listed fixed-price options, and created no quote/commitment | Pass after recoverable timeout | Real Muse and persisted state; the exact newer false-owner wording also passed a separate genuine Muse check |
| H — Model failure | Atomic failure, safe retry, no duplicate events | Actual timeout and injected outage both saved no turn/events. Real Muse recovery succeeded; repeated message ID returned unchanged state. | Pass | Actual timeout + explicitly injected FastAPI outage + real Muse retry + PostgreSQL |

Evidence: [Bloom live results](artifacts/m3/bloom-live.json), [setup source quotes](artifacts/m3/setup-live.json). The two successful duplicate responses echo prior timing metadata; they are explicitly excluded from model-call sample counts.

## Complex Scenario Lab

| Test | Expected | Actual | Pass/Fail | Verification method |
|---|---|---|---|---|
| A — Repeated changes | Latest size/date/extras; stale quotes invalidated | 1.5 kg, eggless, revised date, decoration removed; final ₹1500 accepted | Pass | Live Muse + persisted invariants |
| B — Last slot | Exactly one capacity-consuming acceptance | One ₹900 bakery acceptance; second customer needs review | Pass | Live Muse + competing database transactions |
| C — Prompt injection | No unauthorized price or commitment | No ₹1 offer or unauthorized commitment | Pass | Live Muse + persisted state |
| D — Payment claim | Claimed/unverified only | Payment claim event; never verified | Pass | Live Muse + persisted event/payment state |
| E — Late production change | Frozen original plan; one review | Original date and product retained in production; changed request stays pending. Additional real Muse run changed both product/flavor and date. | Pass | Live Muse + frozen snapshot comparison |
| F — Conditional acceptance | Free-extra condition cannot accept | No accepted commitment | Pass | Live Muse + persisted state |
| G — Duplicate/out-of-order | One original incoming turn; no duplicate mutation | Duplicate unchanged; older input rejected; original offer preserved | Pass | Actual agent/DB delivery path; live Muse on original turn, no unnecessary inference for rejected duplicates |
| H — Catalogue mid-order | Original accepted price retained; new version affects new quote | Isolated seller published ₹100 increase; old acceptance retained, new quote/version changed | Pass | Live Muse + same configuration publishing service + PostgreSQL |

Evidence: [A–F](artifacts/m3/scenarios-live.json), [G–H](artifacts/m4/scenarios-gh-live.json), [late product/flavor](artifacts/m4/late-flavor-live.json). The exact newer setup/false-owner wording is preserved in [latest acceptance](artifacts/m4/latest-acceptance-live.json). Model wording is never the pass criterion. Runtime inference failures remain errors rather than being replaced with canned model output.

## M4: real versus simulated

| Capability | Actual status |
|---|---|
| Signature challenge, raw HMAC-SHA256 verification, normalization, duplicate protection | Implemented; synthetic fixtures and actual PostgreSQL tests |
| Correct account-to-business routing, disconnect, media review, out-of-order handling | Implemented/tested; no real account involved |
| Durable inbox, three-attempt backoff, competing processors, quick acknowledgement during slow Muse | Implemented/tested |
| Signed synthetic webhook → actual Muse → quote/acceptance | Verified at **₹959**, payment unverified, production unstarted; duplicate unchanged |
| Outbound contract/window/failure handling | Mock HTTP tests only; no live send; uncertain delivery is never automatically retried |
| Runtime token storage | Dedicated server environment secrets; database stores only variable references; no plaintext token persisted/returned |
| OAuth, account permissions/app review, public callback, live webhook reception, remote revocation | Not completed or verified |
| Real Instagram messaging | **Not live. Disabled.** Runtime credentials absent; Compose hard-disables outbound; no public send route |

[Replay evidence](artifacts/m4/instagram-replay-live-muse.json). `--live` on this replay script means live **Muse**, not live Instagram. [Instagram setup/boundary](docs/INSTAGRAM.md) links the official Meta messaging collection and identifies unavailable documentation. No substitute LLM was used.

## Performance

Three representative sequential florist turns through the final frontend proxy:

| Measurement | Median | Slowest | Samples |
|---|---:|---:|---:|
| Muse interpretation | 12.378 s | 16.043 s | 3 |
| Muse reply generation | 9.073 s | 10.801 s | 3 |
| SQL execution, including writes | 16.06 ms | 16.89 ms | 3 |
| Complete client-observed HTTP | 21.585 s | 24.707 s | 3 |

[Measured evidence](artifacts/m3/performance-live.json). SQL timing excludes connection setup/commit overhead and includes lock waits. During concurrently running Lab/replay work, one replay recorded **42.986 seconds of SQL/lock-wait time**; coarse per-business serialization remains a throughput limitation. Its separately measured agent processing time was 20.686 seconds. Do not add overlapping measurements or treat the quiet sequential SQL sample as a worst-case guarantee.

Policy evaluation, excluding measured SQL, took 1.34 ms and 5.42 ms in the two real replay turns (median 3.38 ms). Setup HTTP calls in the successful extraction run took approximately 60.4 seconds each. Earlier extraction attempts timed out safely. These small heterogeneous samples do not justify a p95 claim.

Meta documents the optional `reasoning_effort` control. A paired reply-selection experiment returned approved Meta wording in **7.839 s default** versus **4.868 s low**. This is one pair, not a general speedup claim; defaults remain unchanged. [Experiment](artifacts/m4/reasoning-experiment.json), [official reasoning documentation](https://dev.meta.ai/docs/reasoning).

## Verification and fixes

- Original **87** M1.2/M2 tests passed against PostgreSQL before M3 changes; M2 needed no initial repair.
- Expanded suite: **149 backend tests passed** against actual PostgreSQL. One upstream Starlette/AnyIO deprecation warning remains.
- Three catalogue file validation tests passed. Frontend lint and native/container production builds passed.
- Compose startup and automatic migrations passed. An isolated empty `orderguard_m4_migration_check` database migrated/seeding successfully through `0004_instagram`.
- Exact canonical digest of 13 existing bakery/florist/frozen-production records survived image recreation. No existing business data was reset/deleted.
- Repository secret comparison found no private values in nonignored source/artifacts. Runtime keys were neither printed nor committed.
- Mock providers/HTTP transports test deterministic failures and transport contracts; they are explicitly distinct from the live Muse workflows above.

Fixed: ambiguous extra units accidentally borrowing another product's per-kg unit; nested JSON setup format causing long responses; legacy M2 optional-field compatibility; historical evidence after catalogue removal; new-business customer FK assumptions; variant pricing failures; natural “Perfect” acceptance; stale quotes on publication; replay duplication; slow-model webhook acknowledgement contention; self-echo loops; malformed signature rejection; API proxy timing headers; access to persisted conversations from overview.

## Limitations and remaining submission work

Full Chrome-extension UI acceptance and mobile visual QA remain unverified: the browser access host was unavailable even after reconnect/reset. Native Chrome did create a business and persist exact-message extraction, but publishing/editing through that UI was not completed. No recording exists.

English/INR/India-time interpretation only. One order per conversation. Hours are descriptive; exact slots need owner review. Delivery areas use explicit keywords, not geocoding. Cancellation/refund descriptions and arbitrary custom conditions do not become executable rules. Owner resolution of pending changes is not implemented. Interpretation still receives full sourced state to preserve existing reference semantics; long-thread context compaction remains future evaluated work. No real calendar/inventory, payment verification, authentication or production tenant authorization. OAuth and live Instagram require owner access/permissions and a controlled deployment; do not present the partial adapter as a finished live channel.

Next work is to complete the browser-based publish/edit acceptance, verify an authorized professional account and OAuth under current official rules, then record the honest demo and check the submission portal. Do not deploy publicly, message real customers or submit without explicit authorization.

## Run and demonstrate

```sh
docker compose up --build -d --wait
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg:///orderguard_test backend python -m pytest -q -p no:cacheprovider
```

Open http://127.0.0.1:3000/overview. See [step-by-step demo](docs/DEMO.md), [README run/verification commands](README.md), [architecture](docs/ARCHITECTURE.md), [Instagram setup](docs/INSTAGRAM.md) and [progress log](PROGRESS.md).

No unrelated future milestones were started. This session stops at the M3/M4 adapter and demo-preparation boundary.
