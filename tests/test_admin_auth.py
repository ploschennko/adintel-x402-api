from app.admin_auth import create_admin_session, valid_admin_token, verify_admin_session
from app.config import Settings


def test_admin_session_is_signed_and_expires():
    settings = Settings(admin_token='x' * 48)
    value = create_admin_session(settings, now=1000)
    assert verify_admin_session(settings, value, now=1001)
    assert not verify_admin_session(settings, value + 'x', now=1001)
    assert not verify_admin_session(settings, value, now=1000 + 12 * 60 * 60 + 1)
    assert valid_admin_token(settings, 'x' * 48)
    assert not valid_admin_token(settings, 'wrong')
