# Live customer / seller recording

[Actual verification results and boundaries](RECORDING_VERIFICATION.md).

From the repository root, with the existing private environment already configured:

```sh
docker compose up --build -d --wait
```

Open two normal windows in **the same browser/profile**, using the exact same host:

- Customer: http://127.0.0.1:3000/demo/customer
- Seller: http://127.0.0.1:3000/demo/seller

Click **Start a fresh demo** or **Fresh demo** once in either window. Both windows follow the active recording session using browser storage events. Each polls the same persisted backend conversation once a second. Do not mix `localhost` with `127.0.0.1`, private windows with normal windows, or separate browser profiles.

Fresh demo copies the default business’s existing published catalogue and policies into a new synthetic workspace with its own capacity ledger. It never deletes conversations, resets seller capacity, changes seller settings, or overwrites an earlier recording. Existing production/test data is preserved. Old recordings remain in PostgreSQL; the demo buttons select the newest session. Do not use the old dashboard’s **Reset all simulated conversations** button for this recording.

## Type these messages

Wait for each real reply before sending the next message. The current fictional Little Crumb catalogue has chocolate cake at ₹900 for 1 kg, eggless at ₹150 and floral decoration at ₹250, with free pickup. This script uses only those configured values. If the default catalogue has changed, review it before recording.

1. `Hi! I'd like one 1 kg chocolate cake for pickup on 2026-11-12.`
   - A real Muse reply offers ₹900; seller shows the same quotation and requested details.
2. `Please make it eggless with floral decoration.`
   - Updated quotation ₹1,300; deposit ₹650. The earlier ₹900 quotation is invalidated in the event history.
3. `Perfect, let's go ahead!`
   - Accepted commitment ₹1,300. Payment remains unverified; production does not start.
4. `Actually, please change my cake to pistachio instead.`
   - Owner review appears; accepted chocolate/eggless/floral details and ₹1,300 remain intact. No unsupported quotation is created.

For later recordings, replace November 12 with an open date at least seven days in the future. The demo does not fake availability or bypass the configured lead time.

## Fastest three-minute recording

Use macOS **Shift–Command–5 → Record Selected Portion**, or QuickTime’s New Screen Recording. Open both windows beforehand. Put customer and seller side by side, or keep each at a readable width and switch between them. Close the evidence/debug disclosure before recording; it is available to demonstrate provenance afterward.

- 0:00–0:15: Explain that a small bakery’s scattered messages can become expensive order mistakes. Show the subtle “Simulated customer · Live AI” label.
- 0:15–1:00: Send the first request. During the real wait, explain Muse interpretation versus deterministic catalogue pricing; point to the live elapsed-time indicator and seller update.
- 1:00–1:40: Add the customizations. Show the price change from ₹900 to ₹1,300.
- 1:40–2:15: Accept. Show the saved commitment and unverified payment status.
- 2:15–3:00: Request pistachio. Show the owner alert beside the preserved accepted order. End on the seller view.

The HTTP rehearsal measured 17.89–26.78 seconds per turn. Provider latency varies; the UI waits for the actual request and never adds simulated delay. You can narrate during the wait. If editing out waiting time, disclose the time cut; do not present prewritten replies as live output.

All customer sends use the existing backend/Meta path. Inference failures remain retryable errors. The existing checked reply fallback remains available if composition fails; seller audit details label it honestly. A fallback is not a Muse-composed reply. Technical IDs and records are confined to expandable seller audit details. No real Instagram traffic, payments, deployment or external notifications are involved.

## Verification commands

```sh
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg:///orderguard_test backend python -m pytest -q -p no:cacheprovider
cd frontend
npm run lint
npm run build -- --webpack
```

Opt-in real Muse + frontend proxy + direct PostgreSQL rehearsal (creates its own isolated session, without affecting the browser’s selected recording):

```sh
docker compose exec -T backend python -m scripts.verify_recording_demo --live
```

Its JSON evidence is written to `/tmp/recording-demo-verification.json` inside the backend container. The script requires `source=meta` and `reply_source=meta` for every step, compares HTTP responses with direct PostgreSQL and HTTP rereads, and asserts repricing, acceptance and preservation after the unsupported change.
