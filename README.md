# arcolan-auth-kit

Package Python partagé entre les backends de la plateforme Arcolan. Il reste volontairement
petit : validation des JWT d'Authentik (dépendance FastAPI), clients générés depuis les
`openapi.yaml` du service utilisateurs et du backend Discord, constantes de rôles.

Architecture, décisions et plan de réalisation : [arcolan-platform-docs](https://github.com/ARCO-LAN/arcolan-platform-docs).

## Utilisation dans un backend

Le package est versionné par tags git et installé à une version fixe :

```toml
dependencies = [
    "arcolan-auth-kit @ git+https://github.com/ARCO-LAN/arcolan-auth-kit@v0.1.0",
]
```

## Développement

Prérequis : [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
uv build
```

## CI

À chaque push sur `main` et à chaque pull request : lint et format (ruff), tests (pytest),
construction du package.
