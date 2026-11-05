# Instagram adapter: implemented boundary and setup

This is a local adapter and signed synthetic replay, **not a verified live Instagram connection**. No real messages have been sent. OAuth, app review, account authorization and a public HTTPS callback are incomplete. The owner has not authorized real outbound messaging.

## Verified contract references

- [Meta's official Instagram API workspace](https://www.postman.com/meta/instagram/overview) and [Instagram Login collection](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login): professional-account messaging and `instagram_business_manage_messages`.
- [Official Send API request documentation](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-af579d08-121e-4897-8f45-5fd41ace49df): `POST https://graph.instagram.com/{api_version}/{ig_user_id}/messages`, recipient/message body and bearer token.
- [Instagram business login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/), [messaging](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/) and [webhooks](https://developers.facebook.com/docs/instagram-platform/webhooks/): canonical setup references. These developer pages returned HTTP 429 in this session. Their complete current OAuth flow could not be verified, so no speculative OAuth implementation was shipped.

The adapter implements the requested HMAC-SHA256 signature guard over exact raw bytes. Challenge and signature behavior are verified with synthetic fixtures. This is not evidence that a real Meta webhook reached this server.

## What is implemented

- Verification challenge: `GET /webhooks/instagram`; constant-time comparison of `hub.verify_token`, with `hub.mode=subscribe` and plain-text challenge response.
- Incoming endpoint: `POST /webhooks/instagram`; disabled unless explicitly configured; raw-body size limit and HMAC-SHA256 `X-Hub-Signature-256` validation before JSON interpretation.
- Text-message normalization, stable internal IDs, sender/account conversation association, echo/receipt suppression, unsupported-media review and conflict detection for altered duplicate IDs.
- Account IDs are bound to one business by PostgreSQL constraints. A request header cannot override signed webhook routing.
- Durable PostgreSQL inbox; quick enqueue without a Muse call or the long business-capacity lock. An explicit worker processes pending/error rows with stored backoff and at most three attempts.
- Agent processing, order mutation and held reply draft are atomic. Competing processors produce one order turn and one draft. Out-of-order messages need review.
- Outbound transport contract, conservative 24-hour check, explicit authorization gate and commit-before-send claim. Ambiguous failures are `delivery_unknown`, with **no automatic resend**.
- Local disconnect clears the token reference and stops processing while preserving history. HTTP 401/403 from the tested send contract marks reauthorization required. Remote OAuth revocation is not implemented.
- Seller status page at `/channels` and isolated signed synthetic replay using real Muse when configured. Replays never target real accounts and cannot consume the source business's capacity.

## Tokens and access

Tokens are never stored in PostgreSQL, returned to the browser, logged, or copied into images. A server-side account record stores only the name of a dedicated runtime secret variable, such as `INSTAGRAM_ACCESS_TOKEN_DEFAULT`. The actual token must be privately supplied by the operator to that variable. This is runtime secret referencing, not a claim of encrypted OAuth token storage.

No token-entry browser form or OAuth completion route is shipped. No browser/client can register a live account or send a real reply through an HTTP endpoint. Local business switching remains unauthenticated; the application must stay private and loopback-bound.

## Future account setup, requiring owner participation

1. Verify the current professional-account login path and permissions in Meta's official dashboard/rules. Obtain appropriate owner consent and access. This session did not do so.
2. Privately provide a dedicated account token, the correct webhook app secret and verification token. Set an API version actually verified for that app; the code does not guess the current version.
3. Supply a controlled HTTPS webhook endpoint and appropriate authentication/access protections. Public hosting is not performed or authorized here.
4. Register the verified account ID locally using the server command, after confirming it belongs to the selected business:

```sh
docker compose exec -T backend python -m app.instagram_worker \
  --register-account YOUR_PROFESSIONAL_ACCOUNT_ID \
  --business YOUR_BUSINESS_ID \
  --token-env INSTAGRAM_ACCESS_TOKEN_DEFAULT
```

5. Only after consent/permissions are established, deliberately enable `INSTAGRAM_INGEST_ENABLED=true` in the private runtime configuration and configure the callback/subscriptions in Meta. Account registration alone does not validate those permissions.
6. Process one durable inbox batch explicitly:

```sh
docker compose exec -T backend python -m app.instagram_worker --once
```

Replies remain held. Compose **hard-sets `INSTAGRAM_OUTBOUND_ENABLED=false`**. There is no public send route or automatic send worker. Enabling real customer sends requires a separately authorized implementation/deployment decision. A conservative 24-hour guard does not establish full platform-policy compliance.

For multiple accounts, provide separate server-only token variables using a private Compose override or secret injection. Never reuse `MODEL_API_KEY` as an Instagram token. Additional secrets must remain out of source control and images.

## Safe local replay

Open `/channels`, choose **Start isolated replay**, and enter a fictional customer message. The server creates an isolated business/account, signs and verifies a synthetic webhook, stores it in the inbox, invokes the actual agent and returns the reply draft. It never calls the Instagram Send API. Duplicate delivery IDs preserve the saved state. Reset deletes only source-owned synthetic replay namespaces.

```sh
docker compose exec -T backend python scripts/verify_instagram_replay.py --live \
  --business YOUR_PUBLISHED_BLOOM_BUSINESS_ID
```

`--live` means genuine **Muse inference**, not live Instagram transport. All send tests use explicitly mocked HTTP transports. No real account/token/recipient was used for those tests.
