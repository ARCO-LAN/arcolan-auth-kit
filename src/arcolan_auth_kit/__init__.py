"""Package partagé entre les backends Arcolan.

- validation des access tokens émis par Authentik et dépendances FastAPI (`Auth`) ;
- constantes de rôles (`roles`) ;
- à venir : clients générés du service utilisateurs et du backend Discord.
"""

from arcolan_auth_kit import roles
from arcolan_auth_kit.dependencies import Auth
from arcolan_auth_kit.tokens import InvalidToken, JWTVerifier, Principal

__version__ = "0.1.0"
__all__ = ["Auth", "InvalidToken", "JWTVerifier", "Principal", "roles"]
