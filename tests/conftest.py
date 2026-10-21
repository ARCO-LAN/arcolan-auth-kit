"""Un provider Authentik factice : clé RSA locale, JWKS servi sans réseau, tokens à la demande."""

import time
from collections.abc import Callable
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm

from arcolan_auth_kit import JWTVerifier

ISSUER = "https://auth.example.test/application/o/lan/"
AUDIENCE = "client-id-du-bff"
STEAM_ID = 76561197988658077


def _keypair(kid: str) -> dict[str, Any]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    jwk = RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return {"kid": kid, "pem": pem, "jwk": jwk}


@pytest.fixture(scope="session")
def key_a() -> dict[str, Any]:
    return _keypair("key-a")


@pytest.fixture(scope="session")
def key_b() -> dict[str, Any]:
    return _keypair("key-b")


@pytest.fixture
def jwks(key_a: dict[str, Any]) -> dict[str, Any]:
    """JWKS mutable : les tests de rotation y ajoutent une clé."""
    return {"keys": [key_a["jwk"]]}


@pytest.fixture
def fetch_count(monkeypatch: pytest.MonkeyPatch, jwks: dict[str, Any]) -> list[int]:
    """Remplace le téléchargement du JWKS et compte les appels."""
    calls = [0]

    def fetch_data(self: PyJWKClient) -> dict[str, Any]:
        calls[0] += 1
        return jwks

    monkeypatch.setattr(PyJWKClient, "fetch_data", fetch_data)
    return calls


@pytest.fixture
def verifier(fetch_count: list[int]) -> JWTVerifier:
    return JWTVerifier(ISSUER, AUDIENCE)


@pytest.fixture
def make_token(key_a: dict[str, Any]) -> Callable[..., str]:
    """Fabrique de tokens signés : `make_token(service="discord")`, `make_token(exp=0)`…"""

    def _make(
        *,
        key: dict[str, Any] | None = None,
        algorithm: str = "RS256",
        headers: dict[str, Any] | None = None,
        **overrides: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "sub-joueur",
            "iat": now,
            "exp": now + 300,
            "steam_id64": str(STEAM_ID),
            "preferred_username": f"steam_{STEAM_ID}",
            "scope": "openid profile email offline_access steam",
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        key = key or key_a
        return jwt.encode(
            claims, key["pem"], algorithm=algorithm, headers=headers or {"kid": key["kid"]}
        )

    return _make


@pytest.fixture
def service_token(make_token: Callable[..., str]) -> str:
    return make_token(
        sub="sub-svc-discord",
        steam_id64=None,
        preferred_username=None,
        service="discord",
        account_type="service_account",
        scope="arcolan",
    )
