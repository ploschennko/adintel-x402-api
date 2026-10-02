import os
import sys

import httpx


url = os.getenv('TARGET_URL', 'http://127.0.0.1:8080/v1/ad-intel')
payload = {
    'product': 'Test Product',
    'offer': 'Test Offer',
    'geo': 'US',
    'language': 'English',
}

resp = httpx.post(url, json=payload, timeout=20)
print('status:', resp.status_code)
print('payment-required:', resp.headers.get('payment-required'))
print('body:', resp.text[:500])

if resp.status_code == 402:
    print('OK: endpoint is protected by x402')
    sys.exit(0)
print('NOTE: expected 402. If X402_ENABLED=false, a 200 response is normal in local dev mode.')
