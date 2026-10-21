import time

import pytest

from arcolan_auth_kit import InvalidToken, JWTVerifier
from tests.conftest import AUDIENCE, ISSUER, STEAM_ID


def test_player_token(verifier, make_token):
    who = verifier.verify(make_token())
    assert who.sub == "sub-joueur"
    assert who.steam_id64 == STEAM_ID
    assert who.is_player and not who.is_service
    assert who.service is None
    assert "steam" in who.scopes
    assert who.claims["preferred_username"] == f"steam_{STEAM_ID}"


def test_service_token(verifier, service_token):
    who = verifier.verify(service_token)
    assert who.is_service and not who.is_player
    assert who.service == "discord"
    assert who.account_type == "service_account"
    assert who.steam_id64 is None
    assert who.scopes == {"arcolan"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 120},
        {"aud": "un-autre-client"},
        {"iss": "https://auth.example.test/application/o/autre/"},
        {"sub": None},
        {"exp": None},
        {"steam_id64": "pas-un-nombre"},
    ],
    ids=[
        "expiré",
        "mauvaise audience",
        "mauvais issuer",
        "sans sub",
        "sans exp",
        "steam_id64 invalide",
    ],
)
def test_rejected_claims(verifier, make_token, overrides):
    with pytest.raises(InvalidToken):
        verifier.verify(make_token(**overrides))


def test_leeway_tolerates_small_clock_skew(verifier, make_token):
    verifier.verify(make_token(exp=int(time.time()) - 10))


def test_hs256_signed_with_a_secret_is_rejected(verifier):
    import jwt

    secret = "un-secret-hmac-suffisamment-long-pour-pyjwt-0123456789"
    token = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "sub": "x"}, secret, algorithm="HS256")
    with pytest.raises(InvalidToken):
        verifier.verify(token)


def test_garbage_is_rejected(verifier):
    with pytest.raises(InvalidToken):
        verifier.verify("pas.un.jwt")


def test_token_signed_by_unknown_key_is_rejected(verifier, make_token, key_b):
    with pytest.raises(InvalidToken):
        verifier.verify(make_token(key=key_b))


def test_key_rotation_refreshes_jwks(verifier, make_token, jwks, key_a, key_b, fetch_count):
    verifier.verify(make_token())
    assert fetch_count[0] == 1
    jwks["keys"].append(key_b["jwk"])  # Authentik publie la nouvelle clé
    verifier.verify(make_token(key=key_b))
    assert fetch_count[0] == 2  # kid inconnu → JWKS rechargé une fois
    verifier.verify(make_token(key=key_a))
    assert fetch_count[0] == 2  # les deux clés sont en cache


def test_jwks_url_defaults_to_authentik_convention():
    v = JWTVerifier("https://auth.example.test/application/o/lan", "aud")
    assert v.issuer == "https://auth.example.test/application/o/lan/"
    assert v.jwks_url == "https://auth.example.test/application/o/lan/jwks/"
    assert JWTVerifier("https://x/", "aud", jwks_url="https://y/jwks").jwks_url == "https://y/jwks"


def test_from_env(monkeypatch):
    monkeypatch.setenv("ARCOLAN_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("ARCOLAN_OIDC_AUDIENCE", AUDIENCE)
    v = JWTVerifier.from_env()
    assert (v.issuer, v.audience) == (ISSUER, AUDIENCE)
    monkeypatch.delenv("ARCOLAN_OIDC_AUDIENCE")
    with pytest.raises(RuntimeError, match="ARCOLAN_OIDC_AUDIENCE"):
        JWTVerifier.from_env()
