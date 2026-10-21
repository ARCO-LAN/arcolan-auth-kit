"""Validation des access tokens émis par Authentik.

Un backend vérifie chaque token localement : signature RS256 via le JWKS du provider,
`iss`, `aud`, `exp`. Il en tire un `Principal` : un joueur (claim `steam_id64`) ou un
compte de service (claim `service`, scope `arcolan`). Les rôles ne sont pas dans le token,
ils se demandent au service utilisateurs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import jwt
from jwt import PyJWKClient, PyJWKClientError

ALGORITHMS = ("RS256",)
REQUIRED_CLAIMS = ("exp", "iat", "iss", "aud", "sub")


class InvalidToken(Exception):
    """Token absent, mal formé, expiré, mal signé ou destiné à un autre service."""


@dataclass(frozen=True, slots=True)
class Principal:
    """Qui appelle : un joueur ou un backend, d'après les claims vérifiés du token."""

    sub: str
    """Identifiant stable et opaque chez Authentik : clé de jointure avec la base utilisateurs."""
    steam_id64: int | None = None
    """SteamID64 vérifié par Steam, présent pour un joueur."""
    service: str | None = None
    """Nom du backend appelant (`users`, `discord`, `cs2`…), présent pour un compte de service."""
    account_type: str | None = None
    scopes: frozenset[str] = frozenset()
    claims: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @property
    def is_service(self) -> bool:
        return self.service is not None

    @property
    def is_player(self) -> bool:
        return self.steam_id64 is not None and self.service is None

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> Principal:
        raw_steam = claims.get("steam_id64")
        steam_id64: int | None = None
        if raw_steam not in (None, ""):
            try:
                steam_id64 = int(raw_steam)
            except (TypeError, ValueError) as exc:
                raise InvalidToken(f"steam_id64 invalide : {raw_steam!r}") from exc
        service = claims.get("service") or None
        scope = claims.get("scope") or ""
        return cls(
            sub=claims["sub"],
            steam_id64=steam_id64,
            service=service,
            account_type=claims.get("account_type"),
            scopes=frozenset(scope.split()),
            claims=claims,
        )


class JWTVerifier:
    """Vérifie les tokens d'un provider Authentik et les traduit en `Principal`.

    Le JWKS est téléchargé à la première vérification puis mis en cache ; un `kid` inconnu
    déclenche un rafraîchissement, ce qui couvre la rotation de la clé de signature.
    """

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        *,
        leeway_seconds: int = 30,
        jwks_cache_seconds: int = 3600,
    ) -> None:
        if not issuer.endswith("/"):
            issuer += "/"
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url or f"{issuer}jwks/"
        self.leeway_seconds = leeway_seconds
        self._jwks = PyJWKClient(
            self.jwks_url, cache_keys=True, lifespan=jwks_cache_seconds, cache_jwk_set=True
        )

    @classmethod
    def from_env(cls, prefix: str = "ARCOLAN_OIDC_") -> JWTVerifier:
        """Construit le vérificateur depuis `<prefix>ISSUER`, `<prefix>AUDIENCE` et,
        facultativement, `<prefix>JWKS_URL`."""
        try:
            issuer = os.environ[f"{prefix}ISSUER"]
            audience = os.environ[f"{prefix}AUDIENCE"]
        except KeyError as exc:
            raise RuntimeError(f"variable d'environnement manquante : {exc.args[0]}") from None
        return cls(issuer, audience, os.environ.get(f"{prefix}JWKS_URL") or None)

    def verify(self, token: str) -> Principal:
        """Vérifie signature, `iss`, `aud`, `exp` et renvoie le `Principal`."""
        try:
            key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=list(ALGORITHMS),
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
                options={"require": list(REQUIRED_CLAIMS)},
            )
        except (jwt.PyJWTError, PyJWKClientError) as exc:
            raise InvalidToken(str(exc)) from exc
        return Principal.from_claims(claims)
