# Recording demo verification — November 5, 2026

Implemented only the requested customer/seller recording polish. No provider, pricing, acceptance, production or Instagram transport rules were replaced.

## Checks actually performed

- PostgreSQL backend regression suite: **151 passed**, 69.43 seconds. One upstream Starlette/AnyIO deprecation warning.
- Frontend ESLint: **passed** after fixing the browser-storage hydration effect.
- Frontend catalogue tests: **3 passed**. Node reported existing experimental type-stripping/module-format warnings.
- Next.js production builds: **passed**, including both dedicated demo routes; TypeScript `--noEmit` also passed.
- Local backend/frontend Docker builds and Compose health checks: **passed**. Existing PostgreSQL volume retained.
- Real HTTP rehearsal through the frontend proxy: **all four steps passed**, including direct PostgreSQL comparisons and subsequent HTTP reads. All interpretation and reply sources were `meta`; no checked fallback was used. Durations: **26.78, 21.40, 22.21, 17.89 seconds**.
- Real Safari desktop rehearsal in **two separate normal windows**: fresh synthetic conversation, customer composer send, actual waiting state, ₹900 chocolate quote, ₹1,300 customization quote, natural acceptance, unsupported pistachio change, owner alert and preserved ₹1,300 commitment. Seller updated without manual refresh during the flow. Both windows displayed the same messages.
- After the browser-submitted flow, direct PostgreSQL and frontend-proxy reads agreed: eight persisted turns, four real Muse replies, no active unsupported quotation, owner review required, accepted chocolate/eggless/floral terms intact, payment unverified and no production snapshot.
- Seller reload after rebuilding/restarting the local services restored the same final messages, alert and accepted commitment. No seller/test records were reset.
- Final recording build visually inspected in Safari, including visible chat bubbles and the owner alert. **Fresh demo** then switched both existing windows to the same empty conversation without reloading the seller. A direct database check confirmed that the completed rehearsal and its accepted commitment were still present. Both windows were left ready for a new recording.

Evidence: [HTTP rehearsal](../artifacts/demo-polish/live-http.json) and [browser-submitted final persisted state](../artifacts/demo-polish/browser-final-state.json). These contain fictional data only.

The browser-extension access host was unavailable. Native Chrome returned a blank capture surface. Native Safari was successfully used instead; intermittent foreground/capture errors were retried, not counted as product success. Mobile breakpoints are implemented but were not exercised on a real phone. No public service, live Instagram account, real payment, OAuth, remote push or deployment was tested or performed as part of this recording task.

## Files changed

- `frontend/app/demo/customer/page.tsx`, `frontend/app/demo/seller/page.tsx`: dedicated routes and distinct window titles.
- `frontend/components/DemoWorkspace.tsx`, `frontend/components/demo.css`: recording UI, real pending state, safe retries, shared session selection and one-second persisted-state polling.
- `frontend/components/OrderDetails.tsx`, `frontend/app/page.tsx`: share the existing dashboard’s order facts/quote rendering with the seller demo.
- `frontend/app/api/[...path]/route.ts`: allow the fresh-session proxy endpoint.
- `backend/app/main.py`, `backend/tests/test_recording_demo.py`: atomic isolated session creation using existing catalogue values; regressions for isolation, preservation and paused automation. Recording workspaces stay out of the ordinary seller selector.
- `backend/scripts/verify_recording_demo.py`: opt-in real Muse rehearsal with persisted-state assertions.
- README, recording instructions, verification evidence and this report.

Exact startup, test commands, messages and three-minute recording sequence are in [RECORDING_DEMO.md](RECORDING_DEMO.md). The film was produced from these recordings: [MP4](../artifacts/orderguard-hackathon-demo.mp4), [subtitles](../artifacts/orderguard-hackathon-demo.srt), [provenance and technical verification](../artifacts/video-evidence/README.md). No additional product milestone was started.
