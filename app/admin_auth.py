import hashlib
import hmac
import time

from .config import Settings

SESSION_COOKIE_NAME = 'adintel_admin_session'
SESSION_TTL_SECONDS = 12 * 60 * 60


def _safe_equal(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left.encode('utf-8'), right.encode('utf-8'))


def valid_admin_token(settings: Settings, candidate: str) -> bool:
    return _safe_equal(candidate, settings.admin_token)


def create_admin_session(settings: Settings, *, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = str(issued_at)
    signature = hmac.new(
        settings.admin_token.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return f'{payload}.{signature}'


def verify_admin_session(
    settings: Settings,
    value: str,
    *,
    now: int | None = None,
    ttl_seconds: int = SESSION_TTL_SECONDS,
) -> bool:
    if not value or '.' not in value:
        return False
    payload, signature = value.split('.', 1)
    try:
        issued_at = int(payload)
    except ValueError:
        return False

    current = int(time.time() if now is None else now)
    if issued_at > current + 60 or current - issued_at > ttl_seconds:
        return False

    expected = hmac.new(
        settings.admin_token.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
