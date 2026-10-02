# AdIntel x402 API v0.5.1

Multi-endpoint pay-per-call advertising intelligence API using FastAPI, OpenRouter and x402 USDC payments.

## Paid endpoints

| Endpoint | Default price | Output |
|---|---:|---|
| `POST /v1/hooks` | $0.01 | 12 ad hooks |
| `POST /v1/angles` | $0.02 | 6 strategic ad angles |
| `POST /v1/video-storyboard` | $0.03 | storyboard + video prompt |
| `POST /v1/ad-intel` | $0.05 | complete creative pack |
| `POST /v1/full-campaign` | $0.10 | premium strategy + creative pack + testing plan |

Free discovery endpoints: `/`, `/health`, `/pricing`, `/v1/catalog`, `/docs`.

Each paid route has its own x402 price and Bazaar discovery metadata. Dashboard economics store the endpoint and its actual configured revenue per successful call.

## Upgrade from v0.4.1 / current deployed service

Copy your existing `.env`, `.buyer.env` and database into this directory, or update the existing Git repository with the v0.5.1 files. Existing SQLite rows migrate automatically; old calls are assigned `/v1/ad-intel`.

Add the four new price variables to Render (defaults work if omitted):

```env
X402_PRICE_HOOKS=$0.01
X402_PRICE_ANGLES=$0.02
X402_PRICE_STORYBOARD=$0.03
X402_PRICE=$0.05
X402_PRICE_FULL_CAMPAIGN=$0.10
```

Keep `X402_NETWORK=eip155:84532` until public testnet checks pass.

## Smoke test

Set `TARGET_URL` to any paid endpoint, e.g.:

```powershell
$env:TARGET_URL = "https://your-service.onrender.com/v1/hooks"
.\.venv\Scripts\python.exe .\scripts\paid_test.py
```

The script max-spend cap remains $0.10.


## v0.5.1 reliability fix
- Normalizes common LLM object variants in string-array fields (especially angles).
- Prompts explicitly require string arrays.
- Preserves OpenRouter usage/cost when provider output is invalid and local fallback is used.
