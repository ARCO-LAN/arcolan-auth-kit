from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from arcolan_auth_kit import Auth, Principal


@pytest.fixture
def client(verifier):
    auth = Auth(verifier)
    app = FastAPI()

    @app.get("/me")
    def me(who: Annotated[Principal, Depends(auth.player)]):
        return {"sub": who.sub, "steam_id64": who.steam_id64}

    @app.get("/internal")
    def internal(who: Annotated[Principal, Depends(auth.service("discord", "cs2"))]):
        return {"service": who.service}

    @app.get("/any-service")
    def any_service(who: Annotated[Principal, Depends(auth.service())]):
        return {"service": who.service}

    @app.get("/shared")
    def shared(who: Annotated[Principal, Depends(auth.principal)]):
        return {"player": who.is_player, "service": who.is_service}

    return TestClient(app)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_missing_token_is_401_with_challenge(client):
    r = client.get("/me")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_401(client):
    r = client.get("/me", headers=bearer("n.importe.quoi"))
    assert r.status_code == 401
    assert r.json()["detail"].startswith("token invalide")


def test_player_routes(client, make_token, service_token):
    assert client.get("/me", headers=bearer(make_token())).json()["steam_id64"] == 76561197988658077
    assert client.get("/me", headers=bearer(service_token)).status_code == 403


def test_service_routes(client, make_token, service_token):
    assert client.get("/internal", headers=bearer(service_token)).json() == {"service": "discord"}
    assert client.get("/internal", headers=bearer(make_token())).status_code == 403
    autre = make_token(steam_id64=None, service="users", account_type="service_account")
    r = client.get("/internal", headers=bearer(autre))
    assert r.status_code == 403
    assert "'users'" in r.json()["detail"]
    assert client.get("/any-service", headers=bearer(autre)).json() == {"service": "users"}


def test_shared_route_accepts_both(client, make_token, service_token):
    assert client.get("/shared", headers=bearer(make_token())).json() == {
        "player": True,
        "service": False,
    }
    assert client.get("/shared", headers=bearer(service_token)).json() == {
        "player": False,
        "service": True,
    }


def test_openapi_declares_bearer_security(client):
    schema = client.get("/openapi.json").json()
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    assert schema["paths"]["/me"]["get"]["security"] == [{"HTTPBearer": []}]
