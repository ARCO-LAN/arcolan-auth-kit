<!-- bmad:context -->
<!-- Verified 2026-10-23 against 91b175c. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## arcolan-auth-kit

Package Python partagé par les backends Arcolan : validation des tokens Authentik en dépendances FastAPI (`Auth.player`, `Auth.service(...)`, `Auth.principal`), constantes de rôles, et à venir les clients générés. Python 3.13, PyJWT, hatchling, uv.

## Politique

- Les stories, l'architecture, les ADR et les règles complètes vivent dans `arcolan-platform-docs` (cloné à côté, `../arcolan-platform-docs/AGENTS.md`) : les lire avant de changer un flux, un contrat ou une décision.
- Français pour la documentation et les retours de review ; anglais pour le code et les messages de commit.
- Jamais de commit direct sur `main` : une branche par story, `Story-{epic}-{story}-{titre-court}`, puis PR. Les hooks de `../arcolan-platform-docs/scripts/install-hooks.sh` le refusent localement.
- Secrets jamais dans git : `.env` ignoré, `.env.example` sans valeurs.
- Identifiants 64 bits (SteamID64, Discord ID) en chaînes dans l'API, jamais en nombre JSON.

## Lancer et vérifier

- Toujours `uv run` (ruff, pytest, scripts), jamais `pytest` ou `python` nus. `uv` est dans `~/.local/bin`, à ajouter au PATH des shells non interactifs.
- Après tout changement d'API, `uv run python scripts/export_openapi.py` et commiter `openapi.yaml` : la CI échoue sinon.
- Pas d'`openapi.yaml` ici : la CI construit le package avec `uv build` à la place.

## Conventions qui diffèrent des défauts

- Les backends épinglent le kit par `[tool.uv.sources]` à un `rev` git ; un changement d'API publique impose de remonter cet épinglage dans chaque backend qui l'utilise (aujourd'hui `arcolan-users`).
- Tests sans réseau : tokens signés avec une clé RSA locale, JWKS servi en mémoire. Ne jamais appeler Authentik depuis un test.
- Refuser tout token non RS256 ou hors audience ; les rôles ne sont jamais lus dans le token.

## Pièges connus

- Pas de `from __future__ import annotations` dans un module qui déclare des dépendances FastAPI en closure : les annotations deviennent des chaînes et FastAPI répond 422.
- Starlette veut `httpx2` (pas `httpx`) pour son client de test.

<!-- /bmad:context -->
