"""Unit tests for the webhook service HMAC signing."""

from app.services.webhook_service import _sign_payload


def test_sign_payload_hmac_sha256():
    """_sign_payload returns a valid HMAC-SHA256 hex digest."""
    payload = b'{"event": "test"}'
    secret = "my-secret"
    sig = _sign_payload(payload, secret)

    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA256 hex digest is 64 chars


def test_sign_payload_deterministic():
    """Same payload + secret always produce the same signature."""
    payload = b'{"event": "test"}'
    secret = "same-secret"
    assert _sign_payload(payload, secret) == _sign_payload(payload, secret)


def test_sign_payload_different_secrets():
    """Different secrets produce different signatures."""
    payload = b'{"event": "test"}'
    sig1 = _sign_payload(payload, "secret-1")
    sig2 = _sign_payload(payload, "secret-2")
    assert sig1 != sig2
