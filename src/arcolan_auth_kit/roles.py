"""Constantes de rôles de la plateforme.

Les rôles vivent dans le service utilisateurs (tableau `roles` de chaque joueur), jamais dans
le token. Convention de nommage : `global_` pour les rôles compris par tous les backends,
`<backend>_` pour ceux qu'un seul backend interprète, aucun préfixe pour les rôles de base.
"""

from collections.abc import Iterable

GLOBAL_ADMIN = "global_admin"
"""Administrateur de la plateforme : tous les droits dans tous les backends."""

PLAYER = "player"
"""Rôle de base, attribué à tout compte créé."""

GLOBAL_PREFIX = "global_"


def is_global(role: str) -> bool:
    """Vrai si le rôle est transverse (préfixe `global_`)."""
    return role.startswith(GLOBAL_PREFIX)


def backend_of(role: str) -> str | None:
    """Nom du backend qui interprète un rôle préfixé (`cs2_operator` → `cs2`), None sinon."""
    if is_global(role) or "_" not in role:
        return None
    return role.split("_", 1)[0]


def has_role(roles: Iterable[str], *wanted: str) -> bool:
    """Vrai si l'un des rôles voulus est présent. `global_admin` satisfait toujours la demande."""
    owned = set(roles)
    return GLOBAL_ADMIN in owned or any(role in owned for role in wanted)
