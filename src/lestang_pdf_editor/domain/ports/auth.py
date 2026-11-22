"""Port: user account for the future website (username/password).

Port : compte utilisateur du futur site web (identifiant/mot de passe).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Session:
    """Authenticated session; only tokens are stored, never passwords.

    Session authentifiée ; seuls les jetons sont stockés, jamais les mots
    de passe.
    """

    access_token: str
    refresh_token: str
    expires_at: datetime


class AuthRepository(Protocol):
    """Account repository; unauthenticated stub until the website exists.

    Dépôt de compte ; bouchon non authentifié tant que le site n'existe
    pas.
    """

    def sign_in(self, username: str, password: str) -> Session:
        """Sign in with username and password against the future website.

        Connexion avec identifiant et mot de passe sur le futur site web.
        """
        ...

    def sign_out(self) -> None:
        """Sign out and clear the stored tokens.

        Déconnexion et effacement des jetons stockés.
        """
        ...

    def current_session(self) -> Session | None:
        """Return the current session, or None when signed out.

        Retourne la session courante, ou None si déconnecté.
        """
        ...
