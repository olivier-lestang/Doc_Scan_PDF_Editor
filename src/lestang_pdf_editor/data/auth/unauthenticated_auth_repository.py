"""Unauthenticated auth stub: no account backend exists yet.

Bouchon d'authentification non authentifié : aucun backend de compte
n'existe pour l'instant.
"""

from lestang_pdf_editor.domain.ports.auth import Session


class AuthUnavailableError(RuntimeError):
    """Raised when account features are used before the website exists.

    Levée quand les fonctionnalités de compte sont utilisées avant que le
    site n'existe.
    """


class UnauthenticatedAuthRepository:
    """Auth stub: always signed out; sign-in is not available yet.

    Bouchon d'authentification : toujours déconnecté ; la connexion n'est
    pas encore disponible.
    """

    def sign_in(self, username: str, password: str) -> Session:
        """Unavailable: the account website does not exist yet.

        Indisponible : le site de compte n'existe pas encore.
        """
        raise AuthUnavailableError("account sign-in requires the future website")

    def sign_out(self) -> None:
        """No-op: there is no session to clear.

        Sans effet : aucune session à effacer.
        """

    def current_session(self) -> Session | None:
        """Always None until a website account exists.

        Toujours None tant qu'un compte de site n'existe pas.
        """
        return None
