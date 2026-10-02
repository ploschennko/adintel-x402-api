# AdIntel x402 API — v0.4.1

Pay-per-call advertising creative intelligence API for AI agents and automation tools.

## Proven flow

Base Sepolia end-to-end payment has been validated:

`402 Payment Required → signed USDC payment → settlement → 200 OK → OpenRouter result`.

## Paid endpoint

`POST /v1/ad-intel` returns hooks, angles, headlines, primary texts, creative concepts, short-video storyboard, image/video prompts and compliance notes.

Default test price: **$0.05 USDC per call**.

Free endpoints: `/health`, `/pricing`, `/demo`.

## v0.4.1 changes

### Correct measured economics

Old OpenRouter rows created before cost tracking no longer count as `$0` inference cost.
They are marked **N/A** and excluded from measured profit and margin.

The dashboard now separates:

- configured gross revenue
- measured paid calls
- measured revenue
- measured AI cost
- measured gross profit
- measured gross margin
- unmeasured legacy paid calls

OpenRouter cost is taken from `usage.cost` when present.

### Safer admin dashboard

The admin token is no longer placed in the URL.

Open locally:

```text
http://127.0.0.1:8080/admin
```

Enter `ADMIN_TOKEN` in the login form. The browser sends it in `X-Admin-Token`, then receives a signed HttpOnly session cookie valid for 12 hours.

JSON stats still support header authentication:

```text
GET /admin/stats
X-Admin-Token: <ADMIN_TOKEN>
```

Do not expose the admin token publicly. Rotate any token that has appeared in a screenshot, URL, shell history, logs, or chat.

## Upgrade from v0.4

Keep your existing `.env` and `data/adintel.sqlite3`. The database migrates automatically.

On Windows, if the old folder is named `adintel_x402_mvp_v0_4` and both folders are on Desktop, run:

```powershell
.\MIGRATE_FROM_V04.ps1
```

This copies `.env`, `.buyer.env`, and `data\adintel.sqlite3` without printing secrets. Then run:

```bat
RUN_WINDOWS.bat
```

Then verify:

```text
http://127.0.0.1:8080/health
```

Expected version: `0.4.1`.

Dashboard:

```text
http://127.0.0.1:8080/admin
```

## Public deployment readiness

Included:

- `Dockerfile`
- `Procfile`
- `render.yaml`
- `/health`

Before public deployment set:

```env
PUBLIC_BASE_URL=https://YOUR_PUBLIC_HOST
APP_URL=https://YOUR_PUBLIC_HOST
ADMIN_TOKEN=<unique-random-secret-32+-chars>
```

Stay on Base Sepolia (`eip155:84532`) until a public remote paid call succeeds.

## Mainnet later

After the public HTTPS/testnet smoke test:

```env
X402_NETWORK=eip155:8453
X402_PRICE=$0.01
PAY_TO_ADDRESS=0xYOUR_REAL_RECEIVER
```

Use a tiny first mainnet payment, verify the on-chain receipt and API response, then set the intended commercial price.

## Security reminders

- Never upload `.env` or `.buyer.env`.
- Never expose buyer private keys or seed phrases.
- Use a dedicated low-balance buyer wallet for automated tests.
- Rotate exposed admin tokens before public deployment.
- Reconcile dashboard revenue with wallet/on-chain receipts before accounting use.
