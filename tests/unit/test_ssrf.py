import pytest

from app.core.ssrf import UnsafeURL, validate_public_url


def test_rejects_localhost():
    with pytest.raises(UnsafeURL):
        validate_public_url("http://127.0.0.1:8000/health")


def test_rejects_private_literal():
    with pytest.raises(UnsafeURL):
        validate_public_url("http://10.0.0.1/internal")


def test_rejects_non_http():
    with pytest.raises(UnsafeURL):
        validate_public_url("file:///etc/passwd")


def test_rejects_url_userinfo():
    with pytest.raises(UnsafeURL):
        validate_public_url("https://user:pass@example.com/")

def test_accepts_public_example():
    assert validate_public_url("https://example.com/jobs") == "https://example.com/jobs"
