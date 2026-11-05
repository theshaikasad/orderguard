# Recording script and manual browser acceptance

Target: an edited 2–3 minute walkthrough, not an official duration requirement. Record actual requests and responses. Cut or accelerate waiting time with a visible “Model wait shortened” caption; never replace inference with scripted responses. No recording or uploaded demo link exists yet.

Keep this caption visible: **Synthetic customers · real Meta Muse Spark inference · local simulator**. Show `Audit & debug details` → `Interpretation: meta` and the reply source. A checked fallback is possible: disclose it if used; do not call fallback wording Muse-generated. Setup errors and Scenario Lab errors remain errors.

## Preparation

```sh
docker compose up --build -d --wait
```

Privately configure `MODEL_API_KEY` and `POSTGRES_PASSWORD` in root `.env`. Open http://127.0.0.1:3000/overview. Keep Instagram outbound disabled. Use a new business for recording; existing verification florists already have the ₹799 price. Never reset existing seller orders to stage the video. Allow several minutes of raw recording for model waits; the previously measured customer median was about 21.6 seconds and setup can take over a minute.

## Exact seller inputs

Click **＋ New business** → **Business settings / Overview**. New businesses should say **Automation paused · Not published**. Paste into **Tell us about your business** and click **Help me set up with Muse**:

```text
Hey! I run Bloom & Co., a small flower shop.
We sell a bouquet of 12 red roses for ₹699 and
a mixed flower bouquet for ₹499.

Gift wrapping with a ribbon costs ₹50 extra.
A handwritten greeting card costs ₹30 extra.

Pickup is free.
Delivery costs ₹80 in our service area.
We require at least 24 hours' notice.
We can fulfill only 2 orders per day.

Our prices are fixed and we don't offer discounts.
Please keep replies friendly and casual.
```

After real extraction, show unresolved questions and **Setup evidence** (`Inference: meta`). Paste this clarification into the same field, then click **Help me set up with Muse** again:

```text
We are in Bengaluru, India. Both extras are per bouquet: ribbon wrapping is ₹50 per item and the handwritten greeting card is ₹30 per item. Pickup is free, with no charge. Delivery is ₹80 per order to Indiranagar only. We are open 10 AM to 6 PM IST, with no holidays currently planned. Minimum preparation time is 24 hours. Capacity is 2 orders per day. No deposit is required, 0 percent. Changes and cancellations after acceptance need owner approval; no automatic refunds. Any safety/dietary issue, unsupported request, exact delivery slot or accepted change needs owner review. Please use friendly casual English.
```

Review actual extraction; do not assume every edit was inferred. The seller can correct omissions explicitly:

- **Overview**: Bloom & Co.; flower shop; Bengaluru, India.
- **Products & Pricing**: 12-red-rose bouquet ₹699; mixed bouquet ₹499. Check product/variant units; one customer quantity means one bouquet, not twelve bouquets.
- **Customizations**: ribbon wrapping ₹50 and handwritten greeting card ₹30, each **Per item** (one bouquet). Either extra group is valid; names may vary with inference.
- **Delivery & Availability**: pickup ₹0; delivery ₹80, service-area keyword `Indiranagar`; hours `10 AM to 6 PM IST`; preparation `24`; daily capacity `2`; capacity counted in **Orders**; no holidays.
- **Payments & Policies**: deposit `0`; cancellation `Changes and cancellations after acceptance need owner approval; no automatic refunds.`; dietary `Any safety or dietary issue needs owner review.`
- **When to Notify Me**: leave **Require my approval for every order** unchecked; guidance `Unsupported requests, exact delivery slots and accepted changes need owner review.`

Click **Save draft**. If setup questions remain after answering them manually, check **I answered these questions in the settings above. Clear them when saving.**, then **Save draft**. Open **Review & Publish**, review the full summary, check **I checked prices, charge units, preparation time, deposit and approval rules.**, click **Publish reviewed rules**, then **Resume automation**. Verify published version 1 and active automation. Manual corrections are seller decisions, not model output.

## Timed click sequence and narration

| Video time | Exact screen/action | Narration |
|---|---|---|
| 0:00–0:15 | `/overview`; show synthetic-data label | “Small Instagram-first sellers spend hours answering questions and reconstructing changing orders. A wrong price or late change can become a costly promise.” |
| 0:15–0:45 | New business → seller inputs above → Setup evidence → Review & Publish → Publish → Resume | “I teach OrderGuard a florist's menu in plain language. Meta Muse extracts sourced draft rules and asks about gaps. The seller reviews and publishes the authority the agent can use.” |
| 0:45–1:15 | Conversations → fresh URL below → send customer messages → accept | “Muse understands the customer. Backend rules calculate ₹859: ₹699 roses, ₹50 wrapping, ₹30 card and ₹80 delivery. A natural yes confirms this exact quote; it does not verify payment or start production.” |
| 1:15–1:45 | Settings → Products & Pricing → rose price 799 → Save draft → Review & Publish → review checkbox → Publish → fresh conversation | “I publish a price change without restarting. The next quote is ₹959. The earlier accepted order keeps ₹859 and its historical configuration.” |
| 1:45–2:30 | Switch to The Little Crumb → Scenario Lab → E Late production change → Run with Muse | “Now the difficult case. After an explicit simulated production start, the customer changes product and date. The production instructions remain frozen. One actionable owner review is created.” |
| 2:30–2:50 | Persisted checks and audit; optional Bloom overview | “Routine clarification and valid quotes stay automatic. Humans handle exceptions. These are synthetic conversations with real Meta inference, backed by persisted state checks.” |
| 2:50–3:00 | Close on overview | “OrderGuard turns conversations into reliable commitments. Instagram is a partial adapter; live messaging and payment verification are not connected.” |

Before typing, keep Bloom selected in **Demo business switcher**. Open a fresh URL (use a fresh suffix if repeating):

http://127.0.0.1:3000/?conversation=recording-bloom-01

Use **Customer simulator message** → **Send customer message** with the complete request below. This complete-message path produced a fresh ₹859 quote; the shorter two-turn inquiry timed out twice during final checks. Keep those errors disclosed in reliability evidence rather than attempting them during recording.

```text
I need one bouquet of 12 red roses with ribbon wrapping and a handwritten greeting card, delivery to 18 Garden Lane, Indiranagar, Bengaluru on 2026-11-25.
```

Expect **Current quote: Total ₹859**. If details are still missing, answer the actual question; never narrate an absent quote. Then:

```text
Perfect, let's go ahead!
```

Show **Confirmed details: ₹859**, **Payment: Not verified**, empty **Production plan**, no **Owner review** alert, and **Audit & debug details** provenance. Do not click production for this routine-order scene.

After publishing ₹799, open http://127.0.0.1:3000/?conversation=recording-bloom-02 and send:

```text
I need one bouquet of 12 red roses with ribbon wrapping and a handwritten greeting card, delivery to 18 Garden Lane, Indiranagar, Bengaluru on 2026-11-25.
```

Expect **Current quote: Total ₹959**. Return to `?conversation=recording-bloom-01` to show the original confirmed ₹859. Use **Published history** for versions. URLs preserve conversation selection; the business switcher controls business scope.

For the complex scene, select **The Little Crumb**, click **Scenario Lab**, find **E / Late production change**, click **Run with Muse →**. It sends an eligible cake request, “I confirm”, an explicit local owner production action, then a product/date revision. The generated future dates and alternate product appear in the actual transcript. Wait for **passed · 4/4 steps**, **REAL META INFERENCE**, frozen-plan/pending-change checks, **One actionable owner review** and unverified-payment check. Expand **Timing, errors & audit details** to show the original production snapshot. Never substitute prior results if a new run errors; disclose a previously persisted run as such.

## Manual UI checks still required

Final-session native Safari verified the overview, navigation into New business, and the paused unpublished settings form. The browser-extension host was unavailable. Automatic approval review rejected subsequent Safari onboarding interaction (“Computer Use was not approved to use Safari”). Full UI publishing, conversations, Lab and responsive acceptance did **not** pass in this session; API checks are separate evidence.

1. Follow the exact onboarding/publish sequence above. Confirm active version changes and pause/resume behavior.
2. Follow both Bloom conversations; click evidence links in audit and confirm the referenced message is highlighted. Navigate Overview → Open conversation and back.
3. Run Lab E, inspect persisted checks and the single exception; confirm routine Bloom quotes have no owner alert. Lab copies must not consume seller capacity.
4. Visit all navigation links (Overview, Conversations, Business settings, Scenario Lab, Instagram). Instagram must visibly remain disconnected/synthetic.
5. At desktop and 390px viewport width (browser developer tools responsive mode), inspect overview, settings, transcript/order desk and Lab. Check navigation wraps, controls remain reachable, panels stack, no clipped composer or page-wide horizontal scrolling. Tab through inputs and buttons and verify visible focus. Responsive layout has not been visually verified yet.
6. If inference fails, inspect errors and use **Retry same message**. Do not click reset to erase evidence. Verify no duplicate accepted order.

## Existing evidence / optional reruns

Historical real Muse evidence: `artifacts/m3`, `artifacts/m4`, and `M3_REPORT.md`. Current final results are recorded in `docs/FINAL_VERIFICATION.md`. The fresh complete-order florist is `shop-6e3e0b5f795a45fa937920f1afe9360b`, with accepted ₹859 conversation `submission-complete-01` and ₹959 quote `submission-complete-02`; it is now version 2 at ₹799. To inspect it without confusing the several Bloom names, open Overview activity and select the matching conversation URL. Create a fresh business for a new onboarding recording. The historic florist `shop-bb147585b244422e9c3de275eb4a528e` has ₹859 commitment `bloom-193303` and ₹959 quote `bloom-193303-new`; those are audit IDs, not customer prose.

```sh
docker compose exec -T backend python scripts/verify_bloom.py --live
docker compose exec -T backend python scripts/verify_lab.py --live --scenarios E
```

These scripts use genuine Muse and leave synthetic records. The Bloom script explicitly labels injected outage testing; model responses are not scripted. Do not spend the remaining recording/submission window rerunning the whole matrix unnecessarily.
