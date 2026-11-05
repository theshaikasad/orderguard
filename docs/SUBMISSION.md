# Submission handoff

## Copy-ready entry

**Project:** OrderGuard
**Tagline:** Configure once. Automate routine sales. Escalate genuine exceptions.
**Track / theme:** Indie Developer / Build for Your World

**Description:** OrderGuard is a configurable AI sales and order-operations agent for small Instagram-first businesses. Owners lose time answering repetitive questions, calculating custom quotes and reconciling changing requests. A conversational mistake can become a costly commitment.

Owners teach OrderGuard their menu and policies in natural language. Meta Muse Spark extracts sourced draft rules, which the owner reviews and publishes. Muse then interprets customer messages and selects friendly, validated replies. Deterministic backend rules calculate fixed prices, recheck capacity and authorize commitments; the model cannot invent commercial authority.

OrderGuard goes beyond chat by maintaining separate customer requests, current quotes, accepted commitments and frozen production plans, with message evidence and versioned business configurations. A catalogue update affects future quotes without rewriting accepted orders. PostgreSQL transactions protect capacity across concurrent customers. Routine clarification and eligible quotes stay automatic; consequential exceptions create owner alerts.

The demonstrated florist workflow quotes and accepts ₹859, then quotes ₹959 after a published price change while preserving the original ₹859 commitment. Scenario Lab exercises late production changes, competing capacity, payment claims, prompt injection, conditional acceptance, duplicates and catalogue revisions using real Muse inference and persisted invariant checks.

This is a local prototype with synthetic customer conversations. The Instagram adapter supports signed synthetic replay, but live Instagram messaging, OAuth and payment verification are not connected.

## Technical innovation / Meta usage

- **Real Meta model:** server-side `muse-spark-1.3` via Meta Model API. Schema-validated interpretation and sourced onboarding proposals; separate reply selection from backend-approved, fact-equivalent wording.
- **Bounded authority:** deterministic fixed-price arithmetic and policy gates; natural acceptance must match the current valid quote. AI inference alone cannot verify payment, reserve capacity or start production.
- **Durable operations:** Next.js, FastAPI/Pydantic, SQLAlchemy, PostgreSQL and Alembic; atomic message/event/order persistence, duplicate protection, business transaction locks and configuration snapshots.
- **Inspectable evaluation:** isolated Scenario Lab uses actual model calls; checks saved commitments and production instructions rather than matching reply wording. Mocked providers are confined to tests. Reply failure may use a visibly audited deterministic fallback.

## Evidence and limitations

Final fresh commands/results: [FINAL_VERIFICATION.md](FINAL_VERIFICATION.md). Historical real-model evidence and eight scenarios: [M3_REPORT.md](../M3_REPORT.md), [artifacts/m3](../artifacts/m3), [artifacts/m4](../artifacts/m4). Architecture: [ARCHITECTURE.md](ARCHITECTURE.md).

151 backend tests passed against PostgreSQL; frontend lint, all three catalogue tests and production build passed. Compose rebuild/start succeeded with all services healthy and loopback-bound. Tests include mocked failure/transport contracts; those do not establish live Instagram capability. Full final-session browser acceptance remains incomplete.

Limits: no authenticated tenant boundary, live Instagram/OAuth, payment verification, real inventory/calendar or owner resolution of pending reviews. One order per conversation; English/INR/India-time only; delivery uses keywords and exact slots require review. Model waits and coarse per-business locking limit throughput. Historical representative customer median is 21.585 seconds (three samples), not an SLA. No performance changes were made during freeze.

## Links and repository status

- Configured Git remote: `git@github.com:theshaikasad/orderguard.git`.
- Corresponding repository URL: https://github.com/theshaikasad/orderguard. Authenticated GitHub CLI confirmed **PRIVATE**, default branch `main`; anonymous web lookup returned 404. Judge access is not established. The current working tree is pushed to `origin/main`; the repository was not made public.
- Local app: http://127.0.0.1:3000/overview (not judge-accessible hosting).
- Demo video: **recorded locally, not uploaded**. [orderguard-hackathon-demo.mp4](../artifacts/orderguard-hackathon-demo.mp4) is 2:45, 1080p, with burned-in and sidecar captions; provenance is in [video-evidence](../artifacts/video-evidence/README.md). Upload it and add the actual hosted link to the form.
- Public deployment: none. Do not put a localhost URL in a field that expects a hosted demo.

## Official instructions checked

On November 5, 2026, the [official Meta event page](https://dev.meta.ai/events/global-hackathon) and [Cerebral Valley event page](https://events.cerebralvalley.ai/e/meta-ai-developer-hackathon) still stated November 4 at 9 PM Eastern for project submissions: **November 5, 7:30 AM IST / 02:00 UTC**. Indie judging emphasizes creativity, technical ambition and whether it works.

The candidate [participant submission route](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit) returned public event content to the web reader, not authenticated form fields. Exact required fields, link visibility, licensing/repository requirements and video length were not independently verified. Use the accepted participant dashboard/rules and organizer announcements as authority. Do not infer submission rules from this preparation checklist or from the application's demo target.

## Owner's final checklist

- [ ] Open the accepted participant dashboard now; confirm deadline, required fields/artifacts and any repository/license/video constraints.
- [ ] Complete remaining UI checks in [DEMO.md](DEMO.md), especially publishing and a narrow viewport.
- [x] Record the 2–3 minute walkthrough with actual Muse calls; shortened waits and simulated customers are disclosed. See [the film](../artifacts/orderguard-hackathon-demo.mp4).
- [ ] Upload the recording and verify its link opens without an access request; add that actual link to the form.
- [x] Review the local commit and secret scan. The working tree is pushed to the configured remote. Confirm judges have the required repository access and verify any license requirement before selecting a license.
- [ ] Paste the description above; include honest limitations and actual evidence links. Omit unavailable deployment links.
- [ ] Reopen every submitted URL as a judge would, review the completed form and submit personally before **7:30 AM IST**.
- [ ] Save the submission confirmation/receipt and timestamp. A filled draft is not a submission.

## Push record

The owner requested and authorized a push on November 5, 2026. The current `main` was pushed to the configured origin after a clean working-tree check and secret review. No repository visibility change, deployment, upload or hackathon submission was performed. If a later push is rejected, inspect the divergence instead of force-pushing; test outcomes apply to the frozen source.
