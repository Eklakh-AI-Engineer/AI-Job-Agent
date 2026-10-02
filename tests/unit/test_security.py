"""
Unit tests for backend/app/core/security.py

Covers password hashing/verification and the access-token lifecycle, including
the failure modes that authentication depends on failing closed.
"""

from datetime import timedelta

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_stored_hash_that_is_not_the_plaintext():
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert hashed.startswith("$2b$")


def test_hash_password_is_salted():
    assert hash_password("supersecret123") != hash_password("supersecret123")


def test_verify_password_accepts_correct_password():
    hashed = hash_password("supersecret123")
    assert verify_password("supersecret123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("supersecret123")
    assert verify_password("wrong-password", hashed) is False


@pytest.mark.parametrize(
    ("plain", "hashed"),
    [
        ("", "$2b$12$whatever"),
        ("password", ""),
        ("password", None),
        (None, "$2b$12$whatever"),
    ],
)
def test_verify_password_fails_closed_on_malformed_input(plain, hashed):
    assert verify_password(plain, hashed) is False


def test_verify_password_returns_false_for_unrecognised_hash_instead_of_raising():
    assert verify_password("password", "not-a-bcrypt-hash") is False


def test_hash_password_rejects_empty_password():
    with pytest.raises(ValueError):
        hash_password("")


def test_create_access_token_round_trips():
    token = create_access_token(subject="42")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["typ"] == "access"


def test_create_access_token_honours_custom_expiry():
    token = create_access_token(subject="42", expires_delta=timedelta(seconds=-1))
    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token)


def test_create_access_token_rejects_empty_subject():
    with pytest.raises(ValueError):
        create_access_token(subject="")


def test_create_access_token_protects_reserved_claims():
    """Extra claims must not be able to escalate or override reserved claims."""
    token = create_access_token(subject="42", extra_claims={"sub": "admin", "typ": "refresh"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["typ"] == "access"


def test_create_access_token_keeps_non_reserved_claims():
    token = create_access_token(subject="42", extra_claims={"scope": "jobs:read"})
    assert decode_access_token(token)["scope"] == "jobs:read"


def test_decode_rejects_tampered_signature():
    token = create_access_token(subject="42")
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_decode_rejects_token_signed_with_another_secret():
    import jwt

    from app.core.config import get_settings

    settings = get_settings()
    foreign = jwt.encode({"sub": "42", "typ": "access"}, "a-different-secret", algorithm="HS256")
    with pytest.raises(TokenError):
        decode_access_token(foreign)
    assert settings.jwt_algorithm == "HS256"


def test_decode_rejects_wrong_token_type():
    import jwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import get_settings

    settings = get_settings()
    now = datetime.now(timezone.utc)
    refresh_like = jwt.encode(
        {"sub": "42", "typ": "refresh", "iat": now, "exp": now + timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError, match="Invalid token type"):
        decode_access_token(refresh_like)


@pytest.mark.parametrize("token", ["", "   ", None])
def test_decode_rejects_missing_token(token):
    with pytest.raises(TokenError):
        decode_access_token(token)
