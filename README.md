# arcolan-auth-kit

Package Python partagé entre les backends de la plateforme Arcolan. Il reste volontairement
petit : validation des access tokens d'Authentik sous forme de dépendances FastAPI, constantes
de rôles, et bientôt les clients générés depuis les `openapi.yaml` du service utilisateurs et
du backend Discord.

Architecture, décisions et plan de réalisation : [arcolan-platform-docs](https://github.com/ARCO-LAN/arcolan-platform-docs).

## Installation dans un backend

Le package est versionné par tags git et installé à une version fixe :

```toml
dependencies = [
    "arcolan-auth-kit @ git+https://github.com/ARCO-LAN/arcolan-auth-kit@v0.1.0",
]
```

## Validation des tokens

Chaque backend vérifie localement les tokens émis par le provider `lan` d'Authentik :
signature RS256 via le JWKS, `iss`, `aud`, `exp`. Le résultat est un `Principal`, joueur
(claim `steam_id64`) ou compte de service (claim `service`). Les rôles ne sont pas dans le
token : ils se demandent au service utilisateurs.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from arcolan_auth_kit import Auth, JWTVerifier, Principal

auth = Auth(JWTVerifier.from_env())  # ARCOLAN_OIDC_ISSUER, ARCOLAN_OIDC_AUDIENCE
app = FastAPI()


@app.get("/me")
def me(who: Annotated[Principal, Depends(auth.player)]):  # joueurs seulement
    return {"steam_id64": who.steam_id64}


@app.get("/users/by-steam/{steam_id64}")
def by_steam(who: Annotated[Principal, Depends(auth.service("discord", "cs2"))]):  # backends nommés
    ...


@app.get("/teams/{team_id}")
def team(who: Annotated[Principal, Depends(auth.principal)]):  # joueur ou service
    ...
```

| Variable | Valeur en production |
| --- | --- |
| `ARCOLAN_OIDC_ISSUER` | `https://auth.arcolan.fun/application/o/lan/` |
| `ARCOLAN_OIDC_AUDIENCE` | l'ID client du provider `lan` |
| `ARCOLAN_OIDC_JWKS_URL` | facultatif, par défaut `<issuer>jwks/` |

Réponses : 401 avec `WWW-Authenticate: Bearer` si le token manque ou est invalide, 403 si le
token est valide mais vient du mauvais type d'appelant. Le JWKS est mis en cache ; un `kid`
inconnu le recharge, ce qui couvre la rotation de la clé de signature.

## Rôles

`arcolan_auth_kit.roles` porte les constantes (`GLOBAL_ADMIN`, `PLAYER`) et la convention de
nommage : `global_` pour les rôles transverses, `<backend>_` pour ceux qu'un seul backend
interprète. `has_role(roles, "cs2_operator")` est vrai aussi pour un `global_admin`.

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv build
```

Les tests n'ont besoin d'aucun réseau : ils signent des tokens avec une clé RSA locale et
servent le JWKS en mémoire.

## CI

À chaque push sur `main` et à chaque pull request : lint et format (ruff), tests (pytest),
construction du package.
