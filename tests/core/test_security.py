from datetime import timedelta

import pytest

from project_dashboard.core.exceptions import InvalidTokenError
from project_dashboard.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_hashed_value():
    password = "my-password"

    hashed = hash_password(password)

    assert hashed
    assert hashed != password


def test_hash_password_produces_unique_hashes():
    password = "my-password"

    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2


def test_verify_password_verifies_correct_password():
    password = "my-password"

    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_wrong_password():
    password = "my-password"

    hashed = hash_password(password)

    assert verify_password("wrong-password", hashed) is False


def test_create_access_token_creates_token():
    subject = "123"

    token = create_access_token(subject)

    assert token
    assert isinstance(token, str)


def test_decode_access_token_returns_subject():
    subject = "123"

    token = create_access_token(subject)

    assert decode_access_token(token) == subject


def test_decode_access_token_raises_invalid_token_error_on_invalid_token():
    with pytest.raises(InvalidTokenError):
        decode_access_token("invalid-token")


def test_decode_access_token_raises_invalid_token_error_on_tampered_token():
    subject = "123"

    token = create_access_token(subject)
    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered_token)


def test_decode_access_token_raises_invalid_token_error_on_expired_token():
    subject = "123"

    token = create_access_token(subject, expires_delta=timedelta(hours=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
