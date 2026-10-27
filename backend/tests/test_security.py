import time

import jwt
import pytest

from app.core.exceptions import AuthenticationException
from app.core.security import SupabaseJWTVerifier
from tests.conftest import make_settings

SECRET = "test-secret-test-secret-test-secret-123"
ISS = "https://abc.supabase.co/auth/v1"


def _token(**overrides) -> str:
    claims = {"sub": "11111111-1111-1111-1111-111111111111", "aud": "authenticated", "iss": ISS,
              "role": "authenticated", "exp": int(time.time()) + 300}
    claims.update(overrides)
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, SECRET, algorithm="HS256")


@pytest.fixture
def verifier() -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(make_settings())


def test_valid_token(verifier):
    assert verifier.verify(_token())["sub"].startswith("1111")


@pytest.mark.parametrize(
    "bad",
    [
        _token(exp=int(time.time()) - 3600),          # expirado
        _token(aud="otra-audiencia"),                  # audiencia incorrecta
        _token(iss="https://evil.example/auth/v1"),    # emisor incorrecto
        _token(sub=None),                              # sin sub
        jwt.encode({"sub": "x"}, "otra-clave-distinta-otra-clave-1234", algorithm="HS256"),  # firma falsa
        "no.es.un-jwt",
    ],
)
def test_rejects_invalid_tokens(verifier, bad):
    with pytest.raises(AuthenticationException):
        verifier.verify(bad)


def test_rejects_alg_none(verifier):
    unsigned = jwt.encode({"sub": "x", "aud": "authenticated", "iss": ISS}, key=None, algorithm="none")
    with pytest.raises(AuthenticationException):
        verifier.verify(unsigned)
