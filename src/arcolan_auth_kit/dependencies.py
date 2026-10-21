"""Dépendances FastAPI construites sur `JWTVerifier`.

    auth = Auth(JWTVerifier.from_env())

    @app.get("/me")
    def me(who: Annotated[Principal, Depends(auth.player)]): ...

    @app.get("/users/by-steam/{steam_id64}")
    def by_steam(who: Annotated[Principal, Depends(auth.service("discord", "cs2"))]): ...

    @app.get("/teams/{team_id}")
    def team(who: Annotated[Principal, Depends(auth.principal)]): ...   # joueur ou service

Réponses : 401 sans token ou token invalide (avec `WWW-Authenticate: Bearer`), 403 quand
le token est valide mais vient du mauvais type d'appelant.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from arcolan_auth_kit.tokens import InvalidToken, JWTVerifier, Principal

_bearer = HTTPBearer(auto_error=False, description="Access token Authentik (joueur ou service)")

Dependency = Callable[..., Principal]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


class Auth:
    """Fabrique de dépendances FastAPI pour un vérificateur donné."""

    def __init__(self, verifier: JWTVerifier) -> None:
        self.verifier = verifier
        self.principal: Dependency = self._make_principal()
        """Tout token valide : joueur ou compte de service."""
        self.player: Dependency = self._make_player()
        """Token d'un joueur (claim `steam_id64`), jamais d'un compte de service."""

    def _make_principal(self) -> Dependency:
        verifier = self.verifier

        def principal(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        ) -> Principal:
            if credentials is None:
                raise _unauthorized("token manquant")
            try:
                return verifier.verify(credentials.credentials)
            except InvalidToken as exc:
                raise _unauthorized(f"token invalide : {exc}") from None

        return principal

    def _make_player(self) -> Dependency:
        def player(principal: Annotated[Principal, Depends(self.principal)]) -> Principal:
            if not principal.is_player:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "réservé aux joueurs")
            return principal

        return player

    def service(self, *allowed: str) -> Dependency:
        """Token d'un compte de service, limité aux backends nommés (tous si aucun)."""

        def service(principal: Annotated[Principal, Depends(self.principal)]) -> Principal:
            if not principal.is_service:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "réservé aux comptes de service")
            if allowed and principal.service not in allowed:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, f"service {principal.service!r} non autorisé"
                )
            return principal

        return service
