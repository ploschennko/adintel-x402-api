import base64
import json
from typing import Any


class X402PaymentCaptureMiddleware:
    """Capture x402 settlement metadata after the payment middleware responds.

    The x402 middleware adds a `payment-response` header after a successful paid
    request. This outer ASGI middleware reads that header plus the response JSON's
    request_id and stores payer/transaction/network without ever storing a buyer
    private key.
    """

    def __init__(self, app, store):
        self.app = app
        self.store = store

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            await self.app(scope, receive, send)
            return

        response_headers: dict[str, str] = {}
        body_parts: list[bytes] = []

        async def send_wrapper(message: dict[str, Any]):
            if message['type'] == 'http.response.start':
                for key, value in message.get('headers', []):
                    try:
                        response_headers[key.decode('latin-1').lower()] = value.decode('latin-1')
                    except Exception:
                        continue
            elif message['type'] == 'http.response.body':
                body = message.get('body', b'')
                if body and sum(map(len, body_parts)) < 1_000_000:
                    body_parts.append(body)

            await send(message)

            if message['type'] == 'http.response.body' and not message.get('more_body', False):
                self._capture(response_headers, b''.join(body_parts))

        await self.app(scope, receive, send_wrapper)

    def _capture(self, headers: dict[str, str], body: bytes) -> None:
        encoded = headers.get('payment-response')
        if not encoded or not body:
            return
        try:
            payload = json.loads(body.decode('utf-8'))
            request_id = str(payload.get('request_id') or '')
            if not request_id:
                return

            padded = encoded + '=' * (-len(encoded) % 4)
            try:
                decoded = base64.b64decode(padded)
            except Exception:
                decoded = base64.urlsafe_b64decode(padded)
            payment = json.loads(decoded.decode('utf-8'))

            payer = payment.get('payer')
            tx_hash = payment.get('transaction') or payment.get('tx_hash')
            network = payment.get('network')
            self.store.attach_payment(
                request_id=request_id,
                payer=str(payer) if payer else None,
                tx_hash=str(tx_hash) if tx_hash else None,
                network=str(network) if network else None,
            )
        except Exception:
            # Analytics must never break a successful paid API response.
            return


def install_payment_capture(app, store) -> None:
    # Added after x402 so this wrapper can observe x402's final payment-response header.
    app.add_middleware(X402PaymentCaptureMiddleware, store=store)
