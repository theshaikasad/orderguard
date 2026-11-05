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

149 backend tests passed against PostgreSQL; frontend lint, all three catalogue tests and production build passed. Compose rebuild/start succeeded with all services healthy and loopback-bound. Tests include mocked failure/transport contracts; those do not establish live Instagram capability. Full final-session browser acceptance remains incomplete.

Limits: no authenticated tenant boundary, live Instagram/OAuth, payment verification, real inventory/calendar or owner resolution of pending reviews. One order per conversation; English/INR/India-time only; delivery uses keywords and exact slots require review. Model waits and coarse per-business locking limit throughput. Historical representative customer median is 21.585 seconds (three samples), not an SLA. No performance changes were made during freeze.

## Links and repository status

- Configured Git remote: `git@github.com:theshaikasad/orderguard.git`.
- Corresponding repository URL: https://github.com/theshaikasad/orderguard. Authenticated GitHub CLI confirmed **PRIVATE**, default branch `main`; anonymous web lookup returned 404. Judge access is not established. Current working code must be pushed only after owner authorization.
- Local app: http://127.0.0.1:3000/overview (not judge-accessible hosting).
- Demo video: **not recorded/uploaded; no link available**.
- Public deployment: none. Do not put a localhost URL in a field that expects a hosted demo.

## Official instructions checked

On November 5, 2026, the [official Meta event page](https://dev.meta.ai/events/global-hackathon) and [Cerebral Valley event page](https://events.cerebralvalley.ai/e/meta-ai-developer-hackathon) still stated November 4 at 9 PM Eastern for project submissions: **November 5, 7:30 AM IST / 02:00 UTC**. Indie judging emphasizes creativity, technical ambition and whether it works.

The candidate [participant submission route](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit) returned public event content to the web reader, not authenticated form fields. Exact required fields, link visibility, licensing/repository requirements and video length were not independently verified. Use the accepted participant dashboard/rules and organizer announcements as authority. Do not infer submission rules from this preparation checklist or from the application's demo target.

## Owner's final checklist

- [ ] Open the accepted participant dashboard now; confirm deadline, required fields/artifacts and any repository/license/video constraints.
- [ ] Complete remaining UI checks in [DEMO.md](DEMO.md), especially publishing and a narrow viewport.
- [ ] Record the 2–3 minute walkthrough with actual Muse calls; disclose shortened waits, simulated customers and any reply fallback.
- [ ] Upload the recording and verify its link opens without an access request; add that actual link to the form.
- [ ] Review the local commit and secret scan. Authorize/push using the commands below. Check the remote contains this commit and judges have the required repository access. Verify any license requirement before selecting a license.
- [ ] Paste the description above; include honest limitations and actual evidence links. Omit unavailable deployment links.
- [ ] Reopen every submitted URL as a judge would, review the completed form and submit personally before **7:30 AM IST**.
- [ ] Save the submission confirmation/receipt and timestamp. A filled draft is not a submission.

## Push commands — owner action only

Run from the repository root **after authorizing the push**:

```sh
git status --short
git log -1 --oneline
git remote -v
git push --dry-run origin main
git push -u origin main
```

Use a normal push only; if rejected, inspect the divergence instead of force-pushing. No remote fetch, push, repository visibility change, deployment, upload or submission was performed by this preparation task. SSH access and remote branch compatibility must be checked at push time. Source commit details are in the final handoff; test outcomes apply to the frozen source.
