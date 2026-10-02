"""Real x402 paid-call smoke test.

Use only with a dedicated low-balance test wallet.
Environment:
  BUYER_PRIVATE_KEY=0x...
  TARGET_URL=http://127.0.0.1:8080/v1/ad-intel
"""
import asyncio
import os

from eth_account import Account
from x402 import SchemeRegistration, x402Client, x402ClientConfig
from x402.http.clients import x402HttpxClient
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmScheme


async def main() -> None:
    private_key = os.environ.get("BUYER_PRIVATE_KEY")
    url = os.environ.get("TARGET_URL")

    if not private_key:
        raise RuntimeError("BUYER_PRIVATE_KEY is not set")
    if not url:
        raise RuntimeError("TARGET_URL is not set")

    account = Account.from_key(private_key)
    signer = EthAccountSigner(account)

    # Current x402 SDK safety cap belongs on the x402 client config,
    # not on x402HttpxClient/httpx.AsyncClient.
    config = x402ClientConfig(
        schemes=[
            SchemeRegistration(
                network="eip155:84532",
                client=ExactEvmScheme(signer),
            )
        ],
        spend_controls={"max_amount_per_payment": "$0.10"},
    )
    client = x402Client.from_config(config)

    payload = {
        "product": "NOVA App",
        "offer": "20% off annual plan",
        "geo": "US",
        "language": "English",
        "vertical": "mobile app",
        "audience": "Adults interested in productivity tools",
        "tone": "direct",
    }

    print("buyer:", account.address)
    print("target:", url)
    print("max payment: $0.10")

    async with x402HttpxClient(client, timeout=120.0) as http:
        response = await http.post(url, json=payload)
        await response.aread()
        print("status:", response.status_code)
        print("payment-response:", response.headers.get("payment-response"))
        try:
            print(response.json())
        except Exception:
            print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
